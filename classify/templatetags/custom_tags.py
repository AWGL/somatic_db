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
    # convert to lower to make it case insensitive
    value = value.lower()

    # Either pending or ACMG/SVIG VUS codes
    if value == "pending" or "vus" in value:
        css_class = "warning"

    # ACMG or SVIG benign codes
    elif value.startswith("b") or "benign" in value:
        css_class = "primary"

    # SVIG oncogenic codes
    elif value.startswith("o") or "oncogenic" in value:
        css_class = "danger"

    # ACMG pathogenic codes
    elif value.startswith("p") or "pathogenic" in value:
        css_class = "danger"

    # clinical actionability codesn all start with C
    elif value.startswith("c"):
        css_class = "danger"

    # tier 3 is VUS, tier 4 is benign, others are actionable
    elif value.startswith("tier"):
        if value == "tier 3":
            css_class = "warning"
        elif value == "tier 4":
            css_class = "primary"
        else:
            css_class = "danger"

    # if it is not one of the above, then colour grey
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
    if value=="A":
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
