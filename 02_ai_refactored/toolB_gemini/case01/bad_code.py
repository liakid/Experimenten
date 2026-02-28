def calculate_result(a, b, c):
    """Berechnet das Endergebnis basierend auf Schwellenwerten und einer alternierenden Summe."""
    base_value = _calculate_base_value(a, b, c)
    adjustment = _calculate_alternating_offset(limit=10)
    return base_value + adjustment


def _calculate_base_value(a, b, c):
    """Ermittelt den Basiswert abhängig von der Größe von a."""
    if a > 10:
        # Falls b > 5: a + b + c, sonst: a - b + c
        b_modifier = b if b > 5 else -b
        return a + b_modifier + c

    # Falls c > 0: a + b - c, sonst: a - b - c
    b_modifier = b if c > 0 else -b
    return a + b_modifier - c


def _calculate_alternating_offset(limit):
    """Berechnet eine Summe mit alternierenden Vorzeichen (0 - 1 + 2 - 3 ...)."""
    return sum(i if i % 2 == 0 else -i for i in range(limit))