from web3 import Web3
from eth_utils import to_checksum_address
import datetime
import requests
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

matplotlib.rcParams["font.family"] = "Microsoft JhengHei"

# === 設定區 ===
RPC_URL = "https://mainnet.infura.io/v3/YOURAPIKEY"
w3 = Web3(Web3.HTTPProvider(RPC_URL))

OM_ADDRESS = to_checksum_address("0x2ba8349123de45e931a8c8264c332e6e9cf593f9")
TRANSFER_TOPIC = Web3.to_hex(w3.keccak(text="Transfer(address,address,uint256)"))
DECIMALS = 10**18
BLOCKS_PER_DAY = int((24 * 60 * 60) / 12)  # 約 7200 blocks/day

# 設定往回幾天
LOOKBACK_DAYS = 3


def get_price_usdt():
    try:
        resp = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=OMUSDT")
        return float(resp.json()["price"])
    except Exception:
        return None


def get_timestamp(block_number):
    return w3.eth.get_block(block_number)["timestamp"]


def fetch_logs(days=LOOKBACK_DAYS):
    end_block = w3.eth.block_number
    start_block = end_block - days * BLOCKS_PER_DAY
    try:
        logs = w3.eth.get_logs(
            {
                "fromBlock": start_block,
                "toBlock": end_block,
                "address": OM_ADDRESS,
                "topics": [TRANSFER_TOPIC],
            }
        )
        return logs
    except Exception as e:
        print(f"❗ 無法讀取 logs: {e}")
        return []


def find_alerts(min_usdt=100000):
    logs = fetch_logs()
    price = get_price_usdt()
    if not price:
        print("❌ 無法取得即時價格")
        return []

    alerts = []
    for log in logs:
        try:
            if len(log["topics"]) < 3:
                continue
            from_addr = "0x" + log["topics"][1].hex()[-40:]
            to_addr = "0x" + log["topics"][2].hex()[-40:]
            value_hex = log["data"]
            if isinstance(value_hex, bytes):
                value_hex = value_hex.hex()
            value = int(value_hex, 16)
            om_amount = value / DECIMALS
            usdt_value = om_amount * price
            if usdt_value < min_usdt:
                continue  # 🔒 篩掉小額轉帳

            ts = get_timestamp(log["blockNumber"])
            alerts.append(
                {
                    "from": from_addr,
                    "to": to_addr,
                    "amount": om_amount,
                    "usdt": usdt_value,
                    "timestamp": ts,
                }
            )

            print(
                f"📦 {om_amount:.2f} OM（約 {usdt_value:.2f} USDT）from {from_addr[:6]} → {to_addr[:6]}"
            )

        except Exception as e:
            print(f"⚠️ 略過 log：{e}")
            continue

    print(f"📊 總共偵測到 {len(alerts)} 筆 OM 轉帳")
    return alerts


def fetch_omusdt_klines(interval="1h", limit=100):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": "OMUSDT", "interval": interval, "limit": limit}
    data = requests.get(url, params=params).json()
    return [
        {"time": datetime.datetime.fromtimestamp(k[0] / 1000), "close": float(k[4])}
        for k in data
    ]


def plot_alerts_on_chart(alert_list):
    klines = fetch_omusdt_klines()
    times = [k["time"] for k in klines]
    closes = [k["close"] for k in klines]

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.set_title("OMUSDT 價格圖（含轉帳時間點）")
    ax.plot(times, closes, label="Close Price", color="blue")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M"))

    for alert in alert_list:
        t = datetime.datetime.fromtimestamp(alert["timestamp"])
        ax.axvline(x=t, color="red", linestyle="--")
        ax.text(
            t,
            max(closes),
            f"{alert['usdt']:.0f} USDT",
            rotation=90,
            fontsize=8,
            color="red",
        )

    ax.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


def save_alerts_to_csv(alerts, filename="om_alerts.csv"):
    if not alerts:
        print("⚠️ 沒有可輸出的轉帳資料")
        return
    df = pd.DataFrame(alerts)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
    df.to_csv(filename, index=False)
    print(f"✅ 已寫入 {len(df)} 筆到 {filename}")


# 主程式
alerts = find_alerts()
plot_alerts_on_chart(alerts)
save_alerts_to_csv(alerts)
