def expo_backoff(attempt: int, base: float = 2.0, unit_s: float = 1.0) -> float:
    attempt = max(0, attempt)
    return unit_s * (base ** attempt)
