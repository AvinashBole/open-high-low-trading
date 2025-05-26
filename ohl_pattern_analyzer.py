import pandas as pd
import sys
import os
import numpy as np
from datetime import datetime, timedelta
import pytz
import time
sys.path.append(os.path.join(os.path.dirname(__file__), '../iv-basedCalculator/trade calculator'))
from fetch_intraday import fetch_intraday

class OHLPatternAnalyzer:
    def __init__(self):
        self.results = []
        self.debug_logs = []
        self.data_cache = {}  # Cache for storing fetched data
        self.errors = []  # Track any errors

    def log_debug(self, message):
        """Add debug message to logs"""
        print(message)  # Print immediately for real-time feedback
        self.debug_logs.append(message)

    def is_weekday(self, date):
        """Check if date is a weekday"""
        return date.weekday() < 5

    def next_weekday(self, date):
        """Get next weekday from given date"""
        next_day = date + timedelta(days=1)
        while not self.is_weekday(next_day):
            next_day += timedelta(days=1)
        return next_day

    def load_stock_data(self, csv_path):
        """
        Load the stock symbols and dates from CSV file
        Args:
            csv_path: Path to CSV file
        """
        self.log_debug(f"Loading data from {csv_path}")
        df = pd.read_csv(csv_path)

        # Convert date string to datetime
        self.log_debug("Converting dates and adjusting for weekdays...")
        df['original_date'] = pd.to_datetime(df['date'], format='%d-%m-%Y %I:%M %p')

        # Ensure weekdays only
        adjusted_dates = []
        for date in df['original_date']:
            adj_date = date
            if not self.is_weekday(adj_date):
                adj_date = self.next_weekday(adj_date)
            adjusted_dates.append(adj_date)

        df['date'] = [d.strftime('%Y-%m-%d') for d in adjusted_dates]

        # Log the date mappings
        for _, row in df.iterrows():
            if row['original_date'] != pd.Timestamp(row['date']):
                self.log_debug(f"Adjusted {row['original_date'].strftime('%Y-%m-%d')} to {row['date']} (weekend adjustment)")

        self.log_debug(f"Loaded {len(df)} records")
        return df

    def get_stock_data(self, symbol, date_str, interval='1d'):
        """Get stock data with caching and rate limit handling"""
        cache_key = f"{symbol}_{date_str}_{interval}"
        if cache_key in self.data_cache:
            return self.data_cache[cache_key]

        # Add small delay between API calls
        time.sleep(0.1)  # 100ms delay

        try:
            data = fetch_intraday(symbol, date_str, interval)
            if data is not None:
                self.data_cache[cache_key] = data
            return data
        except Exception as e:
            error_msg = f"Error fetching data for {symbol} on {date_str}: {str(e)}"
            self.errors.append(error_msg)
            self.log_debug(error_msg)
            return None

    def analyze_future_performance(self, symbol, pattern_date, entry_price, stop_loss_price, pattern_data, days_to_check=10):
        """
        Check if target is hit in the next few days
        Returns: Dictionary with performance analysis
        """
        try:
            # Convert pattern_date to datetime without timezone at first
            pattern_dt = datetime.strptime(pattern_date, '%Y-%m-%d')

            # Create date-only version for day calculations
            pattern_date_only = pattern_dt.date()

            # For comparison with Yahoo timestamps, create timezone-aware version
            pattern_dt_tz = pd.Timestamp(pattern_dt).tz_localize('UTC')
            end_dt = pattern_dt + timedelta(days=days_to_check)

            target_price = entry_price * 1.002  # 0.2% target
            stop_loss_gap = ((entry_price - stop_loss_price) / entry_price) * 100
            pattern_day_range = ((pattern_data['High'].max() - pattern_data['Low'].min()) / pattern_data['Open'].iloc[0]) * 100
            pattern_day_move = ((pattern_data['Close'].iloc[-1] - pattern_data['Open'].iloc[0]) / pattern_data['Open'].iloc[0]) * 100

            self.log_debug(f"\nAnalyzing {symbol} on {pattern_date}")
            self.log_debug(f"Entry: {entry_price:.2f}, Target: {target_price:.2f} (+0.2%), Stop Loss: {stop_loss_price:.2f} (-{stop_loss_gap:.1f}%)")
            self.log_debug(f"Pattern Day Stats:")
            self.log_debug(f"- OHLC: Open={pattern_data['Open'].iloc[0]:.2f}, High={pattern_data['High'].max():.2f}, Low={pattern_data['Low'].min():.2f}, Close={pattern_data['Close'].iloc[-1]:.2f}")
            self.log_debug(f"- Range: {pattern_day_range:.1f}%, Open to Close: {pattern_day_move:+.1f}%")
            
            # DEBUG: Add extra information about what we're looking for
            self.log_debug(f"DEBUG: Looking for target price >= {target_price:.2f}")
            self.log_debug(f"DEBUG: Looking for low price > {stop_loss_price:.2f}")

            # Get future data
            future_data = self.get_stock_data(symbol, pattern_date, interval='1d')
            if future_data is None or future_data.empty:
                self.log_debug(f"No data available for {symbol}")
                return None

            # Filter data after pattern date - using simple date string comparison approach
            # Convert back to basic timestamp for filtering
            pattern_date_str = pattern_date
            self.log_debug(f"DEBUG: Pattern date string for filtering: {pattern_date_str}")
            
            # Show all dates before filtering
            self.log_debug(f"DEBUG: All dates in data before filtering:")
            self.log_debug(future_data.index.strftime('%Y-%m-%d').tolist())
            
            future_data = future_data[future_data.index.strftime('%Y-%m-%d') > pattern_date_str]
            
            # Show all dates after filtering
            self.log_debug(f"DEBUG: Filtered future dates (should be after {pattern_date_str}):")
            self.log_debug(future_data.index.strftime('%Y-%m-%d').tolist())
            
            if future_data.empty:
                self.log_debug(f"No future data after pattern date for {symbol}")
                return None

            # Track daily performance and check for target/stop loss
            daily_returns = []
            for idx, row in future_data.iterrows():
                day_return = ((row['Close'] - entry_price) / entry_price) * 100
                day_date = idx.date()
                days_diff = (day_date - pattern_date_only).days
                
                self.log_debug(f"\nDEBUG: Checking day {days_diff}: {day_date}")
                self.log_debug(f"DEBUG: OHLC values - Open={row['Open']:.2f}, High={row['High']:.2f}, Low={row['Low']:.2f}, Close={row['Close']:.2f}")
                self.log_debug(f"DEBUG: Target check: High >= {target_price:.2f}? {row['High'] >= target_price}")
                self.log_debug(f"DEBUG: Stop loss check: Low > {stop_loss_price:.2f}? {row['Low'] > stop_loss_price}")
                
                daily_returns.append({
                    'day': days_diff,
                    'open': row['Open'],
                    'high': row['High'],
                    'low': row['Low'],
                    'close': row['Close'],
                    'return': day_return
                })

                # If high >= target price and low > stop loss price
                if row['High'] >= target_price and row['Low'] > stop_loss_price:
                    days_to_target = days_diff
                    self.log_debug(f"TARGET HIT on day {days_to_target}!")
                    self.log_debug(f"Day OHLC: Open={row['Open']:.2f}, High={row['High']:.2f}, Low={row['Low']:.2f}, Close={row['Close']:.2f}")
                    self.log_debug(f"Target condition satisfied: {row['High']} >= {target_price} and {row['Low']} > {stop_loss_price}")
                    return {
                        'date': pattern_date,
                        'symbol': symbol,
                        'entry_price': entry_price,
                        'target_price': target_price,
                        'stop_loss_price': stop_loss_price,
                        'stop_loss_gap': stop_loss_gap,
                        'target_hit': True,
                        'stop_loss_hit': False,
                        'days_to_target': days_to_target,
                        'profit_percent': 0.2,
                        'daily_performance': daily_returns,
                        'exit_price': target_price,
                        'exit_reason': 'target_hit',
                        'day_open': row['Open'],
                        'day_high': row['High'],
                        'day_low': row['Low'],
                        'day_close': row['Close'],
                        'pattern_day_open': pattern_data['Open'].iloc[0],
                        'pattern_day_high': pattern_data['High'].max(),
                        'pattern_day_low': pattern_data['Low'].min(),
                        'pattern_day_close': pattern_data['Close'].iloc[-1],
                        'pattern_day_range': pattern_day_range,
                        'pattern_day_move': pattern_day_move
                    }

                # If low <= stop loss price
                if row['Low'] <= stop_loss_price:
                    days_to_stop = days_diff
                    stop_loss_percent = ((stop_loss_price - entry_price) / entry_price) * 100
                    self.log_debug(f"STOP LOSS hit on day {days_to_stop}!")
                    self.log_debug(f"Day OHLC: Open={row['Open']:.2f}, High={row['High']:.2f}, Low={row['Low']:.2f}, Close={row['Close']:.2f}")
                    self.log_debug(f"Stop loss condition triggered: {row['Low']} <= {stop_loss_price}")
                    return {
                        'date': pattern_date,
                        'symbol': symbol,
                        'entry_price': entry_price,
                        'target_price': target_price,
                        'stop_loss_price': stop_loss_price,
                        'stop_loss_gap': stop_loss_gap,
                        'target_hit': False,
                        'stop_loss_hit': True,
                        'days_to_stop': days_to_stop,
                        'loss_percent': stop_loss_percent,
                        'daily_performance': daily_returns,
                        'exit_price': stop_loss_price,
                        'exit_reason': 'stop_loss',
                        'day_open': row['Open'],
                        'day_high': row['High'],
                        'day_low': row['Low'],
                        'day_close': row['Close'],
                        'pattern_day_open': pattern_data['Open'].iloc[0],
                        'pattern_day_high': pattern_data['High'].max(),
                        'pattern_day_low': pattern_data['Low'].min(),
                        'pattern_day_close': pattern_data['Close'].iloc[-1],
                        'pattern_day_range': pattern_day_range,
                        'pattern_day_move': pattern_day_move
                    }

            # If neither target nor stop loss was hit
            last_close = future_data.iloc[-1]['Close']
            final_percent = ((last_close - entry_price) / entry_price) * 100
            self.log_debug(f"\nDEBUG: End of analysis - Neither target nor stop loss hit!")
            self.log_debug(f"DEBUG: Final return after {days_to_check} days: {final_percent:.2f}%")

            # Find best and worst points
            highs = future_data['High'].values
            lows = future_data['Low'].values
            max_high = max(highs)
            min_low = min(lows)
            best_possible = ((max_high - entry_price) / entry_price) * 100
            worst_possible = ((min_low - entry_price) / entry_price) * 100
            self.log_debug(f"DEBUG: Best high during period: {max_high:.2f}")
            self.log_debug(f"DEBUG: Worst low during period: {min_low:.2f}")
            self.log_debug(f"DEBUG: Best possible return: {best_possible:.2f}%, Worst possible: {worst_possible:.2f}%")

            return {
                'date': pattern_date,
                'symbol': symbol,
                'entry_price': entry_price,
                'target_price': target_price,
                'stop_loss_price': stop_loss_price,
                'stop_loss_gap': stop_loss_gap,
                'target_hit': False,
                'stop_loss_hit': False,
                'final_price': last_close,
                'final_percent': final_percent,
                'days_checked': days_to_check,
                'best_possible_return': best_possible,
                'worst_possible_return': worst_possible,
                'daily_performance': daily_returns,
                'exit_price': last_close,
                'exit_reason': 'time_exit',
                'pattern_day_open': pattern_data['Open'].iloc[0],
                'pattern_day_high': pattern_data['High'].max(),
                'pattern_day_low': pattern_data['Low'].min(),
                'pattern_day_close': pattern_data['Close'].iloc[-1],
                'pattern_day_range': pattern_day_range,
                'pattern_day_move': pattern_day_move
            }

        except Exception as e:
            error_msg = f"Error analyzing future performance for {symbol}: {str(e)}"
            self.errors.append(error_msg)
            self.log_debug(error_msg)
            return None

    def analyze_stocks(self, csv_path):
        """
        Analyze stocks from the CSV file
        Args:
            csv_path: Path to CSV file
        """
        df = self.load_stock_data(csv_path)
        total_stocks = len(df)

        print(f"\nAnalyzing {total_stocks} stock/date combinations...")
        for idx, row in df.iterrows():
            progress = (idx + 1) / total_stocks * 100
            print(f"\rProgress: {idx+1}/{total_stocks} ({progress:.1f}%)", end='')

            # Get pattern day's data to get entry price
            pattern_data = self.get_stock_data(row['symbol'], row['date'], interval='1d')
            self.log_debug(f"\nDEBUG: Raw pattern day data shape: {pattern_data.shape if pattern_data is not None else 'None'}")
            self.log_debug(f"DEBUG: Pattern day ({row['date']}) data date range: {pattern_data.index.min().strftime('%Y-%m-%d') if pattern_data is not None and not pattern_data.empty else 'N/A'} to {pattern_data.index.max().strftime('%Y-%m-%d') if pattern_data is not None and not pattern_data.empty else 'N/A'}")
            
            if pattern_data is not None and not pattern_data.empty:
                # Filter for just the pattern day
                pattern_day_only = pattern_data[pattern_data.index.strftime('%Y-%m-%d') == row['date']]
                self.log_debug(f"DEBUG: Filtered pattern day data shape: {pattern_day_only.shape}")
                self.log_debug(f"DEBUG: Pattern day only data range: {pattern_day_only.index.min().strftime('%Y-%m-%d') if not pattern_day_only.empty else 'N/A'} to {pattern_day_only.index.max().strftime('%Y-%m-%d') if not pattern_day_only.empty else 'N/A'}")
                
                # Get previous day's data for stop loss
                pattern_dt = pd.to_datetime(row['date'])
                prev_day = pattern_dt - timedelta(days=1)
                prev_day_str = prev_day.strftime('%Y-%m-%d')
                self.log_debug(f"DEBUG: Previous day date: {prev_day_str}")
                
                prev_data = self.get_stock_data(row['symbol'], prev_day_str, interval='1d')
                self.log_debug(f"DEBUG: Raw previous day data shape: {prev_data.shape if prev_data is not None else 'None'}")
                self.log_debug(f"DEBUG: Previous day data date range: {prev_data.index.min().strftime('%Y-%m-%d') if prev_data is not None and not prev_data.empty else 'N/A'} to {prev_data.index.max().strftime('%Y-%m-%d') if prev_data is not None and not prev_data.empty else 'N/A'}")
                
                if prev_data is not None and not prev_data.empty:
                    # Filter for just the previous day
                    prev_day_only = prev_data[prev_data.index.strftime('%Y-%m-%d') == prev_day_str]
                    self.log_debug(f"DEBUG: Filtered previous day data shape: {prev_day_only.shape}")
                    self.log_debug(f"DEBUG: Previous day only data range: {prev_day_only.index.min().strftime('%Y-%m-%d') if not prev_day_only.empty else 'N/A'} to {prev_day_only.index.max().strftime('%Y-%m-%d') if not prev_day_only.empty else 'N/A'}")
                    
                    # Log the high/low values before selecting
                    self.log_debug(f"DEBUG: All pattern day highs: {pattern_data['High'].sort_values().tolist()}")
                    self.log_debug(f"DEBUG: All previous day lows: {prev_data['Low'].sort_values().tolist()}")
                    self.log_debug(f"DEBUG: Filtered pattern day highs: {pattern_day_only['High'].sort_values().tolist() if not pattern_day_only.empty else 'N/A'}")
                    self.log_debug(f"DEBUG: Filtered previous day lows: {prev_day_only['Low'].sort_values().tolist() if not prev_day_only.empty else 'N/A'}")
                    
                    # Calculate both ways to see difference
                    entry_price_all = pattern_data['High'].max()
                    entry_price_filtered = pattern_day_only['High'].max() if not pattern_day_only.empty else entry_price_all
                    stop_loss_all = prev_data['Low'].min()
                    stop_loss_filtered = prev_day_only['Low'].min() if not prev_day_only.empty else stop_loss_all
                    
                    self.log_debug(f"DEBUG: Entry price (all data): {entry_price_all}")
                    self.log_debug(f"DEBUG: Entry price (filtered): {entry_price_filtered}")
                    self.log_debug(f"DEBUG: Stop loss (all data): {stop_loss_all}")
                    self.log_debug(f"DEBUG: Stop loss (filtered): {stop_loss_filtered}")
                    
                    # Use the filtered values for specific dates instead of all data
                    entry_price = entry_price_filtered
                    stop_loss_price = stop_loss_filtered
                    self.log_debug(f"DEBUG: USING - Entry: {entry_price}, Target: {entry_price * 1.002}, Stop loss: {stop_loss_price}")
                    result = self.analyze_future_performance(row['symbol'], row['date'], entry_price, stop_loss_price, pattern_data)
                    if result:
                        self.results.append(result)

            # Save intermediate results every 50 stocks
            if (idx + 1) % 50 == 0:
                self.save_results(f"trade_analysis_results_{idx+1}.csv")

        print("\nAnalysis complete!")

    def save_results(self, filename):
        """Save results to CSV file"""
        if self.results:
            output_path = os.path.join(os.path.dirname(__file__), filename)
            pd.DataFrame(self.results).to_csv(output_path, index=False)
            self.log_debug(f"Results saved to: {output_path}")

    def generate_summary(self):
        """Generate summary statistics of the analysis"""
        if not self.results:
            return "No results to analyze"

        df = pd.DataFrame(self.results)
        total_trades = len(df)
        successful_trades = len(df[df['target_hit'] == True])
        stopped_trades = len(df[df['stop_loss_hit'] == True])
        time_exit_trades = total_trades - successful_trades - stopped_trades

        success_rate = (successful_trades / total_trades) * 100
        stop_rate = (stopped_trades / total_trades) * 100
        time_exit_rate = (time_exit_trades / total_trades) * 100

        summary = f"""
Trade Analysis Summary
-------------------------------
Total Trades Analyzed: {total_trades}

Trade Outcomes:
- Successful Trades (0.2% target hit): {successful_trades} ({success_rate:.2f}%)
- Stopped Out Trades: {stopped_trades} ({stop_rate:.2f}%)
- Time Exit Trades: {time_exit_trades} ({time_exit_rate:.2f}%)

Performance Metrics:
"""
        if successful_trades > 0:
            successful = df[df['target_hit'] == True]
            avg_days = successful['days_to_target'].mean()
            summary += f"- Average Days to Target: {avg_days:.1f} days\n"

        if stopped_trades > 0:
            stopped = df[df['stop_loss_hit'] == True]
            avg_days_stop = stopped['days_to_stop'].mean()
            avg_loss = stopped['loss_percent'].mean()
            avg_stop_gap = stopped['stop_loss_gap'].mean()
            summary += f"- Average Days to Stop Loss: {avg_days_stop:.1f} days\n"
            summary += f"- Average Loss on Stopped Trades: {avg_loss:.2f}%\n"
            summary += f"- Average Stop Loss Gap: {avg_stop_gap:.2f}%\n"

        if time_exit_trades > 0:
            time_exits = df[~df['target_hit'] & ~df['stop_loss_hit']]
            avg_return = time_exits['final_percent'].mean()
            best_possible = time_exits['best_possible_return'].mean()
            worst_possible = time_exits['worst_possible_return'].mean()
            summary += f"- Average Return on Time Exits: {avg_return:.2f}%\n"
            summary += f"- Average Best Possible Return: {best_possible:.2f}%\n"
            summary += f"- Average Worst Possible Return: {worst_possible:.2f}%\n"

        # Pattern day stats
        pattern_day_moves = df['pattern_day_move']
        pattern_day_ranges = df['pattern_day_range']
        summary += f"\nPattern Day Statistics:"
        summary += f"\n- Average Open to Close: {pattern_day_moves.mean():.2f}%"
        summary += f"\n- Max Open to Close: {pattern_day_moves.max():.2f}%"
        summary += f"\n- Min Open to Close: {pattern_day_moves.min():.2f}%"
        summary += f"\n- Average Day Range: {pattern_day_ranges.mean():.2f}%"
        summary += f"\n- Max Day Range: {pattern_day_ranges.max():.2f}%"
        summary += f"\n- Min Day Range: {pattern_day_ranges.min():.2f}%"

        # Add date range info
        dates = pd.to_datetime(df['date'])
        summary += f"\n\nDate Range Analyzed: {dates.min().strftime('%Y-%m-%d')} to {dates.max().strftime('%Y-%m-%d')}"

        # Add error summary if any
        if self.errors:
            summary += f"\n\nErrors Encountered: {len(self.errors)}"
            summary += f"\nFirst 5 errors:"
            for error in self.errors[:5]:
                summary += f"\n- {error}"

        return summary

def main():
    analyzer = OHLPatternAnalyzer()
    # Use the new input file
    csv_path = os.path.expanduser("~/Downloads/Backtest OHOL+PRB, Technical Analysis Scanner.csv")

    print(f"Starting analysis using: {csv_path}")
    analyzer.analyze_stocks(csv_path)

    print("\nGenerating summary...")
    summary = analyzer.generate_summary()
    print(summary)

    # Save final results
    if analyzer.results:
        output_path = os.path.join(os.path.dirname(__file__), 'trade_analysis_results_final.csv')
        pd.DataFrame(analyzer.results).to_csv(output_path, index=False)
        print(f"\nFinal results saved to: {output_path}")

        # Save debug logs
        log_path = os.path.join(os.path.dirname(__file__), 'analysis_debug.log')
        with open(log_path, 'w') as f:
            # Fix the issue with list items in debug_logs
            cleaned_logs = []
            for log in analyzer.debug_logs:
                if isinstance(log, list):
                    cleaned_logs.append(str(log))
                else:
                    cleaned_logs.append(log)
            f.write('\n'.join(cleaned_logs))
        print(f"Debug logs saved to: {log_path}")

if __name__ == "__main__":
    main()
