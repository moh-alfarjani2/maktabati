from django import template

register = template.Library()

@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    """
    Updates the current URL query string with new parameters.
    Preserves existing parameters (like search queries or sorting).
    Usage: {% url_replace page=2 %} or {% url_replace sort='price' dir='desc' %}
    """
    query = context['request'].GET.copy()
    for kwarg, value in kwargs.items():
        if value is not None and value != '':
            query[kwarg] = str(value)
        else:
            query.pop(kwarg, None)
    return f"?{query.urlencode()}"
