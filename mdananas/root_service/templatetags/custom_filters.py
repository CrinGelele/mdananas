from django import template

register = template.Library()

@register.filter
def mul100(value):
    if value:
        return f"{value * 100}"
    return None
