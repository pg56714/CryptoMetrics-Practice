import requests
import pandas as pd


def get_market_data():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 250,
        "page": 1,
        "sparkline": False,
    }
    response = requests.get(url, params=params)
    return response.json()


def analyze_liquidity(data):
    records = []
    for coin in data:
        market_cap = coin["market_cap"]
        volume = coin["total_volume"]
        ratio = volume / market_cap if market_cap else 0
        records.append(
            {
                "name": coin["name"],
                "symbol": coin["symbol"],
                "market_cap": market_cap,
                "volume_24h": volume,
                "liquidity_ratio": ratio,
            }
        )
    df = pd.DataFrame(records)
    return df.sort_values("liquidity_ratio").head(20)  # 排前 20 流動性最差


data = get_market_data()
df_liquidity = analyze_liquidity(data)
print(df_liquidity)
