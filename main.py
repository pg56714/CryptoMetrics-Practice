import requests
from web3 import Web3
from eth_utils import to_checksum_address
import time

# 設定
RPC_URL = "https://mainnet.infura.io/v3/264e4f7f59274806b9f7cf5e88083c68"
w3 = Web3(Web3.HTTPProvider(RPC_URL))

OM_ADDRESS = to_checksum_address("0x2ba8349123de45e931a8c8264c332e6e9cf593f9")
TRANSFER_TOPIC = Web3.to_hex(w3.keccak(text="Transfer(address,address,uint256)"))

BINANCE_ADDRESSES = {
    to_checksum_address("0x28C6c06298d514Db089934071355E5743bf21d60"),
    to_checksum_address("0x21a31Ee1afC51d94C2eFcCAa2092aD1028285549"),
}

# 用「對應 USDT 價值」當作警報門檻
MIN_ALERT_USDT_VALUE = 50000  # 例如 5 萬 USDT


def get_om_price_usdt():
    try:
        resp = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=OMUSDT")
        data = resp.json()
        return float(data["price"])
    except Exception as e:
        print("❗ 無法取得 OM 價格：", e)
        return None


def monitor():
    print(
        f"📡 開始監控：若 OM 轉入 CEX 對應 > {MIN_ALERT_USDT_VALUE} USDT 就觸發警報..."
    )
    latest_block = w3.eth.block_number

    while True:
        try:
            current_block = w3.eth.block_number
            if current_block > latest_block:
                om_price = get_om_price_usdt()
                if om_price is None:
                    time.sleep(5)
                    continue

                for block_number in range(latest_block + 1, current_block + 1):
                    logs = w3.eth.get_logs(
                        {
                            "fromBlock": block_number,
                            "toBlock": block_number,
                            "address": OM_ADDRESS,
                            "topics": [TRANSFER_TOPIC],
                        }
                    )

                    for log in logs:
                        from_address = "0x" + log["topics"][1].hex()[-40:]
                        to_address = "0x" + log["topics"][2].hex()[-40:]
                        value = int(log["data"], 16)

                        to_address = to_checksum_address(to_address)
                        om_amount = value / 10**18
                        usdt_value = om_amount * om_price

                        if (
                            to_address in BINANCE_ADDRESSES
                            and usdt_value >= MIN_ALERT_USDT_VALUE
                        ):
                            print("🚨 發現大額轉入 CEX")
                            print(f"🔸 From: {from_address}")
                            print(f"🔸 To (Binance): {to_address}")
                            print(f"🔸 Amount: {om_amount:.2f} OM")
                            print(f"💰 對應市值：{usdt_value:.2f} USDT")
                            print(f"🔸 Block: {block_number}\n")

                latest_block = current_block
            time.sleep(3)

        except Exception as e:
            print("❗ 錯誤：", e)
            time.sleep(5)


if __name__ == "__main__":
    monitor()
