from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
import logging
from tradingagents.analysis.trend_analyzer import TrendAnalyzer
import pandas as pd

router = APIRouter()
logger = logging.getLogger(__name__)

class TrendSignal(BaseModel):
    ts_code: str
    name: str
    industry: str
    score: float
    signals: List[str]
    latest_close: float
    latest_vol: float

class ChartData(BaseModel):
    dates: List[str]
    open: List[float]
    close: List[float]
    high: List[float]
    low: List[float]
    vol: List[float]
    ma5: List[float]
    ma10: List[float]
    ma20: List[float]

@router.get("/scan", response_model=List[TrendSignal])
async def scan_market(
    limit: int = Query(30, ge=10, le=100),
    min_score: int = Query(30, ge=0, le=100)
):
    """
    Scan the market for potential hot stocks based on trend analysis.
    """
    try:
        analyzer = TrendAnalyzer()
        if not analyzer.token:
            raise HTTPException(status_code=500, detail="Tushare token not configured")
            
        results = analyzer.get_hot_stocks(limit=limit)
        
        # Filter by min_score
        filtered_results = [r for r in results if r['score'] >= min_score]
        
        return filtered_results
    except Exception as e:
        logger.error(f"Error scanning market: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/chart/{ts_code}", response_model=ChartData)
async def get_stock_chart(ts_code: str):
    """
    Get chart data for a specific stock.
    """
    try:
        analyzer = TrendAnalyzer()
        if not analyzer.token:
            raise HTTPException(status_code=500, detail="Tushare token not configured")
            
        import datetime
        end_date = datetime.datetime.now().strftime('%Y%m%d')
        start_date = (datetime.datetime.now() - datetime.timedelta(days=180)).strftime('%Y%m%d')
        
        df = analyzer.get_stock_data(ts_code, start_date, end_date)
        if df is None or df.empty:
            raise HTTPException(status_code=404, detail="Stock data not found")
            
        df = analyzer.calculate_indicators(df)
        
        # Handle NaN values for JSON serialization
        df = df.fillna(0)
        
        return ChartData(
            dates=df['trade_date'].dt.strftime('%Y-%m-%d').tolist(),
            open=df['open'].tolist(),
            close=df['close'].tolist(),
            high=df['high'].tolist(),
            low=df['low'].tolist(),
            vol=df['vol'].tolist(),
            ma5=df['ma5'].tolist(),
            ma10=df['ma10'].tolist(),
            ma20=df['ma20'].tolist()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chart data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
