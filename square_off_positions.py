# square_off_positions.py
import time
import traceback
import ccxt

# Binance API credentials (same as main script)
API_KEY = 'jbzSqtPRcAk8CPb4u142bN6lBwu47cqLxFxzwVmJ086FaoWvjHW0gmWQzajjYFlc'
API_SECRET = 'pKwacZUGBtHiUyaOGFBmq7CQLc4zJrkCITz2ZtZO2vqaswWqWdzGuJ2gzGi6CvzT'

# Initialize Binance client
exchange = ccxt.binance({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'enableRateLimit': True,
    'options': {
        'adjustForTimeDifference': True
    }
})


def fetch_current_price(symbol):
    try:
        ticker = exchange.fetch_ticker(symbol)
        return ticker['last']
    except Exception as e:
        print(f"Error fetching price for {symbol}: {e}")
        return None


def get_funding_wallet_balance(asset):
    try:
        response = exchange.sapiPostAssetGetFundingAsset(params={"asset": asset})
        if isinstance(response, list):
            for balance in response:
                if balance['asset'] == asset:
                    return float(balance['free'])
        return 0
    except Exception as e:
        print(f"Error fetching funding balance: {e}")
        return 0


def transfer_to_funding(asset, amount):
    try:
        response = exchange.sapi_post_asset_transfer({
            "type": "MAIN_FUNDING",
            "asset": asset,
            "amount": amount
        })
        print(f"Transferred to funding: {response}")
        return True
    except Exception as e:
        print(f"Transfer to funding failed: {e}")
        return False


def transfer_to_spot(asset, amount):
    try:
        response = exchange.sapi_post_asset_transfer({
            "type": "FUNDING_MAIN",
            "asset": asset,
            "amount": amount
        })
        print(f"Transferred to spot: {response}")
        return True
    except Exception as e:
        print(f"Transfer to spot failed: {e}")
        return False


def convert_asset_to_usdt(asset):
    try:
        asset_balance = get_funding_wallet_balance(asset)
        if asset_balance <= 0:
            return 0

        quote_params = {
            "fromAsset": asset,
            "toAsset": "USDT",
            "fromAmount": asset_balance,
            "walletType": "FUNDING"
        }
        quote_response = exchange.sapiPostConvertGetQuote(quote_params)
        quote_id = quote_response["quoteId"]
        time.sleep(2)

        accept_params = {"quoteId": quote_id}
        conversion_response = exchange.sapiPostConvertAcceptQuote(accept_params)
        time.sleep(2)

        return get_funding_wallet_balance("USDT")
    except Exception as e:
        print(f"Conversion failed: {e}")
        return 0


def square_off_position(asset):
    try:
        balance = exchange.fetch_balance()
        available_balance = balance['free'].get(asset, 0)
        if available_balance <= 0:
            return

        if transfer_to_funding(asset, available_balance):
            time.sleep(5)
            usdt_available = convert_asset_to_usdt(asset)
            if usdt_available > 0:
                transfer_to_spot("USDT", usdt_available)
    except Exception as e:
        print(f"Square-off error: {e}")
        traceback.print_exc()


def calculate_returns_from_trade_history(asset, current_price):
    try:
        trades = exchange.fetch_my_trades(asset + "/USDT")
        total_cost = 0.0
        total_amount = 0.0

        for trade in trades:
            total_cost += trade['amount'] * trade['price']
            total_amount += trade['amount']

        if total_amount == 0:
            return None

        average_price = total_cost / total_amount
        current_value = total_amount * current_price
        returns = ((current_value - total_cost) / total_cost) * 100

        return {
            'asset': asset,
            'average_price': average_price,
            'total_amount': total_amount,
            'returns_percentage': returns
        }
    except Exception as e:
        print(f"Returns calculation error: {e}")
        return None


def check_and_square_off_positions():
    try:
        print(f"\n{'=' * 40}")
        print(f"Checking positions at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        open_positions = exchange.fetch_balance()['total']

        for asset, amount in open_positions.items():
            if amount > 0 and asset != 'USDT':
                print(f"\nProcessing {asset}")
                current_price = fetch_current_price(asset + "/USDT")
                if not current_price:
                    continue

                result = calculate_returns_from_trade_history(asset, current_price)
                if not result:
                    continue

                print(f"Current returns: {result['returns_percentage']:.2f}%")
                if result['returns_percentage'] > 5:
                    print("Triggering square-off...")
                    square_off_position(asset)
        print(f"{'=' * 40}\n")
    except Exception as e:
        print(f"Main check error: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    check_and_square_off_positions()