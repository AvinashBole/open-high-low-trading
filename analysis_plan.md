# Open High Low Pattern Analysis Plan

## Objective
Analyze the performance of pre-identified Open High Low patterns to validate if entering at the day's high with a 0.2% target is profitable.

## Input Data
- CSV file containing:
  - Stock symbols where Open High Low pattern was observed
  - Date of pattern occurrence

## Analysis Steps

1. **For Each Stock/Date Entry**
   - Fetch daily price data
   - Entry point: Day's high
   - Target: 0.2% above entry
   - Stop loss: Previous day's low

2. **Track Outcomes**
   - Success: Price reached 0.2% target
   - Failure: Price hit stop loss
   - Incomplete: Neither target nor stop loss hit

3. **Generate Statistics**
   - Success rate
   - Average profit/loss
   - Risk-reward metrics

## Implementation

1. **Data Processing**
   - Read CSV file
   - Fetch required price data using yfinance
   - Calculate entry, target, and stop loss points

2. **Results Output**
   - Summary statistics
   - Trade-by-trade details
   - Debug logs for verification

## Success Metrics
- Percentage of trades hitting target
- Average loss on failed trades
- Overall win/loss ratio
