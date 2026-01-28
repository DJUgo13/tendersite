from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def is_same(value, other):
    """Checks if two values are equal, useful when auto-formatters strip spaces around =="""
    return str(value) == str(other)
