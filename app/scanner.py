import asyncio, time
import httpx
CHAINS = {'solana','base','bsc','ethereum'}

class DexScanner:
    def __init__(self, base_url, max_cap, min_liquidity):
        self.base_url=base_url.rstrip('/'); self.max_cap=max_cap; self.min_liquidity=min_liquidity; self.cache=[]; self.cache_at=0
    async def get(self, client, path):
        r=await client.get(self.base_url+path); r.raise_for_status(); return r.json()
    async def scan(self, force=False):
        if not force and time.time()-self.cache_at<90: return self.cache
        async with httpx.AsyncClient(timeout=20, headers={'User-Agent':'ARAD-Meme-Hunter/0.1'}) as client:
            profiles=await self.get(client,'/token-profiles/latest/v1')
            sem=asyncio.Semaphore(8)
            async def fetch(p):
                chain=(p.get('chainId') or '').lower(); addr=p.get('tokenAddress')
                if chain not in CHAINS or not addr: return []
                async with sem:
                    try: return await self.get(client,f'/token-pairs/v1/{chain}/{addr}')
                    except (httpx.HTTPError,ValueError): return []
            batches=await asyncio.gather(*(fetch(p) for p in profiles[:120] if isinstance(p,dict)))
            rows=[]; seen=set()
            for pairs in batches:
                if not isinstance(pairs,list) or not pairs: continue
                pair=max(pairs,key=lambda p:float((p.get('liquidity') or {}).get('usd') or 0))
                chain=(pair.get('chainId') or '').lower(); token=pair.get('baseToken') or {}; addr=token.get('address')
                if chain not in CHAINS or not addr or (chain,addr) in seen: continue
                seen.add((chain,addr)); liq=float((pair.get('liquidity') or {}).get('usd') or 0)
                mc,fdv=pair.get('marketCap'),pair.get('fdv'); cap=float(mc or fdv or 0)
                if liq<self.min_liquidity or cap<=0 or cap>self.max_cap: continue
                tx=(pair.get('txns') or {}).get('h24') or {}
                rows.append({'chain':chain,'name':token.get('name') or 'Unknown','symbol':token.get('symbol') or '?','contract_address':addr,'pair_address':pair.get('pairAddress'),'price_usd':pair.get('priceUsd'),'market_cap_usd':mc,'fdv_usd':fdv,'cap_metric':'market_cap' if mc else 'fdv_proxy','liquidity_usd':liq,'volume_24h_usd':(pair.get('volume') or {}).get('h24'),'change_24h_pct':(pair.get('priceChange') or {}).get('h24'),'buys_24h':tx.get('buys'),'sells_24h':tx.get('sells'),'pair_created_at':pair.get('pairCreatedAt'),'dex_url':pair.get('url'),'holder_count':None,'holder_growth_pct':None,'ourbit_listed':None,'data_source':'DexScreener'})
            self.cache=sorted(rows,key=lambda x:float(x.get('volume_24h_usd') or 0),reverse=True); self.cache_at=time.time(); return self.cache
