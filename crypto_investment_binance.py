import ssl
import traceback

import ccxt
import pandas as pd
import requests
import numpy as np
import asyncio
import websockets
import json
from datetime import datetime, timedelta

# Binance API credentials
API_KEY = 'jbzSqtPRcAk8CPb4u142bN6lBwu47cqLxFxzwVmJ086FaoWvjHW0gmWQzajjYFlc'
API_SECRET = 'pKwacZUGBtHiUyaOGFBmq7CQLc4zJrkCITz2ZtZO2vqaswWqWdzGuJ2gzGi6CvzT'

# API_KEY = 'aSm4URx4S5MCIhnlRGmsOLs0bsMDsmuLMJPhMnlkOO0yg9gqFwHAXFIVbQR1MBLN'
# API_SECRET = 'zE1WCQ4uSbhfkJBaTrNRtCoJPjUy3Ap0G0ek5Mxlm1d0rgAmllobBrTvK433w4aT'

# Initialize Binance client
exchange = ccxt.binance({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'enableRateLimit': True,
    'options': {
        'adjustForTimeDifference': True
    }
})


# Fetching 15-minute historical data
def fetch_ohlcv(symbol):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1d', limit=90)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df


# Calculate the 5-period EMA
def calculate_ema(df):
    df['5EMA'] = df['close'].ewm(span=5, adjust=False).mean()
    return df


# Place a buy order
def place_buy_order(symbolTop, inr_amount=500):
    # Fetch the current price of the symbol
    print("place_buy_order :- ", symbolTop)
    ticker = exchange.fetch_ticker(symbolTop)
    current_price = ticker['last']

    # Calculate the amount to buy so that the total cost is near ₹500
    amount_to_buy = inr_amount / (current_price * 83)

    print(f"Buy Order placed for {symbolTop}")
    print(f"Amount: {amount_to_buy}, Total Cost: {amount_to_buy * current_price} INR")

    # Place a market buy order with the calculated amount
    order = exchange.create_market_buy_order(symbolTop, amount_to_buy)
    print("ORDER -> ", order)
    return order


# Place a sell order
def place_sell_order(symbol, amount):
    order = exchange.create_market_sell_order(symbol, amount)
    print(f"Sell Order placed: {order}")


# Main function to start the process
def getTopCryptosFromWeb():
    url = "https://fda.forbes.com/v2/tradedAssets?limit=300&pageNum=1&sortBy=marketCap&direction=desc&query=&category=ft"
    response = requests.get(url)
    jsonResponse = json.loads(response.content)
    return jsonResponse["assets"]


def get20DmaValueForCrypto(df):
    df['close'] = pd.to_numeric(df['close'], errors='coerce')

    # Calculate the 20-day moving average (DMA)
    df['20DMA'] = df['close'].rolling(window=20).mean()
    # print(df.tail(5))

    # Get the latest 20 DMA value
    latest_20dma = df['20DMA'].iloc[-1]

    return latest_20dma, df['close'].iloc[0]


def addTwentyDmaData(df):
    global latest20Dma, threeMonthClose, ltp
    count = 0
    for index, row in df.iterrows():
        if count <= 100:
            symbol = row['displaySymbol'].upper()
            ticker = symbol + "/USDT"
            if ticker=="WETH/USDT":
                print("check things here")
            try:
                ltp = float(exchange.fetch_ticker(ticker).get("last"))
                threeMonthHistoricalData = fetch_ohlcv(ticker)
                (latest20Dma, threeMonthClose) = get20DmaValueForCrypto(threeMonthHistoricalData)
                count += 1
            except Exception as e:
                latest20Dma=None
                ltp =None
                threeMonthClose=None
                print("Error during ->", symbol, traceback.print_exception(e))

            print(symbol, latest20Dma, ltp, threeMonthClose)

            if latest20Dma is not None:
                df.at[index, '20DMA'] = latest20Dma
                df.at[index, 'CMP-20DMA'] = ltp - latest20Dma
                df.at[index, 'CMP-20DMA_%'] = ((ltp - latest20Dma) / ltp) * 100
                df.at[index, '3m_change%'] = ((ltp - threeMonthClose) / threeMonthClose) * 100
                df.at[index, 'ticker'] = ticker

            else:
                df.at[index, '20DMA'] = 0.0
                df.at[index, 'CMP-20DMA'] = 0.0
                df.at[index, 'CMP-20DMA_%'] = 0.0
                df.at[index, '3m_change%'] = 0.0

        else:
            break
            # df = df.dropna(subset=['20DMA'])
            # df = df.drop(['isMunicipalBond', 'quotepreopenstatus', 'industry', 'assets','tempSuspendedSeries'], axis=1)
            # print(symbol, df)

    return df


def findTradableEtf(df):
    newEtfs = df.loc[df['3m_change%'] > 10]
    newEtfs = newEtfs.sort_values('CMP-20DMA_%', ascending=True)
    print("Saving to new file")
    newEtfs.to_csv("binance-etf.csv")
    return newEtfs


def main():
    # df = fetch_ohlcv(symbol)
    # print(df)
    filteredCryptos = getTopCryptosFromWeb()
    df = pd.DataFrame(filteredCryptos)
    print(df)
    newDf = addTwentyDmaData(df)
    print(newDf)
    newDf.to_csv("all-crypto.csv")
    result = findTradableEtf(newDf)
    print(result)
    amount = 500
    order = place_buy_order(result.head(1)['ticker'].values[0], amount)
    print(order)


if __name__ == "__main__":
    main()
