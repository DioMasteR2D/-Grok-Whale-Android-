"""Jupiter Price API v3 adapter. Returns freshness metadata; never invents missing prices."""
import os, re, httpx
B58 = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")
async def fetch_prices(mints):
    clean=list(dict.fromkeys(m for m in mints if isinstance(m,str) and B58.fullmatch(m)))[:50]
    if not clean:
        return {"status":"rejected","items":{},"message":"Provide 1-50 valid Solana mint addresses."}
    headers={"Accept":"application/json"}
    key=os.getenv("JUPITER_API_KEY","").strip()
    if key: headers["x-api-key"]=key
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            response=await client.get("https://api.jup.ag/price/v3",params={"ids":",".join(clean)},headers=headers)
        if response.status_code==429:
            return {"status":"rate_limited","items":{},"message":"Jupiter rate limit reached."}
        response.raise_for_status()
        payload=response.json()
        items={}
        for mint in clean:
            row=payload.get(mint)
            if isinstance(row,dict) and isinstance(row.get("usdPrice"),(int,float)) and row["usdPrice"]>0:
                items[mint]={"usd_price":row["usdPrice"],"liquidity":row.get("liquidity"),
                             "block_id":row.get("blockId"),"created_at":row.get("createdAt"),
                             "price_change_24h":row.get("priceChange24h")}
            else:
                items[mint]=None
        return {"status":"ok","provider":"Jupiter Price API v3","items":items,
                "missing_prices":[m for m,v in items.items() if v is None],
                "message":"Missing or stale/unpriced tokens are not assigned a fallback price."}
    except httpx.HTTPStatusError as exc:
        return {"status":"provider_error","items":{},"http_status":exc.response.status_code}
    except httpx.HTTPError:
        return {"status":"provider_unavailable","items":{}}
