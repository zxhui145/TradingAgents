from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any
from app.services.backtest_service import BacktestService


router = APIRouter(prefix="/api/backtest", tags=["backtest"])


def get_service() -> BacktestService:
    return BacktestService()


@router.post("/run")
async def run_backtest(
    strategy: str = Query(...),
    symbols: List[str] = Query(...),
    start_date: str = Query(...),
    end_date: str = Query(...),
    initial_capital: float = Query(100000.0),
    svc: BacktestService = Depends(get_service)
) -> Dict[str, Any]:
    validation = await svc.validate_backtest_params({
        "strategy": strategy,
        "symbols": symbols,
        "start_date": start_date,
        "end_date": end_date,
        "initial_capital": initial_capital
    })
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail="; ".join(validation["errors"]))
    return await svc.run_backtest(strategy, symbols, start_date, end_date, initial_capital)


@router.get("/strategies")
async def get_strategies(svc: BacktestService = Depends(get_service)) -> List[Dict[str, str]]:
    return await svc.get_available_strategies()


@router.get("/health")
async def health_check() -> Dict[str, str]:
    return {"status": "healthy", "service": "backtest"}

