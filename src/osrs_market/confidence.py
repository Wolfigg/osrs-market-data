from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConfidenceComponents:
    mechanical: float
    price: float
    liquidity: float
    throughput: float
    output_model: float
    source_freshness: float

    def normalised(self) -> "ConfidenceComponents":
        clamp = lambda value: max(0.0, min(100.0, float(value)))
        return ConfidenceComponents(
            clamp(self.mechanical), clamp(self.price), clamp(self.liquidity),
            clamp(self.throughput), clamp(self.output_model), clamp(self.source_freshness),
        )


DEFAULT_WEIGHTS = {
    "mechanical": 0.22,
    "price": 0.20,
    "liquidity": 0.18,
    "throughput": 0.16,
    "output_model": 0.14,
    "source_freshness": 0.10,
}


def method_confidence(components: ConfidenceComponents, weights: dict[str, float] | None = None) -> dict[str, object]:
    current = components.normalised()
    selected = dict(DEFAULT_WEIGHTS if weights is None else weights)
    missing = set(DEFAULT_WEIGHTS) - set(selected)
    if missing:
        raise ValueError(f"missing confidence weights: {sorted(missing)}")
    total_weight = sum(max(0.0, float(selected[key])) for key in DEFAULT_WEIGHTS)
    if total_weight <= 0:
        raise ValueError("confidence weights must sum to a positive value")
    values = {
        "mechanical": current.mechanical,
        "price": current.price,
        "liquidity": current.liquidity,
        "throughput": current.throughput,
        "outputModel": current.output_model,
        "sourceFreshness": current.source_freshness,
    }
    raw = (
        current.mechanical * selected["mechanical"]
        + current.price * selected["price"]
        + current.liquidity * selected["liquidity"]
        + current.throughput * selected["throughput"]
        + current.output_model * selected["output_model"]
        + current.source_freshness * selected["source_freshness"]
    ) / total_weight
    return {
        "overall": round(raw, 1),
        "components": values,
        "weights": {key: round(float(selected[key]) / total_weight, 6) for key in DEFAULT_WEIGHTS},
    }
