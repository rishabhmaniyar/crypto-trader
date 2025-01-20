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
    url = "https://fda.forbes.com/v2/tradedAssets?limit=100&pageNum=1&sortBy=marketCap&direction=desc&query=&category=ft"
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
            try:
                ltp = float(exchange.fetch_ticker(ticker).get("last"))
                threeMonthHistoricalData = fetch_ohlcv(ticker)
                (latest20Dma, threeMonthClose) = get20DmaValueForCrypto(threeMonthHistoricalData)
                count += 1
            except Exception as e:
                latest20Dma = None
                ltp = None
                threeMonthClose = None
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


# Fetch open positions or holdings
def fetch_open_positions():
    try:
        # Fetch balance from Binance account
        balance = exchange.fetch_balance()
        open_positions = []
        for asset, details in balance['total'].items():
            if details > 0:  # Non-zero balance
                open_positions.append({
                    'asset': asset,
                    'amount': details,
                    'value': balance['free'][asset]
                })
        return open_positions
    except Exception as e:
        print("Error fetching open positions:", traceback.print_exception(e))
        return []


# Fetch the current price of a coin
def fetch_current_price(symbol):
    try:
        ticker = exchange.fetch_ticker(symbol)
        return ticker['last']
    except Exception as e:
        print(f"Error fetching price for {symbol}: {e}")
        return None


# Calculate returns for each position
def calculate_returns(open_positions):
    positions_with_returns = []
    for position in open_positions:
        symbol = position['asset'] + "/USDT"
        current_price = fetch_current_price(symbol)
        if current_price:
            # Calculate current value based on current market price
            current_value = position['amount'] * current_price

            # Use `value` from `fetch_balance` as an approximation of the initial value
            # NOTE: Ideally, you should calculate `initial_value` from transaction history
            initial_value = position['amount'] * position['value']  # Approximation

            # Avoid division by zero and incorrect data
            if initial_value > 0:
                returns = ((current_value - initial_value) / initial_value) * 100
            else:
                returns = 0.0

            # Append the position with calculated details
            positions_with_returns.append({
                'symbol': symbol,
                'amount': position['amount'],
                'current_price': current_price,
                'initial_value': initial_value,
                'current_value': current_value,
                'returns': returns
            })
        else:
            print(f"Could not fetch current price for {symbol}. Skipping...")
    return positions_with_returns


# Square off positions with returns greater than 15%
def square_off_position(asset, total_amount):
    try:
        # Fetch the latest balance for the asset
        balance = exchange.fetch_balance()
        available_balance = balance['free'].get(asset, 0)

        if available_balance <= 0:
            print(f"No available balance for {asset}. Skipping square-off.")
            return

        # Load market data for precision and limits
        markets = exchange.load_markets()
        market_data = markets[asset + "/USDT"]
        amount_precision = int(market_data['precision']['amount'])
        price_precision = int(market_data['precision']['price'])
        min_notional = float(market_data['limits']['cost']['min'])

        # Use the smaller of total_amount and available_balance
        total_amount = min(total_amount, available_balance)
        total_amount_rounded = round(total_amount, amount_precision)

        # Fetch the current price
        current_price = fetch_current_price(asset + "/USDT")
        if not current_price:
            print(f"Could not fetch current price for {asset}. Skipping square-off.")
            return

        # Calculate the notional value
        notional_value = current_price * total_amount

        # Ensure the notional value meets the minimum requirement
        if notional_value < min_notional:
            adjusted_amount = round(min_notional / current_price, amount_precision)
            if adjusted_amount <= available_balance:
                print(
                    f"Adjusting sell amount for {asset} to meet minimum notional value: Requested={total_amount}, Adjusted={adjusted_amount}"
                )
                total_amount_rounded = adjusted_amount
            else:
                print(
                    f"Cannot adjust sell amount for {asset}. Insufficient balance. "
                    f"Available={available_balance}, Required={adjusted_amount}."
                )
                return

        # Create a limit sell order slightly below the current price (e.g., 0.5% below)
        limit_price = round(current_price * 0.995, price_precision)

        # Check the adjusted notional value again before placing the order
        adjusted_notional_value = total_amount_rounded * limit_price
        if adjusted_notional_value >= min_notional:
            print(
                f"Placing limit sell order for {asset}: "
                f"Amount={total_amount}, Price={limit_price}, Available Balance ={available_balance}"
            )
            # order = exchange.create_limit_sell_order(
            #     asset + "/USDT", total_amount, limit_price
            # )

            order = exchange.create_market_sell_order(
                asset + "/USDT", available_balance
            )
            print(f"Square-off order placed for {asset}: {order}")
        else:
            print(
                f"Adjusted order notional value still too low for {asset}: "
                f"{adjusted_notional_value} < {min_notional}. No action taken."
            )

    except ccxt.InsufficientFunds as e:
        print(f"Insufficient funds for {asset}: {e}")
    except Exception as e:
        print(f"Error squaring off position for {asset}: {e}")
        traceback.print_exc()


