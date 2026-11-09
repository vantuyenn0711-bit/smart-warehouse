from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def vn_num(value):
    try:
        number = Decimal(str(value or 0))
        text = f"{number:,.3f}".rstrip("0").rstrip(".")
        return text.replace(",", "_").replace(".", ",").replace("_", ".")
    except (InvalidOperation, ValueError, TypeError):
        return value


@register.filter
def money(value):
    try:
        return f"{Decimal(str(value or 0)):,.0f}".replace(",", ".") + " ₫"
    except (InvalidOperation, ValueError, TypeError):
        return value


@register.simple_tag(takes_context=True)
def querystring(context, **kwargs):
    params = context["request"].GET.copy()
    for key, value in kwargs.items():
        if value is None:
            params.pop(key, None)
        else:
            params[key] = value
    return params.urlencode()
