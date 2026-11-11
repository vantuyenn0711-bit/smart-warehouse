"""Read models: one set of filters for on-screen reports and downloadable exports."""
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.db.models import F, Q, Sum
from django.db.models.functions import TruncDate

from catalog.models import Product
from core.demo import demo_transaction
from inventory.models import StockBalance, StockDocument, StockMovement, Warehouse

ZERO = Decimal("0")


def filtered_movements(data):
    movements = StockMovement.objects.filter(document__status=StockDocument.Status.CONFIRMED)
    if data.get("warehouse"):
        movements = movements.filter(warehouse=data["warehouse"])
    if data.get("category"):
        movements = movements.filter(product__category=data["category"])
    if data.get("q"):
        movements = movements.filter(Q(product__sku__icontains=data["q"]) | Q(product__name__icontains=data["q"]))
    if data.get("supplier"):
        # Pick SKUs received from the supplier, then include ALL their movements.
        # Subtracting only supplier-linked movements would give a false closing balance.
        supplied = StockMovement.objects.filter(document__supplier=data["supplier"], document__type="IN").values("product_id")
        movements = movements.filter(product_id__in=supplied)
    return movements


def chart_for(movements, start, end):
    grouped = movements.filter(created_at__date__gte=start, created_at__date__lte=end).annotate(day=TruncDate("created_at")).values("day").annotate(
        inbound=Sum("signed_qty", filter=Q(signed_qty__gt=0)),
        outbound=Sum("signed_qty", filter=Q(signed_qty__lt=0)),
    ).order_by("day")
    indexed = {row["day"]: row for row in grouped}
    result = {"labels": [], "inbound": [], "outbound": []}
    day = start
    while day <= end:
        point = indexed.get(day, {})
        result["labels"].append(day.strftime("%d/%m"))
        result["inbound"].append(str(point.get("inbound") or ZERO))
        result["outbound"].append(str(-(point.get("outbound") or ZERO)))
        day += timedelta(days=1)
    return result


@demo_transaction
def inventory_report(data):
    movements = filtered_movements(data)
    start, end = data["start"], data["end"]
    aggregates = movements.filter(created_at__date__lte=end).order_by().values("product_id", "warehouse_id").annotate(
        opening=Sum("signed_qty", filter=Q(created_at__date__lt=start)),
        inbound=Sum("signed_qty", filter=Q(created_at__date__gte=start, signed_qty__gt=0)),
        outbound=Sum("signed_qty", filter=Q(created_at__date__gte=start, signed_qty__lt=0)),
    )
    aggregates = list(aggregates)
    products = Product.objects.select_related("category").in_bulk({row["product_id"] for row in aggregates})
    warehouses = Warehouse.objects.in_bulk({row["warehouse_id"] for row in aggregates})
    rows = []
    totals = dict.fromkeys(["opening", "inbound", "outbound", "closing", "value"], ZERO)
    for item in aggregates:
        product = products[item["product_id"]]
        opening, inbound = item["opening"] or ZERO, item["inbound"] or ZERO
        outbound = -(item["outbound"] or ZERO)
        closing = opening + inbound - outbound
        row = {"product": product, "warehouse": warehouses[item["warehouse_id"]],
               "opening": opening, "inbound": inbound, "outbound": outbound,
               "closing": closing, "value": closing * product.default_cost}
        rows.append(row)
        for key in totals:
            totals[key] += row[key]
    rows.sort(key=lambda row: (row["product"].sku, row["warehouse"].code))
    product_totals = {}
    for row in rows:
        entry = product_totals.setdefault(row["product"].pk, {"product": row["product"], "inbound": ZERO, "outbound": ZERO})
        entry["inbound"] += row["inbound"]
        entry["outbound"] += row["outbound"]
    top_products = sorted(product_totals.values(), key=lambda row: row["inbound"] + row["outbound"], reverse=True)[:5]
    return {"rows": rows, "totals": totals, "top_products": top_products,
            "chart_data": chart_for(movements, start, end)}


def dashboard_data(data):
    stocks = StockBalance.objects.select_related("product__category", "warehouse")
    products = Product.objects.filter(is_active=True)
    if data.get("warehouse"):
        stocks = stocks.filter(warehouse=data["warehouse"])
    low_stocks = stocks.filter(product__is_active=True, warehouse__is_active=True, quantity_on_hand__lt=F("product__min_stock"))
    stock_value = stocks.aggregate(value=Sum(F("quantity_on_hand") * F("product__default_cost")))["value"] or ZERO
    movements = filtered_movements(data)
    period = movements.filter(created_at__date__gte=data["start"], created_at__date__lte=data["end"])
    sums = period.aggregate(inbound=Sum("signed_qty", filter=Q(signed_qty__gt=0)), outbound=Sum("signed_qty", filter=Q(signed_qty__lt=0)))
    warehouses = Warehouse.objects.filter(is_active=True)
    if data.get("warehouse"):
        warehouses = warehouses.filter(pk=data["warehouse"].pk)
    warehouse_quantities = {row["warehouse_id"]: row for row in stocks.order_by().values("warehouse_id").annotate(quantity=Sum("quantity_on_hand"))}
    stock_skus = defaultdict(int)
    for warehouse_id in stocks.filter(quantity_on_hand__gt=0).values_list("warehouse_id", flat=True):
        stock_skus[warehouse_id] += 1
    total_quantity = sum((row["quantity"] or ZERO for row in warehouse_quantities.values()), ZERO)
    warehouse_stats = []
    for warehouse in warehouses:
        quantity = warehouse_quantities.get(warehouse.pk, {}).get("quantity") or ZERO
        warehouse_stats.append({"warehouse": warehouse, "sku_count": stock_skus[warehouse.pk], "quantity": quantity,
                                "percent": int(quantity * 100 / total_quantity) if total_quantity else 0})
    low = [{"product": row.product, "warehouse": row.warehouse, "quantity": row.quantity_on_hand, "min_stock": row.product.min_stock} for row in low_stocks.order_by("quantity_on_hand", "product__sku")[:5]]
    recent = StockDocument.objects.select_related("warehouse", "supplier", "created_by").prefetch_related("items__product").order_by("-created_at", "-pk")
    if data.get("warehouse"):
        recent = recent.filter(warehouse=data["warehouse"])
    return {"metrics": {"sku_count": products.count(), "warehouse_count": warehouses.count(),
                         "low_stock_count": low_stocks.count(), "stock_value": stock_value,
                         "inbound": sums["inbound"] or ZERO, "outbound": -(sums["outbound"] or ZERO)},
            "recent_documents": recent[:6], "low_stock": low, "warehouse_stats": warehouse_stats,
            "chart_data": chart_for(movements, data["start"], data["end"])}
