import csv
import io
from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook

from inventory.models import StockBalance, StockDocument, StockMovement
from reports.services import dashboard_data, inventory_report

pytestmark = pytest.mark.django_db


@pytest.fixture
def dated_transactions(stock_env, document_factory):
    inbound = document_factory(quantity="20", confirm=True)
    historical = timezone.now() - timedelta(days=2)
    StockMovement.objects.filter(document=inbound).update(created_at=historical)
    StockDocument.objects.filter(pk=inbound.pk).update(created_at=historical, confirmed_at=historical)
    outbound = document_factory(type="OUT", quantity="5", confirm=True)
    document_factory(quantity="7", warehouse=stock_env.other_warehouse, product=stock_env.second_product, confirm=True)
    document_factory(quantity="999")  # Pending documents must not enter reports.
    return inbound, outbound


def report_filters(stock_env, **changes):
    values = {"start": timezone.localdate(), "end": timezone.localdate(),
              "warehouse": stock_env.warehouse, "category": None, "supplier": None, "q": ""}
    values.update(changes)
    return values


def test_report_opening_period_and_closing_match_ledger(stock_env, dated_transactions):
    result = inventory_report(report_filters(stock_env))
    assert len(result["rows"]) == 1
    row = result["rows"][0]
    assert row["opening"] == Decimal("20")
    assert row["inbound"] == Decimal("0")
    assert row["outbound"] == Decimal("5")
    assert row["closing"] == Decimal("15")
    assert row["value"] == Decimal("157.50")
    assert row["closing"] == StockBalance.objects.get(product=stock_env.product, warehouse=stock_env.warehouse).quantity_on_hand
    assert result["totals"]["closing"] == Decimal("15")
    assert result["chart_data"]["outbound"] == ["5.000"]


def test_supplier_filter_includes_all_movements_of_supplied_sku(stock_env, dated_transactions):
    result = inventory_report(report_filters(stock_env, supplier=stock_env.supplier))
    assert result["rows"][0]["outbound"] == Decimal("5")
    assert result["rows"][0]["closing"] == Decimal("15")


def test_dashboard_has_real_current_value_and_period_totals(stock_env, dated_transactions):
    result = dashboard_data(report_filters(stock_env))
    assert result["metrics"]["stock_value"] == Decimal("157.50")
    assert result["metrics"]["inbound"] == Decimal("0")
    assert result["metrics"]["outbound"] == Decimal("5")
    assert result["warehouse_stats"][0]["quantity"] == Decimal("15")
    assert result["metrics"]["sku_count"] == 2


def test_low_stock_alert_uses_product_threshold(stock_env, document_factory):
    document_factory(quantity="3", confirm=True)
    result = dashboard_data(report_filters(stock_env))
    assert result["metrics"]["low_stock_count"] == 1
    assert result["low_stock"][0]["quantity"] == Decimal("3")
    assert result["low_stock"][0]["min_stock"] == Decimal("5")


def test_report_product_and_warehouse_filters(stock_env, dated_transactions):
    assert not inventory_report(report_filters(stock_env, q="NO-MATCH"))["rows"]
    other = inventory_report(report_filters(stock_env, warehouse=stock_env.other_warehouse, q=stock_env.second_product.sku))
    assert len(other["rows"]) == 1
    assert other["totals"]["closing"] == Decimal("7")


def test_excel_export_uses_same_filtered_ledger_data(client, stock_env, dated_transactions):
    client.force_login(stock_env.viewer)
    response = client.get(reverse("report_export"), {
        "start": str(timezone.localdate()), "end": str(timezone.localdate()),
        "warehouse": stock_env.warehouse.pk, "q": stock_env.product.sku,
    })
    assert response.status_code == 200
    assert response["Content-Type"].endswith("spreadsheetml.sheet")
    sheet = load_workbook(io.BytesIO(response.content)).active
    assert sheet["B3"].value == stock_env.warehouse.name
    assert sheet["B4"].value == stock_env.product.sku
    assert sheet["A7"].value == stock_env.product.sku
    assert [sheet.cell(row=7, column=column).value for column in range(5, 10)] == [20, 0, 5, 15, 157.5]
    assert sheet["H8"].value == 15
    assert sheet.freeze_panes == "E7"
    assert "₫" in sheet["I7"].number_format


def test_report_csv_preserves_filters_and_numbers(client, stock_env, dated_transactions):
    client.force_login(stock_env.viewer)
    response = client.get(reverse("report_export"), {
        "format": "csv", "start": str(timezone.localdate()), "end": str(timezone.localdate()),
        "warehouse": stock_env.warehouse.pk,
    })
    assert response.status_code == 200
    rows = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))
    assert stock_env.warehouse.name in rows[1][0]
    assert len(rows) == 4
    assert Decimal(rows[3][7]) == Decimal("15")


@pytest.mark.parametrize("filters", [
    {"start": "2026-11-10", "end": "2026-11-09"},
    {"start": "invalid", "end": "2026-11-09"},
    {"start": "2020-01-01", "end": "2026-11-09"},
    {"warehouse": "999999"},
])
def test_invalid_report_filters_are_400_for_page_and_export(client, stock_env, filters):
    client.force_login(stock_env.viewer)
    for name in ("report", "report_export", "dashboard"):
        assert client.get(reverse(name), filters).status_code == 400


def test_excel_text_cannot_become_formula(client, stock_env, document_factory):
    stock_env.product.name = "=1+1"
    stock_env.product.save()
    document_factory(confirm=True)
    client.force_login(stock_env.viewer)
    response = client.get(reverse("report_export"))
    sheet = load_workbook(io.BytesIO(response.content)).active
    assert sheet["B7"].value == "'=1+1"
    assert sheet["B7"].data_type == "s"


def test_empty_report_has_zero_totals_and_empty_chart(stock_env):
    result = inventory_report(report_filters(stock_env))
    assert result["rows"] == []
    assert all(value == 0 for value in result["totals"].values())
    assert result["chart_data"]["inbound"] == ["0"]
