"""
Currency formatting utilities for the Employee Attendance System
"""
from django.conf import settings
from decimal import Decimal


def format_currency(amount, include_symbol=True):
    """
    Format a decimal amount as XAF currency
    
    Args:
        amount: Decimal or float amount to format
        include_symbol: Whether to include the FCFA symbol
    
    Returns:
        Formatted currency string
    """
    if amount is None:
        amount = Decimal('0.00')
    
    if isinstance(amount, (int, float)):
        amount = Decimal(str(amount))
    
    # Format with thousands separator and 2 decimal places
    formatted = "{:,.2f}".format(float(amount))
    
    if include_symbol:
        currency_symbol = getattr(settings, 'CURRENCY_SYMBOL', 'FCFA')
        return f"{formatted} {currency_symbol}"
    
    return formatted


def get_currency_info():
    """
    Get currency information from settings
    
    Returns:
        Dictionary with currency code, symbol, and name
    """
    return {
        'code': getattr(settings, 'CURRENCY_CODE', 'XAF'),
        'symbol': getattr(settings, 'CURRENCY_SYMBOL', 'FCFA'),
        'name': getattr(settings, 'CURRENCY_NAME', 'Central African Franc')
    }


def parse_currency(currency_string):
    """
    Parse a currency string back to Decimal
    
    Args:
        currency_string: String like "1,234.56 FCFA"
    
    Returns:
        Decimal amount
    """
    if not currency_string:
        return Decimal('0.00')
    
    # Remove currency symbol and spaces
    cleaned = currency_string.replace('FCFA', '').replace(',', '').strip()
    
    try:
        return Decimal(cleaned)
    except:
        return Decimal('0.00')
