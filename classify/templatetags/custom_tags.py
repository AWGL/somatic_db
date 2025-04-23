from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()


@register.filter
@stringfilter
def colour_by_class(value):
    """
    colour anywhere the current classification is displayed
    e.g. summary buttons, dropdowns, table rows
    """
    value = value.lower()
    if value == "pending" or "vus" in value:
        css_class = "warning"

    elif value.startswith("b") or "benign" in value:
        css_class = "primary"

    elif value.startswith("o") or "oncogenic" in value:
        css_class = "danger"

    elif value.startswith("p") or "pathogenic" in value:
        css_class = "danger"

    elif value.startswith("tier"):
        if value == "tier iii":
            css_class = "warning"
        elif value == "tier iv":
            css_class = "primary"
        else:
            css_class = "danger"

    else:
        css_class = "secondary"

    return css_class


@register.filter
@stringfilter
def colour_by_build(value):
    """
    Colour anywhere the genome build is displayed
    """
    if value == "38":
        return "success"
    else:
        return "info"


@register.filter
@stringfilter
def colour_by_guideline(value):
    """
    colour different guidelines differently, e.g. ACMG/ SVIG
    """
    if value=="G":
        return "primary"
    if value=="S":
        return "info"
    else:
        return "success"


@register.filter
@stringfilter
def colour_by_count(value):
    """
    colour different guidelines differently, e.g. ACMG/ SVIG
    """
    value = int(value)
    if value > 0:
        return "warning"
    else:
        return "secondary"