def calculate_returns_from_trade_history(asset, current_price):
    try:
        # Fetch trade history for the given asset
        trades = exchange.fetch_my_trades(asset + "/USDT")

        # Calculate total cost and total amount
        total_cost = 0.0
        total_amount = 0.0

        for trade in trades:
            total_cost += trade['amount'] * trade['price']  # Amount * Price
            total_amount += trade['amount']  # Sum up all amounts traded

        if total_amount == 0:
            print(f"No trade history available for {asset}")
            return None

        # Calculate weighted average price
        average_price = total_cost / total_amount

        # Calculate current value
        current_value = total_amount * current_price

        # Calculate returns
        returns = ((current_value - total_cost) / total_cost) * 100

        return {
            'asset': asset,
            'average_price': average_price,
            'total_amount': total_amount,
            'total_cost': total_cost,
            'current_value': current_value,
            'returns_percentage': returns
        }
    except Exception as e:
        print(f"Error calculating returns for {asset}: {e}")
        traceback.print_exc()
        return None


def check_and_square_off_positions():
    open_positions = exchange.fetch_balance()['total']
    for asset, amount in open_positions.items():
        if amount > 0 and asset != 'USDT':  # Check non-zero positions excluding USDT
            print(f"Processing asset: {asset}, Amount: {amount}")
            current_price = fetch_current_price(asset + "/USDT")
            if current_price:
                result = calculate_returns_from_trade_history(asset, current_price)
                if result:
                    print(f"Asset: {result['asset']}")
                    print(f"Average Price: {result['average_price']}")
                    print(f"Total Amount: {result['total_amount']}")
                    print(f"Total Cost: {result['total_cost']}")
                    print(f"Current Value: {result['current_value']}")
                    print(f"Returns (%): {result['returns_percentage']}%")

                    # Square off if returns > 5%
                    if result['returns_percentage'] > 5:
                        print(f"Square-off triggered for {asset}")
                        square_off_position(asset, result['total_amount'])
                    else:
                        print(f"Returns for {asset} are below 15%. No action taken.\n")
                else:
                    print(f"Could not calculate returns for {asset}\n")
            else:
                print(f"Could not fetch current price for {asset}\n")


# Updated main function
def main():
    # Existing logic
    filteredCryptos = getTopCryptosFromWeb()
    df = pd.DataFrame(filteredCryptos)
    print(df)
    newDf = addTwentyDmaData(df)
    print(newDf)
    newDf.to_csv("all-crypto.csv")
    result = findTradableEtf(newDf)
    print(result)

    try:
        check_and_square_off_positions()
    except Exception as e:
        print("Something went wrong while selling due to --", e)

    amount = 500
    order = place_buy_order(result.head(1)['ticker'].values[0], amount)
    print(order)


if __name__ == "__main__":
    main()