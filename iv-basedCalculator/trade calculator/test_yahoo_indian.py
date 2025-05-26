"""
Simple test script to verify yfinance functionality with Indian stocks
"""

import yfinance as yf
from datetime import datetime, timedelta

def test_indian_stocks():
    # Test stocks (some major Indian companies)
    test_symbols = [
        "RELIANCE.NS",  # Reliance Industries
        "TCS.NS",       # Tata Consultancy Services
        "INFY.NS",      # Infosys
        "HDFCBANK.NS"   # HDFC Bank
    ]
    
    print("Testing yfinance with Indian stocks...\n")
    
    for symbol in test_symbols:
        try:
            print(f"\nTesting {symbol}:")
            stock = yf.Ticker(symbol)
            
            # Test basic info
            print("1. Fetching basic info...")
            info = stock.info
            print(f"Company Name: {info.get('longName', 'N/A')}")
            print(f"Current Price: {info.get('currentPrice', 'N/A')}")
            
            # Test historical data
            print("\n2. Fetching historical data...")
            hist = stock.history(period="5d")
            print(f"Last 5 days of data available: {not hist.empty}")
            if not hist.empty:
                print(f"Latest close price: {hist['Close'].iloc[-1]:.2f}")  # Fixed deprecation warning
            
            # Test historical volatility calculation
            print("\n3. Calculating 30-day historical volatility...")
            hist_30d = stock.history(period="60d")
            if not hist_30d.empty:
                daily_returns = hist_30d['Close'].pct_change().dropna()
                annual_volatility = daily_returns.std() * (252 ** 0.5)  # Annualized volatility
                print(f"30-day Historical Volatility: {annual_volatility:.2%}")
            
            print("\n" + "="*50)
            
        except Exception as e:
            print(f"Error processing {symbol}: {str(e)}")
            print("\n" + "="*50)

if __name__ == "__main__":
    test_indian_stocks()
