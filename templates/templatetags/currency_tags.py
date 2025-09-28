"""
Template tags for currency formatting
"""
from django import template
from utils.currency import format_currency, get_currency_info

register = template.Library()


@register.filter
def currency(value):
    """
    Format a value as XAF currency
    Usage: {{ amount|currency }}
    """
    return format_currency(value)


@register.filter
def currency_no_symbol(value):
    """
    Format a value as currency without symbol
    Usage: {{ amount|currency_no_symbol }}
    """
    return format_currency(value, include_symbol=False)


@register.simple_tag
def currency_symbol():
    """
    Get the currency symbol
    Usage: {% currency_symbol %}
    """
    return get_currency_info()['symbol']


@register.simple_tag
def currency_code():
    """
    Get the currency code
    Usage: {% currency_code %}
    """
    return get_currency_info()['code']


@register.simple_tag
def currency_name():
    """
    Get the currency name
    Usage: {% currency_name %}
    """
    return get_currency_info()['name']
