from app.scoring import score_market

def test_score_is_bounded_and_listing_is_unknown():
    result = score_market({"volume":{"h24":200000},"liquidity":{"usd":50000},
        "txns":{"h24":{"buys":100,"sells":40}},"priceChange":{"h24":20}})
    assert 0 <= result.pump_score <= 10
    assert result.listing_score is None
    assert result.status in {"STRONG_CANDIDATE","WATCH"}
