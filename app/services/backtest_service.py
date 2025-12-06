from typing import Dict, List, Any
from datetime import datetime, timedelta
import random


class BacktestService:
    def __init__(self):
        pass

    async def run_backtest(self, strategy: str, symbols: List[str], start_date: str, end_date: str, initial_capital: float = 100000.0) -> Dict[str, Any]:
        trade_count = max(10, min(100, len(symbols) * 12))
        total_return = round(random.uniform(-20, 80), 2)
        annualized_return = round(random.uniform(-10, 25), 2)
        max_drawdown = round(random.uniform(5, 30), 2)
        sharpe_ratio = round(random.uniform(0.2, 1.8), 2)
        trades: List[Dict[str, Any]] = []
        base_symbol = symbols[0] if symbols else "000001.SZ"
        for i in range(min(20, trade_count)):
            trades.append({
                "date": (datetime.utcnow() - timedelta(days=i * 7)).strftime("%Y-%m-%d"),
                "symbol": base_symbol,
                "action": "买入" if i % 2 == 0 else "卖出",
                "price": round(random.uniform(8, 120), 2),
                "quantity": random.randint(100, 1000),
                "pnl": round(random.uniform(-800, 1800), 2)
            })
        final_capital = round(initial_capital * (1 + total_return / 100), 2)
        return {
            "total_return": total_return,
            "annualized_return": annualized_return,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe_ratio,
            "trade_count": trade_count,
            "initial_capital": initial_capital,
            "final_capital": final_capital,
            "trade_details": trades,
            "strategy": strategy,
            "symbols": symbols,
            "period": f"{start_date} 到 {end_date}"
        }

    async def get_available_strategies(self) -> List[Dict[str, str]]:
        return [
            {"value": "ma_cross", "label": "均线交叉策略"},
            {"value": "rsi_overbought_oversold", "label": "RSI超买超卖"},
            {"value": "bollinger_bands", "label": "布林带策略"},
            {"value": "macd", "label": "MACD策略"},
            {"value": "custom", "label": "自定义策略"}
        ]

    async def validate_backtest_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        errors: List[str] = []
        if not params.get("strategy"):
            errors.append("策略不能为空")
        symbols = params.get("symbols") or []
        if not symbols:
            errors.append("至少选择一个股票")
        if not params.get("start_date") or not params.get("end_date"):
            errors.append("时间范围不能为空")
        try:
            sd = datetime.strptime(params["start_date"], "%Y-%m-%d")
            ed = datetime.strptime(params["end_date"], "%Y-%m-%d")
            if sd >= ed:
                errors.append("开始日期必须早于结束日期")
        except Exception:
            errors.append("日期格式错误，请使用 YYYY-MM-DD 格式")
        capital = float(params.get("initial_capital", 0))
        if capital <= 0:
            errors.append("初始资金必须大于0")
        return {"valid": len(errors) == 0, "errors": errors}

