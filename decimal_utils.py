"""Decimal utilities for precise financial calculations"""

from decimal import Decimal, ROUND_HALF_UP, getcontext
from typing import Union

# Set precision for decimal calculations
getcontext().prec = 28


def format_price(price: Union[float, Decimal]) -> str:
    """
    Format price according to specification:
    - Prices >= 1: 2 decimal places
    - Prices < 1: up to 8 decimal places, strip trailing zeros
    
    Args:
        price: Price to format (float or Decimal)
        
    Returns:
        str: Formatted price string
    """
    decimal_price = Decimal(str(price))
    
    if decimal_price >= 1:
        # For prices >= 1, use 2 decimal places
        formatted = decimal_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    else:
        # For prices < 1, use up to 8 decimal places
        # We'll use a progressive approach to find the right number of decimals
        formatted = decimal_price.normalize()
        # Ensure we don't exceed 8 decimal places
        if abs(formatted.as_tuple().exponent) > 8:
            formatted = decimal_price.quantize(Decimal('0.00000001'), rounding=ROUND_HALF_UP)
    
    # Convert to string and strip trailing zeros for prices < 1
    result = str(formatted)
    if decimal_price < 1:
        result = result.rstrip('0').rstrip('.') if '.' in result else result
    
    return result


def precise_divide(a: Union[float, Decimal], b: Union[float, Decimal]) -> Decimal:
    """
    Perform precise division using Decimal.
    
    Args:
        a: Dividend
        b: Divisor
        
    Returns:
        Decimal: Result of division
    """
    return Decimal(str(a)) / Decimal(str(b))


def precise_multiply(a: Union[float, Decimal], b: Union[float, Decimal]) -> Decimal:
    """
    Perform precise multiplication using Decimal.
    
    Args:
        a: First operand
        b: Second operand
        
    Returns:
        Decimal: Result of multiplication
    """
    return Decimal(str(a)) * Decimal(str(b))


def precise_add(a: Union[float, Decimal], b: Union[float, Decimal]) -> Decimal:
    """
    Perform precise addition using Decimal.
    
    Args:
        a: First operand
        b: Second operand
        
    Returns:
        Decimal: Result of addition
    """
    return Decimal(str(a)) + Decimal(str(b))


def precise_subtract(a: Union[float, Decimal], b: Union[float, Decimal]) -> Decimal:
    """
    Perform precise subtraction using Decimal.
    
    Args:
        a: First operand
        b: Second operand
        
    Returns:
        Decimal: Result of subtraction
    """
    return Decimal(str(a)) - Decimal(str(b))


def precise_round(value: Union[float, Decimal], decimals: int) -> Decimal:
    """
    Round a value to specified number of decimal places using Decimal.
    
    Args:
        value: Value to round
        decimals: Number of decimal places
        
    Returns:
        Decimal: Rounded value
    """
    decimal_value = Decimal(str(value))
    return decimal_value.quantize(Decimal('0.' + '0' * decimals), rounding=ROUND_HALF_UP)