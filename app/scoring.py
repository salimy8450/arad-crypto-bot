from dataclasses import dataclass

def clamp(v, lo=0.0, hi=100.0):
    return max(lo, min(hi, float(v)))

@dataclass
class Scores:
    pump_score: float
    listing_score: float | None
    status: str
    reasons: list[str]

def score_market(pair: dict) -> Scores:
    """Transparent momentum ranking, not a predictive probability."""
    volume = float((pair.get("volume") or {}).get("h24") or 0)
    liquidity = float((pair.get("liquidity") or {}).get("usd") or 0)
    tx = (pair.get("txns") or {}).get("h24") or {}
    buys, sells = float(tx.get("buys") or 0), float(tx.get("sells") or 0)
    change = float((pair.get("priceChange") or {}).get("h24") or 0)
    vol_liq = volume / liquidity if liquidity else 0
    buy_share = buys / max(buys + sells, 1)
    # Weighted components are deliberately visible and bounded.
    volume_component = clamp(vol_liq / 3.0 * 100)
    buy_component = clamp((buy_share - 0.35) / 0.40 * 100)
    momentum_component = clamp((change + 15) / 60 * 100)
    liquidity_component = clamp(liquidity / 150000 * 100)
    raw = (volume_component * .30 + buy_component * .25 +
           momentum_component * .25 + liquidity_component * .20)
    pump = round(raw / 10, 1)
    reasons = []
    if vol_liq >= 1.5: reasons.append("حجم معاملات ۲۴ساعته نسبت به نقدینگی بالاست")
    if buy_share >= .58: reasons.append("تعداد خریدها از فروش‌ها بیشتر است")
    if change >= 10: reasons.append("شتاب قیمت ۲۴ساعته مثبت است")
    if liquidity >= 50000: reasons.append("حداقل نقدینگی تعیین‌شده رعایت شده")
    if not reasons: reasons.append("شواهد مومنتوم قوی کافی نیست")
    # No verified historical Orbit listing dataset is connected: do not invent a score.
    return Scores(pump, None, "STRONG_CANDIDATE" if pump >= 7.5 else "WATCH", reasons)
