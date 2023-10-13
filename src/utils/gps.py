from typing import Tuple


def gps_to_decimal(input: Tuple[float, float, float]) -> float:
    d, m, s = input
    return d + (m / 60.0) + (s / 3600.0)
