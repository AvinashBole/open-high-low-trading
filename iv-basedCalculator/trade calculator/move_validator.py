"""
DISCLAIMER: 

This software is provided solely for educational and research purposes. 
It is not intended to provide investment advice, and no investment recommendations are made herein. 
The developers are not financial advisors and accept no responsibility for any financial decisions or losses resulting from the use of this software. 
Always consult a professional financial advisor before making any investment decisions.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from calculator import get_current_price  # Reuse function from calculator.py

class MoveValidator:
    def __init__(self, lookback_days=90):
        self.mag7 = ['META', 'AAPL', 'AMZN', 'GOOGL', 'MSFT', 'NVDA', 'TSLA']
        self.lookback_days = lookback_days
        self.results = []
        self.summary = {}

    def calculate_expected_move(self, ticker, date):
        """Calculate expected move for a given stock and date"""
        try:
            stock = yf.Ticker(ticker)
            
            # Get options expirations
            exp_dates = list(stock.options)
            if not exp_dates:
                return None

            # Get current price
            price_data = stock.history(period='2d', end=date)
            if price_data.empty:
                return None
            price_data.index = price_data.index.tz_localize(None)  # Remove timezone info
            current_price = price_data['Close'].iloc[-1]

            # Get nearest expiration options chain
            options = stock.option_chain(exp_dates[0])
            calls = options.calls
            puts = options.puts

            # Find ATM options
            call_diffs = (calls['strike'] - current_price).abs()
            call_idx = call_diffs.idxmin()
            put_diffs = (puts['strike'] - current_price).abs()
            put_idx = put_diffs.idxmin()

            # Calculate straddle price
            call_price = (calls.loc[call_idx, 'bid'] + calls.loc[call_idx, 'ask']) / 2
            put_price = (puts.loc[put_idx, 'bid'] + puts.loc[put_idx, 'ask']) / 2
            straddle_price = call_price + put_price

            # Calculate expected move
            expected_move_pct = (straddle_price / current_price) * 100
            expected_range = {
                'date': date,
                'price': current_price,
                'expected_move_pct': expected_move_pct,
                'lower_bound': current_price * (1 - expected_move_pct/100),
                'upper_bound': current_price * (1 + expected_move_pct/100)
            }
            return expected_range

        except Exception as e:
            print(f"Error calculating expected move for {ticker} on {date}: {str(e)}")
            return None

    def validate_moves(self):
        """Validate expected moves against actual price movements"""
        end_date = pd.Timestamp.now().tz_localize(None)
        start_date = (end_date - pd.Timedelta(days=self.lookback_days))

        for symbol in self.mag7:
            print(f"\nAnalyzing {symbol}...")
            stock = yf.Ticker(symbol)
            
            # Get daily price data
            daily_data = stock.history(start=start_date, end=end_date)
            daily_data.index = daily_data.index.tz_localize(None)  # Remove timezone info
            
            # Analyze each week
            current_date = start_date
            while current_date < end_date:
                # Skip weekends
                if current_date.weekday() >= 5:
                    current_date += timedelta(days=1)
                    continue

                expected_range = self.calculate_expected_move(symbol, current_date)
                if expected_range:
                    # Get next 5 trading days of prices
                    next_date = current_date + pd.Timedelta(days=7)
                    mask = (daily_data.index >= current_date) & (daily_data.index <= next_date)
                    future_prices = daily_data[mask]
                    if not future_prices.empty:
                        max_price = future_prices['High'].max()
                        min_price = future_prices['Low'].min()
                        
                        # Check if price stayed within expected range
                        within_range = (min_price >= expected_range['lower_bound'] and 
                                      max_price <= expected_range['upper_bound'])
                        
                        actual_move_pct = ((max(abs(max_price - expected_range['price']),
                                              abs(min_price - expected_range['price'])) /
                                          expected_range['price']) * 100)

                        result = {
                            'symbol': symbol,
                            'date': pd.Timestamp(current_date).strftime('%Y-%m-%d'),
                            'starting_price': expected_range['price'],
                            'expected_move_pct': expected_range['expected_move_pct'],
                            'actual_move_pct': actual_move_pct,
                            'within_range': within_range,
                            'min_price': min_price,
                            'max_price': max_price,
                            'lower_bound': expected_range['lower_bound'],
                            'upper_bound': expected_range['upper_bound']
                        }
                        self.results.append(result)

                current_date += pd.Timedelta(days=5)  # Move to next week

    def generate_report(self):
        """Generate analysis report and visualizations"""
        if not self.results:
            print("No results to analyze. Run validate_moves() first.")
            return

        df = pd.DataFrame(self.results)
        
        # Calculate summary statistics
        for symbol in self.mag7:
            symbol_data = df[df['symbol'] == symbol]
            if not symbol_data.empty:
                success_rate = (symbol_data['within_range'].sum() / len(symbol_data)) * 100
                avg_expected = symbol_data['expected_move_pct'].mean()
                avg_actual = symbol_data['actual_move_pct'].mean()
                
                self.summary[symbol] = {
                    'success_rate': success_rate,
                    'avg_expected_move': avg_expected,
                    'avg_actual_move': avg_actual,
                    'total_predictions': len(symbol_data)
                }

        # Save detailed results to CSV
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_file = f'move_validation_results_{timestamp}.csv'
        df.to_csv(csv_file, index=False)
        
        # Print summary report
        print("\nExpected Move Validation Summary:")
        print("=" * 80)
        for symbol, stats in self.summary.items():
            print(f"\n{symbol}:")
            print(f"Success Rate: {stats['success_rate']:.1f}%")
            print(f"Average Expected Move: {stats['avg_expected_move']:.1f}%")
            print(f"Average Actual Move: {stats['avg_actual_move']:.1f}%")
            print(f"Total Predictions: {stats['total_predictions']}")

        # Create visualization
        plt.figure(figsize=(15, 8))
        x = range(len(self.mag7))
        success_rates = [self.summary[symbol]['success_rate'] for symbol in self.mag7]
        expected_moves = [self.summary[symbol]['avg_expected_move'] for symbol in self.mag7]
        actual_moves = [self.summary[symbol]['avg_actual_move'] for symbol in self.mag7]

        plt.bar([i-0.2 for i in x], success_rates, width=0.2, label='Success Rate (%)', color='green')
        plt.bar([i for i in x], expected_moves, width=0.2, label='Avg Expected Move (%)', color='blue')
        plt.bar([i+0.2 for i in x], actual_moves, width=0.2, label='Avg Actual Move (%)', color='red')

        plt.xlabel('Stocks')
        plt.ylabel('Percentage')
        plt.title('Expected vs Actual Moves Analysis')
        plt.xticks(x, self.mag7)
        plt.legend()
        
        # Save plot
        plt.savefig(f'move_validation_plot_{timestamp}.png')
        plt.close()

        print(f"\nDetailed results saved to: {csv_file}")
        print(f"Plot saved as: move_validation_plot_{timestamp}.png")

def main():
    # Create validator instance
    validator = MoveValidator(lookback_days=90)  # Analyze last 90 days
    
    # Run validation
    print("Starting move validation analysis...")
    validator.validate_moves()
    
    # Generate and display report
    validator.generate_report()

if __name__ == "__main__":
    main()
