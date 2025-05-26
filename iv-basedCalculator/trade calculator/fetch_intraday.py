"""
Fetch daily OHLC data for Indian stocks using direct API calls
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import argparse
import time

def get_stock_data(symbol, start_date, end_date, max_retries=3):
    """Fetch stock data directly from Yahoo Finance API"""
    # Convert dates to UNIX timestamps
    start_timestamp = int(time.mktime(start_date.timetuple()))
    end_timestamp = int(time.mktime(end_date.timetuple()))

    # Construct URL
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {
        "period1": start_timestamp,
        "period2": end_timestamp,
        "interval": "1d",
        "events": "history"
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    # Suppress SSL warnings
    requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

    # Create a session for connection pooling
    session = requests.Session()
    session.verify = False  # Disable SSL verification

    # Retry logic
    for attempt in range(max_retries):
        try:
            response = session.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()  # Raise an error for bad status codes
            data = response.json()
            break
        except (requests.exceptions.RequestException, ValueError) as e:
            if attempt == max_retries - 1:  # Last attempt
                print(f"\nError after {max_retries} attempts: {str(e)}")
                return None
            print(f"\nRetry {attempt + 1}/{max_retries} after error: {str(e)}")
            time.sleep(1)  # Wait before retrying

    if "chart" not in data or "result" not in data["chart"] or not data["chart"]["result"]:
        return None

    result = data["chart"]["result"][0]
    timestamps = result["timestamp"]
    quote = result["indicators"]["quote"][0]

    df = pd.DataFrame({
        "Open": quote.get("open", []),
        "High": quote.get("high", []),
        "Low": quote.get("low", []),
        "Close": quote.get("close", []),
        "Volume": quote.get("volume", [])
    }, index=pd.to_datetime([datetime.fromtimestamp(x) for x in timestamps]))

    return df

def fetch_intraday(symbol, date_str, interval=None):  # interval param kept for compatibility
    try:
        # Add .NS suffix if not present
        if not (symbol.endswith('.NS') or symbol.endswith('.BO')):
            symbol = f"{symbol}.NS"

        # Parse the date
        date = datetime.strptime(date_str, '%Y-%m-%d')

        # Fetch 60 days before and after for sufficient data
        start_date = date - timedelta(days=60)
        end_date = date + timedelta(days=60)

        print(f"\nFetching daily data for {symbol} from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        hist = get_stock_data(symbol, start_date, end_date)

        if hist.empty:
            print(f"\nNo data available for {symbol}")
            return None

        # Filter for the specific date
        date_str = date.strftime('%Y-%m-%d')
        print(f"\nDebug: Looking for date {date_str}")
        print(f"Debug: Available dates in data: {hist.index.strftime('%Y-%m-%d').unique().tolist()}")

        day_data = hist[hist.index.strftime('%Y-%m-%d') == date_str]
        print(f"Debug: Found {len(day_data)} rows for target date")

        if day_data.empty:
            print(f"\nNo data available for {symbol} on {date_str}")
            print("Note: This might be due to a market holiday or weekend")
            return None

        # Verify target date exists in data before returning full history
        if not day_data.empty:
            print(f"Debug: Found data for target date, returning full history")
            return hist
        return None

    except Exception as e:
        print(f"\nError processing {symbol}: {str(e)}")
        return None

def print_data(symbol, date_str, data):
    """Print formatted OHLC data"""
    if data is None or data.empty:
        return

    print(f"\nDaily OHLC Data for {symbol} on {date_str}:")
    print("Date          Open     High     Low      Close    Volume")
    print("-" * 65)

    for idx, row in data.iterrows():
        date_str = idx.strftime('%Y-%m-%d')
        print(f"{date_str}    ₹{row['Open']:<8.2f}₹{row['High']:<8.2f}₹{row['Low']:<8.2f}₹{row['Close']:<8.2f}{int(row['Volume']):,}")

    # Calculate period statistics
    period_open = data.iloc[0]['Open']
    period_close = data.iloc[-1]['Close']
    period_high = data['High'].max()
    period_low = data['Low'].min()
    total_volume = data['Volume'].sum()

    period_change = ((period_close - period_open) / period_open) * 100
    period_range = ((period_high - period_low) / period_low) * 100

    print(f"\nPeriod Summary:")
    print(f"Open:          ₹{period_open:.2f}")
    print(f"High:          ₹{period_high:.2f}")
    print(f"Low:           ₹{period_low:.2f}")
    print(f"Close:         ₹{period_close:.2f}")
    print(f"Total Volume:  {int(total_volume):,}")
    print(f"Change:        {period_change:+.2f}%")
    print(f"Range:         {period_range:.2f}%")

def main():
    parser = argparse.ArgumentParser(description='Fetch daily OHLC data for Indian stocks')
    parser.add_argument('symbol', help='Stock symbol (e.g., RELIANCE or RELIANCE.NS)')
    parser.add_argument('date', help='Date in YYYY-MM-DD format')

    args = parser.parse_args()
    data = fetch_intraday(args.symbol, args.date)
    if data is not None:
        print_data(args.symbol, args.date, data)

if __name__ == "__main__":
    main()
