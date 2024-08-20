import ccxt
import pandas as pd
import time
from datetime import datetime, timedelta

# Initialize the Binance exchange
exchange = ccxt.binance()

# Define the symbol and timeframe
symbol = 'BTC/USDT'
timeframe = '15m'  # 15-minute interval

# Calculate the timestamp for 6 months ago
now = datetime.utcnow()
since = exchange.parse8601((now - timedelta(days=180)).isoformat())

# Function to fetch historical data
def fetch_ohlcv(symbol, timeframe, since, limit=1000):
    all_data = []
    while since < exchange.parse8601(datetime.utcnow().isoformat()):
        data = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
        if len(data) == 0:
            break
        all_data += data
        since = data[-1][0] + 1  # Move to the next set of data
        time.sleep(exchange.rateLimit / 1000)  # Respect rate limit
    return all_data

# Fetch data
ohlcv = fetch_ohlcv(symbol, timeframe, since)

# Convert to a DataFrame
df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

# Convert timestamp to datetime
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

# Print the DataFrame
print(df.head())
print(df.tail())

# Save to CSV if needed
# df.to_csv('btc_usdt_15m_last_6_months.csv', index=False)
