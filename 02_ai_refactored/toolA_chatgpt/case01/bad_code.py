def _calculate_base_result(first_value: int, second_value: int, third_value: int) -> int:
    if first_value > 10:
        return first_value + second_value + third_value if second_value > 5 else first_value - second_value + third_value

    return first_value + second_value - third_value if third_value > 0 else first_value - second_value - third_value


def _apply_alternating_offset(value: int, start: int = 0, end: int = 10) -> int:
    for index in range(start, end):
        value += index if index % 2 == 0 else -index
    return value


def f(a: int, b: int, c: int) -> int:
    result = _calculate_base_result(a, b, c)
    return _apply_alternating_offset(result)
