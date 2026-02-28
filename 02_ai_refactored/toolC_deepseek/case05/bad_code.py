def calculate_modified_value(value_a, value_b, value_c):
    """Calculate a modified value based on input parameters and a fixed adjustment."""
    base_value = _calculate_base_value(value_a, value_b, value_c)
    adjusted_value = _apply_adjustment(base_value)
    return adjusted_value

def _calculate_base_value(value_a, value_b, value_c):
    """Calculate the base value based on the input parameters."""
    if value_a > 10:
        return value_a + value_b + value_c if value_b > 5 else value_a - value_b + value_c

    return value_a + value_b - value_c if value_c > 0 else value_a - value_b - value_c

def _apply_adjustment(value):
    """Apply iterative adjustment to the value."""
    adjustment = 0
    for number in range(10):
        adjustment += number if number % 2 == 0 else -number

    return value + adjustment