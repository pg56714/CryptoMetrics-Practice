import requests
import pandas as pd
import matplotlib.pyplot as plt
import time

MIN_MARKET_CAP = 1e6  # 過濾市值過小的幣
TOP_N = 5
SLEEP = 0.05


def fetch_binance_oi_with_price():
    print("🔄 抓取 Binance 合約 OI × 最新價格...")
    symbols_info = requests.get("https://fapi.binance.com/fapi/v1/exchangeInfo").json()[
        "symbols"
    ]
    symbols = [
        s["symbol"]
        for s in symbols_info
        if s["quoteAsset"] == "USDT" and s["contractType"] == "PERPETUAL"
    ]

    oi_data = []
    for symbol in symbols:
        try:
            oi = requests.get(
                "https://fapi.binance.com/fapi/v1/openInterest",
                params={"symbol": symbol},
            ).json()
            ticker = requests.get(
                "https://fapi.binance.com/fapi/v1/ticker/price",
                params={"symbol": symbol},
            ).json()
            oi_val = float(oi["openInterest"]) * float(ticker["price"])
            oi_data.append({"symbol": symbol, "oi_value": oi_val})
            time.sleep(SLEEP)
        except Exception:
            continue
    return pd.DataFrame(oi_data)


def fetch_coingecko_market_caps():
    print("🔄 抓取 CoinGecko 市值資料中...")
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 250,
        "page": 1,
    }
    mcap_list = []
    while True:
        resp = requests.get(url, params=params)
        try:
            data = resp.json()
            if not isinstance(data, list) or not data:
                break
            for coin in data:
                mcap_list.append(
                    {
                        "cg_id": coin["id"],
                        "symbol_base": coin["symbol"].upper(),
                        "market_cap": coin.get("market_cap", 0),
                    }
                )
            params["page"] += 1
            time.sleep(1)
        except Exception:
            break
    return pd.DataFrame(mcap_list)


def match_symbols(binance_df, cg_df):
    # 從 BINANCE Symbol 中擷取 base symbol
    binance_df["symbol_base"] = binance_df["symbol"].str.replace(
        "USDT", "", regex=False
    )
    merged = pd.merge(binance_df, cg_df, on="symbol_base", how="inner")
    return merged


def plot_top_oi_ratio(df):
    # 先把 NaN 填成極小數避免除以零
    df = df.copy()
    df["market_cap"] = df["market_cap"].fillna(1)  # 避免除以 0
    df["oi_mcap_ratio"] = df["oi_value"] / df["market_cap"]
    df = df.sort_values("oi_mcap_ratio", ascending=False).head(TOP_N)

    plt.figure(figsize=(12, 6))
    bars = plt.bar(df["symbol"], df["oi_mcap_ratio"], color="skyblue", alpha=0.7)
    for bar in bars:
        yval = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            yval + 0.01,
            f"{yval:.4f}",
            ha="center",
            va="bottom",
        )
    plt.title("Top 5 Cryptocurrencies by OI/Market Cap Ratio")
    plt.xlabel("Cryptocurrency")
    plt.ylabel("OI / Market Cap Ratio")
    plt.xticks(rotation=30)
    plt.tight_layout()
    plt.show()


def main():
    oi_df = fetch_binance_oi_with_price()
    cg_df = fetch_coingecko_market_caps()
    full_df = match_symbols(oi_df, cg_df)

    # 合併不到的幣也要保留（outer join 模擬方式）
    full_df = pd.merge(
        oi_df, cg_df[["symbol_base", "market_cap"]], on="symbol_base", how="left"
    )

    full_df["oi_mcap_ratio"] = full_df["oi_value"] / full_df["market_cap"]
    full_df = full_df.sort_values("oi_mcap_ratio", ascending=False)

    # 匯出所有幣種（包含市值為 NaN 的）
    full_df.to_csv("oi_marketcap_all.csv", index=False)
    print("✅ 匯出完整資料：oi_marketcap_all.csv")

    # 僅畫出有市值資料者（避免 NaN 無法畫）
    plot_df = full_df[full_df["market_cap"].notna()].copy()
    plot_top_oi_ratio(plot_df)


if __name__ == "__main__":
    main()
