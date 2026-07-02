"""Alert condition evaluators — check if alert should fire."""



def evaluate_condition(
    condition: str, threshold: float, current_price: float, previous_close: float | None = None
) -> bool:
    """Check if an alert condition is met."""
    match condition:
        case "above":
            return current_price >= threshold
        case "below":
            return current_price <= threshold
        case "change_pct":
            if previous_close and previous_close > 0:
                change_pct = ((current_price - previous_close) / previous_close) * 100
                return abs(change_pct) >= threshold
            return False
        case _:
            return False
