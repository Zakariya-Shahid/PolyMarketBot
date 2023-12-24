from datetime import datetime
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
from py_clob_client.clob_types import ApiCreds, OrderArgs, OrderType, FilterParams
from py_clob_client.order_builder.constants import BUY, SELL
from prob import find_probability
from time import sleep
import math

def create_order(price: float, size: float, side: str, token_id: str, order_type: str = OrderType.GTC):
    order_args = OrderArgs(
        price=price,
        size=size,
        side=side,
        token_id=token_id,
    )
    signed_order = client.create_order(order_args)
    resp = client.post_order(signed_order, order_type)    
    return resp

def filter_by_exp_and_coin(data: list[dict], coin: str, expiration_date: str) -> list:
    filtered_data = []
    for market in data:
        if market["end_date_iso"] == expiration_date and coin.lower() in market["question"].lower():
            filtered_data.append(market)
    return filtered_data

def filter_tokens_by_outcome(tokens: list[dict], outcome: str = "Yes") -> str or None:
    for token in tokens:
        if token['outcome'] == outcome:
            return token['token_id']
    return None

def convert_date_format(date: str) -> str:
    try:
        return datetime.strptime(date, "%m/%d/%Y").strftime("%Y-%m-%d")
    except ValueError:
        print("Invalid date format")
        return None

def connect():
    host: str = "https://clob.polymarket.com"
    key: str = "your key here"
    chain_id: int = POLYGON
    creds = ApiCreds(
        api_key="your API key",
        api_secret="api secret here",
        api_passphrase="passpharase here"
    )
    client = ClobClient(host, key=key, chain_id=chain_id, creds=creds)

    return client

def get_filtered_market(client: ClobClient, coin: str, expiration_date: str) -> list:
    data = client.get_markets()
    next_cursor = data["next_cursor"]
    data = data["data"]
    filtered_data = filter_by_exp_and_coin(data, coin, expiration_date)

    while next_cursor != "LTE=":
        data = client.get_markets(next_cursor=next_cursor)
        next_cursor = data["next_cursor"]
        data = data["data"]
        filtered_data.extend(filter_by_exp_and_coin(data, coin, expiration_date))

    return filtered_data

def filter_orders_by_market_id(orders: list[dict], market_id: str) -> list:
    filtered_orders = []
    for order in orders:
        if order["market"] == market_id:
            filtered_orders.append(order)
    return filtered_orders

coin = input("Enter coin: ")
expiration_date_prob = input("Enter expiration date (MM/DD/YYYY): ")
expiration_date_poly = convert_date_format(expiration_date_prob)

size = float(input("Enter size: "))
lower_bound = float(input("Enter lower bound: "))
upper_bound = float(input("Enter upper bound: "))
waiting_time = float(input("Enter waiting time: "))

client = connect()

while True:
    probability = find_probability(coin, expiration_date_prob)
    filtered_markets = get_filtered_market(client, coin, expiration_date_poly)

    if len(filtered_markets) != 1:
        sleep(waiting_time)
        continue

    for market in filtered_markets:
        buy_price_yes = probability - lower_bound
        buy_price_no = 1 - probability - lower_bound
        yes_token = filter_tokens_by_outcome(market["tokens"])
        no_token = filter_tokens_by_outcome(market["tokens"], "No")

        previous_orders = client.get_orders(
            params=FilterParams(
                market=market["condition_id"]
            )
        )
        yes_count = 0
        no_count = 0
        for order in previous_orders:
            if order["side"] == BUY and order['asset_id'] == no_token and float(order["price"]) > buy_price_no:
                client.cancel(order["id"])

            elif order["side"] == BUY and order['asset_id'] == yes_token and float(order["price"]) > buy_price_yes:
                client.cancel(order["id"])

            if order["side"] == BUY and order['asset_id'] == no_token:
                no_count += 1

            elif order["side"] == BUY and order['asset_id'] == yes_token:
                yes_count += 1

        # BUY
        # checking if round down to 2 decimal places is equal to the number itself or if there are no orders
        if math.floor(buy_price_yes * 100) / 100 == buy_price_yes or yes_count == 0:
            create_order(buy_price_yes, size, BUY, yes_token)
        if math.floor(buy_price_no * 100) / 100 == buy_price_no or no_count == 0:
            create_order(buy_price_no, size, BUY, no_token)

        # SELL
        # create_order(probability + upper_bound, size, SELL, filter_tokens_by_outcome(market["tokens"]))
        # create_order(1 - probability + upper_bound, size, SELL, filter_tokens_by_outcome(market["tokens"], "No"))

                
    sleep(waiting_time)
