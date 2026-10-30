
import os, time, requests
from datetime import datetime, timezone

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN secret is missing")
TG = f"https://api.telegram.org/bot{TOKEN}"
BINANCE = "https://api.binance.com"
SYMBOLS = ["DOGEUSDT","SHIBUSDT","PEPEUSDT","BONKUSDT","WIFUSDT","FLOKIUSDT","BOMEUSDT","MEMEUSDT"]

def get(url, params=None):
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

def ema(a, n):
    if len(a) < n: return None
    v = sum(a[:n]) / n
    k = 2 / (n + 1)
    for x in a[n:]: v = x*k + v*(1-k)
    return v

def rsi(a, n=14):
    if len(a) <= n: return None
    changes = [a[i]-a[i-1] for i in range(1,len(a))]
    gains = [max(x,0) for x in changes]
    losses = [max(-x,0) for x in changes]
    ag, al = sum(gains[:n])/n, sum(losses[:n])/n
    for i in range(n,len(gains)):
        ag = (ag*(n-1)+gains[i])/n
        al = (al*(n-1)+losses[i])/n
    return 100 if al == 0 else 100-100/(1+ag/al)

def candles(symbol, interval):
    raw = get(BINANCE+"/api/v3/klines", {"symbol":symbol,"interval":interval,"limit":100})[:-1]
    return [{"o":float(x[1]),"h":float(x[2]),"l":float(x[3]),"c":float(x[4]),"v":float(x[5]),"t":int(x[6])} for x in raw]

def analyze(symbol):
    a, b = candles(symbol,"15m"), candles(symbol,"1h")
    x, y = [z["c"] for z in a], [z["c"] for z in b]
    e21,e50,e21h,e50h = ema(x,21),ema(x,50),ema(y,21),ema(y,50)
    r15,r1h = rsi(x),rsi(y)
    if None in (e21,e50,e21h,e50h,r15,r1h): return None
    trs=[]
    for i in range(1,len(a)):
        z,p=a[i],a[i-1]["c"]
        trs.append(max(z["h"]-z["l"],abs(z["h"]-p),abs(z["l"]-p)))
    atr=sum(trs[-14:])/14
    if atr <= 0: return None
    avgvol=sum(z["v"] for z in a[-15:-1])/14
    vr=a[-1]["v"]/avgvol if avgvol else 0
    price=x[-1]
    long=short=0
    if e21>e50: long+=25
    else: short+=25
    if e21h>e50h: long+=25
    else: short+=25
    if price>e21: long+=15
    else: short+=15
    if 50<=r15<=68: long+=15
    elif 32<=r15<=50: short+=15
    if r1h>50: long+=10
    elif r1h<50: short+=10
    if vr>=1.2:
        if a[-1]["c"]>a[-1]["o"]: long+=10
        elif a[-1]["c"]<a[-1]["o"]: short+=10
    side="LONG" if long>=short else "SHORT"
    score=max(long,short)
    aligned=(side=="LONG" and e21>e50 and e21h>e50h) or (side=="SHORT" and e21<e50 and e21h<e50h)
    if not aligned or score<75 or (side=="LONG" and r15>=75) or (side=="SHORT" and r15<=25): return None
    risk=atr*1.5
    sl=price-risk if side=="LONG" else price+risk
    tps=[price+risk*k if side=="LONG" else price-risk*k for k in (1,1.5,2,3)]
    return (side,score,price,sl,tps,r15,r1h,vr)

def fmt(x): return f"{x:.8f}".rstrip("0").rstrip(".")

def main():
    # Workflow checks every 5 minutes; notifications are sent only each 15 minutes.
    if datetime.now(timezone.utc).minute % 15 != 0:
        print("Not an alert slot.")
        return
    updates=get(TG+"/getUpdates").get("result",[])
    chat=None
    for u in reversed(updates):
        m=u.get("message") or u.get("edited_message")
        if m and m.get("chat",{}).get("type")=="private":
            chat=m["chat"]["id"]; break
    if chat is None:
        print("Open your Telegram bot and press Start first.")
        return
    signals=[]
    for symbol in SYMBOLS:
        try:
            s=analyze(symbol)
            if s: signals.append((symbol,s))
        except Exception as e:
            print(symbol, "scan error:", e)
        time.sleep(.25)
    if not signals:
        requests.post(TG+"/sendMessage",data={"chat_id":chat,"text":"Arad Crypto Bot: اسکن انجام شد؛ فعلاً سیگنال قوی و هم‌جهت پیدا نشد."},timeout=20).raise_for_status()
        return
    for symbol,s in signals:
        side,score,price,sl,tps,r15,r1h,vr=s
        msg=(f"🚨 ARAD CRYPTO SIGNAL\n{symbol} | {side} | Score {score}/100\n"
             f"Entry: {fmt(price)}\nTP1: {fmt(tps[0])}\nTP2: {fmt(tps[1])}\n"
             f"TP3: {fmt(tps[2])}\nTP4: {fmt(tps[3])}\nSL: {fmt(sl)}\n"
             f"RSI 15m: {r15:.1f} | RSI 1h: {r1h:.1f} | Volume: {vr:.2f}x\n"
             "ATR-based levels; leverage not included. Confirm before trading.")
        r=requests.post(TG+"/sendMessage",data={"chat_id":chat,"text":msg},timeout=20)
        r.raise_for_status()
        time.sleep(1)
    print("Sent",len(signals),"signal(s).")

if __name__=="__main__":
    main()

