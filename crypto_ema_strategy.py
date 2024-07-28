import ccxt
import pandas as pd
import numpy as np
import asyncio
import websockets
import json
import time

# Binance API credentials
API_KEY = 'jbzSqtPRcAk8CPb4u142bN6lBwu47cqLxFxzwVmJ086FaoWvjHW0gmWQzajjYFlc'
API_SECRET = 'pKwacZUGBtHiUyaOGFBmq7CQLc4zJrkCITz2ZtZO2vqaswWqWdzGuJ2gzGi6CvzT'

# Initialize Binance client
exchange = ccxt.binance({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'enableRateLimit': True,
})


# Fetching 15-minute historical data
def fetch_ohlcv(symbol):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe='15m')
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df


# Calculate the 5-period EMA
def calculate_ema(df):
    df['5EMA'] = df['close'].ewm(span=5, adjust=False).mean()
    return df


# Place a buy order
def place_buy_order(symbol, amount):
    order = exchange.create_market_buy_order(symbol, amount)
    print(f"Buy Order placed: {order}")


# Place a sell order
def place_sell_order(symbol, amount):
    order = exchange.create_market_sell_order(symbol, amount)
    print(f"Sell Order placed: {order}")


# Process incoming WebSocket messages
async def process_message(message, df, symbol, amount):
    data = json.loads(message)
    price = float(data['c'])

    # Fetching latest historical data and calculating 5EMA
    df = fetch_ohlcv(symbol)
    df = calculate_ema(df)

    latest_ema = df['5EMA'].iloc[-1]
    print(f"Latest EMA: {latest_ema}, Current Price: {price}")

    # Your strategy logic here
    # e.g., Buy if price crosses above EMA, sell if it crosses below
    if price > latest_ema:
        place_buy_order(symbol, amount)
    elif price < latest_ema:
        place_sell_order(symbol, amount)


# Subscribe to the market feed WebSocket
async def subscribe_to_websocket(symbol, amount):
    uri = f"wss://stream.binance.com:9443/ws/{symbol.lower()}@ticker"
    async with websockets.connect(uri) as websocket:
        while True:
            message = await websocket.recv()
            df = fetch_ohlcv(symbol)
            await process_message(message, df, symbol, amount)


# Main function to start the process
def main():
    symbol = 'BTC/USDT'  # Change this to your desired trading pair
    amount = 0.001  # Change this to your desired trade amount
    df = fetch_ohlcv(symbol)
    # asyncio.get_event_loop().run_until_complete(subscribe_to_websocket(symbol, amount))


if __name__ == "__main__":
    main()
