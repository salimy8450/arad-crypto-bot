from dataclasses import dataclass

def clamp(v, lo=0, hi=100): return max(lo, min(hi, float(v)))

@dataclass
class Scores:
    pump_score: float
    listing_score: float
    status: str
    reasons: list[str]

def score_market(pair: dict) -> Scores:
    volume = float((pair.get('volume') or {}).get('h24') or 0)
    liquidity = float((pair.get('liquidity') or {}).get('usd') or 0)
    tx = (pair.get('txns') or {}).get('h24') or {}
    buys, sells = float(tx.get('buys') or 0), float(tx.get('sells') or 0)
    change = float((pair.get('priceChange') or {}).get('h24') or 0)
    vl = volume / liquidity if liquidity else 0
    br = buys / max(sells, 1)
    raw = clamp(vl / 5 * 100) * .30 + clamp(br / 3 * 100) * .25 + clamp((change + 20) / 1.2) * .20 + clamp(liquidity / 150000 * 100) * .25
    reasons = []
    if vl >= 1.5: reasons.append('24h volume high relative to liquidity')
    if br >= 1.5: reasons.append('Buy transactions exceed sells')
    if change > 0: reasons.append('Positive 24h momentum')
    if liquidity >= 50000: reasons.append('Minimum liquidity filter passed')
    pump = round(raw / 10, 1)
    return Scores(pump, 0.0, 'STRONG_CANDIDATE' if pump >= 7.5 else 'WATCH', reasons)
