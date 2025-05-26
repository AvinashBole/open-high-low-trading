"""
DISCLAIMER: 

This software is provided solely for educational and research purposes. 
It is not intended to provide investment advice, and no investment recommendations are made herein. 
The developers are not financial advisors and accept no responsibility for any financial decisions or losses resulting from the use of this software. 
Always consult a professional financial advisor before making any investment decisions.
"""

from calculator import compute_recommendation
import pandas as pd
import concurrent.futures
import time
from datetime import datetime
import yfinance as yf
import requests

class IndianOptionsScanner:
    def __init__(self):
        self.results = []
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.output_file = f"indian_scan_results_{self.timestamp}.csv"

    def process_stock(self, symbol):
        """Analyze a single stock using the calculator logic"""
        try:
            # Add .NS suffix for NSE stocks if not present
            if not (symbol.endswith('.NS') or symbol.endswith('.BO')):
                symbol = f"{symbol}.NS"
                
            print(f"Processing {symbol}...")
            result = compute_recommendation(symbol)
            
            if isinstance(result, dict):
                return {
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'symbol': symbol,
                    'recommendation': ('Recommended' if all([result['avg_volume'], 
                                                          result['iv30_rv30'], 
                                                          result['ts_slope_0_45']]) 
                                    else 'Consider' if result['ts_slope_0_45'] and 
                                         (result['avg_volume'] or result['iv30_rv30'])
                                    else 'Avoid'),
                    'avg_volume_pass': result['avg_volume'],
                    'iv30_rv30_pass': result['iv30_rv30'],
                    'term_structure_pass': result['ts_slope_0_45'],
                    'expected_move': result['expected_move']
                }
            return None
        except Exception as e:
            print(f"Error processing {symbol}: {str(e)}")
            return None

    def scan_stocks(self, symbols, parallel=True, max_workers=5):
        """Scan multiple stocks with optional parallel processing"""
        self.results = []
        total = len(symbols)
        
        if parallel:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(self.process_stock, symbol): symbol for symbol in symbols}
                completed = 0
                
                for future in concurrent.futures.as_completed(futures):
                    completed += 1
                    symbol = futures[future]
                    try:
                        result = future.result()
                        if result:
                            self.results.append(result)
                            print(f"Progress: {completed}/{total} stocks processed")
                    except Exception as e:
                        print(f"Error processing {symbol}: {str(e)}")
        else:
            for i, symbol in enumerate(symbols, 1):
                result = self.process_stock(symbol)
                if result:
                    self.results.append(result)
                print(f"Progress: {i}/{total} stocks processed")

        self.save_results()
        return self.results

    def save_results(self):
        """Save scan results to CSV file"""
        if self.results:
            df = pd.DataFrame(self.results)
            df.to_csv(self.output_file, index=False)
            print(f"\nResults saved to {self.output_file}")
            
            # Print summary
            total = len(self.results)
            recommended = len([r for r in self.results if r['recommendation'] == 'Recommended'])
            consider = len([r for r in self.results if r['recommendation'] == 'Consider'])
            avoid = len([r for r in self.results if r['recommendation'] == 'Avoid'])
            
            print(f"\nScan Summary:")
            print(f"Total stocks processed: {total}")
            print(f"Recommended: {recommended}")
            print(f"Consider: {consider}")
            print(f"Avoid: {avoid}")

    def load_nifty50_symbols(self):
        """Load NIFTY 50 symbols"""
        try:
            # Using Wikipedia for NIFTY 50 constituents
            url = "https://en.wikipedia.org/wiki/NIFTY_50"
            tables = pd.read_html(url)
            for table in tables:
                if 'Symbol' in table.columns:
                    return table['Symbol'].tolist()
            return []
        except Exception as e:
            print(f"Error loading NIFTY 50 symbols: {str(e)}")
            return []

    def load_custom_symbols(self, file_path):
        """Load custom symbol list from a text file"""
        try:
            with open(file_path, 'r') as f:
                symbols = [line.strip() for line in f if line.strip()]
            return symbols
        except Exception as e:
            print(f"Error loading symbols from {file_path}: {str(e)}")
            return []

def main():
    scanner = IndianOptionsScanner()
    
    print("Indian Options Scanner Menu:")
    print("1. Scan NIFTY 50 stocks")
    print("2. Scan custom list from file")
    print("3. Scan specific symbols")
    print("4. Switch between NSE/BSE for specific symbols")
    
    choice = input("Enter your choice (1-4): ")
    
    if choice == '1':
        symbols = scanner.load_nifty50_symbols()
        if not symbols:
            print("Failed to load NIFTY 50 symbols. Please try another option.")
            return
    elif choice == '2':
        file_path = input("Enter the path to your symbols file (one symbol per line): ")
        symbols = scanner.load_custom_symbols(file_path)
        if not symbols:
            print("Failed to load symbols from file. Please check the file path and format.")
            return
    elif choice == '3':
        symbols_input = input("Enter symbols separated by commas (e.g., RELIANCE,TCS,INFY): ")
        symbols = [s.strip() for s in symbols_input.split(',') if s.strip()]
    elif choice == '4':
        symbols_input = input("Enter symbols separated by commas: ")
        exchange = input("Enter exchange (NSE/BSE): ").upper()
        suffix = '.NS' if exchange == 'NSE' else '.BO'
        symbols = [f"{s.strip()}{suffix}" for s in symbols_input.split(',') if s.strip()]
    else:
        print("Invalid choice. Please run the script again.")
        return
    
    parallel = input("Use parallel processing? (y/n, default: y): ").lower() != 'n'
    if parallel:
        max_workers = input("Enter maximum number of parallel workers (default: 5): ")
        max_workers = int(max_workers) if max_workers.isdigit() else 5
    else:
        max_workers = 1
    
    print(f"\nStarting scan of {len(symbols)} symbols...")
    scanner.scan_stocks(symbols, parallel=parallel, max_workers=max_workers)

if __name__ == "__main__":
    main()
