import pytest

from app.cost import cost_usd, estimate_cost, load_prices
from app.observability import TokenUsage

USAGE = TokenUsage(input_tokens=1_000_000, output_tokens=100_000)  # Hesabı kolay doğrulanan değerler


def test_pricing_file_has_local_and_api_models():
    prices = load_prices()
    assert prices["qwen3:8b"].input_per_mtok == 0
    assert prices["claude-sonnet-5-5"].input_per_mtok > 0


def test_cost_formula():
    # Sonnet 5.5: 1M girdi × $2 + 0.1M çıktı × $10 = $2 + $1 = $3
    assert cost_usd(USAGE, "claude-sonnet-5-5") == pytest.approx(3.0)


def test_local_model_is_free_and_unknown_model_is_none():
    assert cost_usd(USAGE, "qwen3:8b") == 0
    # Tabloda olmayan modele 0 demek yanıltıcı olurdu → None
    assert cost_usd(USAGE, "bilinmeyen-model") is None


def test_estimate_cost_has_actual_and_reference():
    estimate = estimate_cost(USAGE, "qwen3:8b", "claude-sonnet-5-5")
    assert (estimate.usd, estimate.reference_usd) == (0, pytest.approx(3.0))
