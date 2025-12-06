import tushare as ts
import pandas as pd
import numpy as np
import datetime
import os
import logging

# Configure logging
logger = logging.getLogger(__name__)

class TrendAnalyzer:
    def __init__(self, token=None):
        self.token = token or os.getenv('TUSHARE_TOKEN')
        if self.token:
            ts.set_token(self.token)
            self.pro = ts.pro_api()
        else:
            logger.warning("Tushare token not found. Data fetching may fail.")
            self.pro = None

    def get_stock_data(self, ts_code, start_date, end_date):
        """
        Fetch daily stock data from Tushare.
        """
        if not self.pro:
            return None
        
        try:
            df = self.pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
            if df is None or df.empty:
                return None
            
            # Sort by date ascending
            df = df.sort_values('trade_date').reset_index(drop=True)
            
            # Convert trade_date to datetime
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            
            return df
        except Exception as e:
            logger.error(f"Error fetching data for {ts_code}: {e}")
            return None

    def calculate_indicators(self, df):
        """
        Calculate technical indicators (MA, Volume MA).
        """
        if df is None or df.empty:
            return df
        
        # Moving Averages
        df['ma5'] = df['close'].rolling(window=5).mean()
        df['ma10'] = df['close'].rolling(window=10).mean()
        df['ma20'] = df['close'].rolling(window=20).mean()
        df['ma60'] = df['close'].rolling(window=60).mean()
        
        # Volume Moving Averages
        df['vol_ma5'] = df['vol'].rolling(window=5).mean()
        df['vol_ma10'] = df['vol'].rolling(window=10).mean()
        
        return df

    def analyze_trend_reversal(self, df):
        """
        Analyze for trend reversal signals.
        Returns a score and a list of signals.
        """
        if df is None or len(df) < 60:
            return 0, ["Insufficient data"]
        
        # Get the latest data point
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        score = 0
        signals = []
        
        # 1. Price above MA20 (Trend confirmation)
        if latest['close'] > latest['ma20']:
            score += 10
            signals.append("Price above MA20")
            
            # Check if it just crossed above MA20
            if prev['close'] <= prev['ma20']:
                score += 20
                signals.append("Bullish crossover MA20")

        # 2. Volume Spike (Volume > 1.5 * Vol_MA5)
        if latest['vol'] > 1.5 * latest['vol_ma5']:
            score += 15
            signals.append(f"Volume Spike ({latest['vol']/latest['vol_ma5']:.1f}x avg)")

        # 3. Golden Cross (MA5 crosses above MA10)
        if latest['ma5'] > latest['ma10'] and prev['ma5'] <= prev['ma10']:
            score += 20
            signals.append("MA5/MA10 Golden Cross")

        # 4. Price Reversal from Low (Recent low was lowest in 20 days, now rising)
        recent_low = df['low'].tail(20).min()
        if df.iloc[-5:]['low'].min() == recent_low and latest['close'] > latest['open']:
             # Check if we are bouncing off the low
             if latest['close'] > recent_low * 1.05: # 5% bounce
                 score += 15
                 signals.append("Bounce from 20-day Low")

        # 5. Consecutive Up Days with Increasing Volume
        if (df.iloc[-3:]['close'] > df.iloc[-3:]['open']).all() and \
           (df.iloc[-3:]['vol'].is_monotonic_increasing):
            score += 20
            signals.append("3 Days Up with Increasing Volume")

        return score, signals

    def scan_market(self, market='E', limit=50):
        """
        Scan the market for potential hot stocks.
        market: 'E' for Exchange (Stock), etc.
        This is a simplified scan. In a real app, we might scan a specific list or sector.
        For demo, we'll fetch a list of stocks and analyze a subset.
        """
        if not self.pro:
            return []

        try:
            # Get a list of stocks
            # listing_status='L' means listed
            data = self.pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name,industry,market')
            
            if data is None or data.empty:
                return []
            
            # Filter by market if needed (e.g., Main Board, ChiNext)
            # For now, just take a random sample or top stocks to avoid API limits/time
            # Let's take top 20 stocks by some criteria if possible, or just first 20 for demo
            # In a real scenario, we might want to filter by recent volume or gainers first.
            
            # Let's try to get daily basic data for a specific date to find top gainers first?
            # That consumes API calls. Let's just pick a few popular ones or random ones for the "Scan" demo.
            # Or better, let user input a list, or scan a small sector.
            
            # To make it useful, let's scan a small batch of random stocks to simulate a "Discovery" feature.
            sample_stocks = data.sample(n=min(limit, len(data)))
            
            results = []
            end_date = datetime.datetime.now().strftime('%Y%m%d')
            start_date = (datetime.datetime.now() - datetime.timedelta(days=100)).strftime('%Y%m%d')
            
            for index, row in sample_stocks.iterrows():
                ts_code = row['ts_code']
                name = row['name']
                
                df = self.get_stock_data(ts_code, start_date, end_date)
                if df is not None:
                    df = self.calculate_indicators(df)
                    score, signals = self.analyze_trend_reversal(df)
                    
                    if score >= 30: # Filter for decent scores
                        results.append({
                            'ts_code': ts_code,
                            'name': name,
                            'industry': row['industry'],
                            'score': score,
                            'signals': signals,
                            'latest_close': df.iloc[-1]['close'],
                            'latest_vol': df.iloc[-1]['vol']
                        })
            
            # Sort by score desc
            results.sort(key=lambda x: x['score'], reverse=True)
            return results
            
        except Exception as e:
            logger.error(f"Error scanning market: {e}")
            return []

    def get_hot_stocks(self, limit=10):
        """
        Get a list of hot stocks (simulated or via specific Tushare API if available).
        For now, we will use the scan_market method.
        """
        return self.scan_market(limit=limit)
