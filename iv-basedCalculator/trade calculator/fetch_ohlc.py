"""
Fetch OHLC data for Indian stocks for a specific date
"""

import yfinance as yf
from datetime import datetime, timedelta
import argparse

def fetch_ohlc(symbol, date_str):
    try:
        # Add .NS suffix if not present
        if not (symbol.endswith('.NS') or symbol.endswith('.BO')):
            symbol = f"{symbol}.NS"
            
        # Parse the date
        date = datetime.strptime(date_str, '%Y-%m-%d')
        
        # Create ticker object
        stock = yf.Ticker(symbol)
        
        # Fetch data for the specific date
        # We fetch one day before and after to ensure we get the date we want
        start_date = date - timedelta(days=1)
        end_date = date + timedelta(days=1)
        hist = stock.history(start=start_date, end=end_date)
        
        # Get data for the specific date
        date_str = date.strftime('%Y-%m-%d')
        if date_str in hist.index.strftime('%Y-%m-%d').values:
            data = hist[hist.index.strftime('%Y-%m-%d') == date_str].iloc[0]
            
            print(f"\nOHLC Data for {symbol} on {date_str}:")
            print(f"Open:   ₹{data['Open']:.2f}")
            print(f"High:   ₹{data['High']:.2f}")
            print(f"Low:    ₹{data['Low']:.2f}")
            print(f"Close:  ₹{data['Close']:.2f}")
            print(f"Volume: {int(data['Volume']):,}")
            
            # Calculate day's movement
            day_change = ((data['Close'] - data['Open']) / data['Open']) * 100
            day_range = ((data['High'] - data['Low']) / data['Low']) * 100
            
            print(f"\nDay's Analysis:")
            print(f"Change:    {day_change:+.2f}%")
            print(f"Range:     {day_range:.2f}%")
            
        else:
            print(f"\nNo data available for {symbol} on {date_str}")
            print("Note: This might be due to a market holiday or weekend")
            
    except Exception as e:
        print(f"\nError processing {symbol}: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Fetch OHLC data for Indian stocks')
    parser.add_argument('symbol', help='Stock symbol (e.g., RELIANCE or RELIANCE.NS)')
    parser.add_argument('date', help='Date in YYYY-MM-DD format')
    
    args = parser.parse_args()
    fetch_ohlc(args.symbol, args.date)

if __name__ == "__main__":
    main()
