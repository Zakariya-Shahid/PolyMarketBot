from datetime import datetime, timedelta
import pandas as pd
import requests
import numpy as np

def find_probability(coin: str, expiration_date: str) -> float:
    strike = 32000
    today = datetime.today()
    ticker = coin + "USDT"

    # Get the current price using Binance US API
    url = f"https://api.binance.us/api/v3/ticker/price?symbol={ticker}"
    headers = {}
    response = requests.get(url, headers=headers)
    data = response.json()
    current_price = float(data.get("price", 0))  # Use get method with default value to handle KeyError

    if current_price == 0:
        print("Error: Unable to fetch the current price from Binance US API.")
        exit()

    factor = strike / current_price

    days_to_expiry = (datetime.strptime(expiration_date, "%m/%d/%Y") - today).days

    # Lists to store results for different historical timeframes
    results = []

    for years in [1]:
        days = years * 365
        start = today - timedelta(days=days)

        # Fetch historical price data from Binance US API
        url = f"https://api.binance.us/api/v1/klines?symbol={ticker}&interval=1d&startTime={int(start.timestamp())*1000}&endTime={int(today.timestamp())*1000}"
        response = requests.get(url, headers=headers)
        klines = response.json()

        # Convert the data to a pandas DataFrame
        df = pd.DataFrame(klines, columns=["timestamp", "open", "high", "low", "close", "volume", "close_time", "quote_asset_volume", "number_of_trades", "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"])

        # Convert the timestamp to a datetime object
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit='ms')

        # Convert the data to numeric values
        df["open"] = pd.to_numeric(df["open"])
        df["high"] = pd.to_numeric(df["high"])
        df["low"] = pd.to_numeric(df["low"])
        df["close"] = pd.to_numeric(df["close"])

        # Initialize lists to store ITM results for each row in the historical timeframe
        itm_at_expiry_list = []
        itm_before_expiry_list = []

        for i in range(len(df) - days_to_expiry):
            # Get the closing price at row i
            price_i = df["close"].iloc[i]

            # Get the closing price at days_to_expiry rows ahead
            closing_price_at_expiry = df["close"].iloc[i + days_to_expiry]

            # Check if the stock was ITM at the expiration date for this row
            itm_at_expiry = closing_price_at_expiry >= price_i * factor
            itm_at_expiry_list.append(itm_at_expiry)

        # Calculate the likelihood of ITM at Expiry and ITM before Expiry for this historical timeframe
        itm_at_expiry_likelihood = np.mean(itm_at_expiry_list)

        # Store the results for this historical timeframe
        results.append((days, itm_at_expiry_likelihood))


    print(f"Likelihood of ITM at Expiry: {results[0][1] * 100:.2f}%")
    return results[0][1]