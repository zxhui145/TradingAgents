"""
历史图形挖掘与上涨预警服务
1. 扫描全市场历史K线，自动标注“起涨点”
2. 提取起涨点前20根K线特征向量（33维）
3. 使用KMeans聚类归纳出6种高胜率上涨形态模板
4. 每日收盘后与模板比对，相似度>0.92则写入upcoming_upswing集合并推送到前端
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import numpy as np
import pandas as pd
from dataclasses import dataclass
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity

from app.core.database import get_database
from tradingagents.utils.logging_manager import get_logger
logger = get_logger("pattern_mining")
from tradingagents.tools.analysis.indicators import add_all_indicators
from tradingagents.tools.pattern import (
    extract_feature_vector,
    cosine_similarity_1d,
    upswing_label
)


@dataclass
class UpswingCase:
    """单个起涨点样本"""
    symbol: str
    market: str
    date: datetime
    features: np.ndarray          # 33维特征向量
    return_5d: float              # 后5日收益
    return_20d: float             # 后20日收益
    win: bool                     # 20日收益>5%视为成功


@dataclass
class PatternTemplate:
    """聚类后的形态模板"""
    id: str
    name: str
    centroid: np.ndarray          # 中心向量
    win_rate: float               # 模板胜率
    avg_return_5d: float
    avg_return_20d: float
    count: int                    # 样本数


class PatternMiningService:
    """历史图形挖掘服务"""

    def __init__(self):
        self.db = get_database()
        self.templates_coll = self.db.pattern_templates
        self.cases_coll = self.db.upswing_cases
        self.upcoming_coll = self.db.upcoming_upswing
        self.scaler = StandardScaler()
        self.kmeans: Optional[KMeans] = None

    # -------------------- 对外接口 --------------------

    async def mine_all_market(self, market: str = "CN", years: int = 5) -> Dict:
        """全市场挖掘指定年份的起涨点"""
        logger.info(f"[图形挖掘] 开始 {market} 市场 {years} 年数据挖掘...")
        begin = datetime.now() - timedelta(days=years * 365)
        symbols = await self._get_all_symbols(market)
        total_cases = 0
        for sym in symbols:
            cases = await self._scan_symbol(sym, market, begin)
            if cases:
                await self._save_cases(cases)
                total_cases += len(cases)
        logger.info(f"[图形挖掘] 共发现 {total_cases} 个起涨点")
        # 聚类生成模板
        templates = await self._generate_templates(market)
        return {
            "market": market, 
            "total_cases": total_cases, 
            "templates": [self._template_to_doc(t) for t in templates]
        }

    async def generate_templates(self, market: str = "CN") -> List[PatternTemplate]:
        """根据已存 cases 重新聚类生成模板"""
        return await self._generate_templates(market)

    async def scan_upcoming(self, market: str = "CN", top_k: int = 10) -> List[Dict]:
        """收盘后扫描最新形态，返回相似度最高的 top_k 只股票"""
        templates = await self._load_templates(market)
        if not templates:
            logger.warning("[图形预警] 无模板，请先执行 mine")
            return []
        last_trade_date = await self._get_last_trade_date(market)
        symbols = await self._get_all_symbols(market)
        upcoming = []
        for sym in symbols:
            item = await self._match_single(sym, market, last_trade_date, templates)
            if item:
                upcoming.append(item)
        # 按相似度排序
        upcoming.sort(key=lambda x: x["similarity"], reverse=True)
        upcoming = upcoming[:top_k]
        # 持久化
        if upcoming:
            await self.upcoming_coll.delete_many({"market": market, "date": last_trade_date})
            await self.upcoming_coll.insert_many(upcoming)
        logger.info(f"[图形预警] {market} 发现 {len(upcoming)} 只潜在上涨标的")
        return upcoming

    # -------------------- 内部实现 --------------------

    async def _get_all_symbols(self, market: str) -> List[str]:
        """获取市场全部股票代码"""
        cursor = self.db.stock_basic.find({"market": market}, {"symbol": 1})
        return [doc["symbol"] async for doc in cursor]

    async def _scan_symbol(self, symbol: str, market: str, begin: datetime) -> List[UpswingCase]:
        """扫描单只股票历史，返回起涨点列表"""
        # 拉取日线（复权）
        df = await self._fetch_kline(symbol, market, begin)
        if df is None or len(df) < 60:
            return []
        # 计算指标
        df = add_all_indicators(df, close_col="close")
        # 标注起涨点
        df["upswing"] = upswing_label(df)
        # 提取样本
        cases = []
        for idx in df[df.upswing].index:
            if idx < 20 or idx + 20 >= len(df):
                continue
            features = extract_feature_vector(df, idx - 19, idx)   # 前20根
            if features is None:
                continue
            return_5d = (df.iloc[idx + 5].close / df.iloc[idx].close - 1) * 100
            return_20d = (df.iloc[idx + 20].close / df.iloc[idx].close - 1) * 100
            cases.append(UpswingCase(
                symbol=symbol,
                market=market,
                date=df.iloc[idx].trade_date,
                features=features,
                return_5d=return_5d,
                return_20d=return_20d,
                win=return_20d > 5
            ))
        return cases

    async def _fetch_kline(self, symbol: str, market: str, begin: datetime) -> Optional[pd.DataFrame]:
        """从 MongoDB 拉取日线"""
        cursor = self.db.stock_historical_daily.find({
            "symbol": symbol,
            "market": market,
            "trade_date": {"$gte": begin}
        }).sort("trade_date", 1)
        records = [doc async for doc in cursor]
        if not records:
            return None
        df = pd.DataFrame(records)
        df["trade_date"] = pd.to_datetime(df["trade_date"])
        return df

    async def _save_cases(self, cases: List[UpswingCase]):
        """批量写入起涨点样本"""
        docs = []
        for c in cases:
            docs.append({
                "symbol": c.symbol,
                "market": c.market,
                "date": c.date,
                "features": c.features.tolist(),
                "return_5d": c.return_5d,
                "return_20d": c.return_20d,
                "win": c.win,
                "created_at": datetime.utcnow()
            })
        if docs:
            await self.cases_coll.insert_many(docs)

    async def _generate_templates(self, market: str) -> List[PatternTemplate]:
        """聚类生成模板"""
        cases = await self._load_cases(market)
        if len(cases) < 50:
            logger.warning(f"[图形挖掘] 样本不足({len(cases)})，跳过聚类")
            return []
        # 特征矩阵
        X = np.vstack([c.features for c in cases])
        X = self.scaler.fit_transform(X)
        # KMeans 聚类
        k = min(6, len(cases) // 20)
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X)
        self.kmeans = kmeans
        # 统计每类胜率
        templates = []
        for i in range(k):
            cluster_cases = [c for c, l in zip(cases, labels) if l == i]
            win_rate = np.mean([c.win for c in cluster_cases])
            avg_ret_5 = np.mean([c.return_5d for c in cluster_cases])
            avg_ret_20 = np.mean([c.return_20d for c in cluster_cases])
            centroid = kmeans.cluster_centers_[i]
            templates.append(PatternTemplate(
                id=f"{market}T{i}",
                name=self._guess_name(cluster_cases),
                centroid=centroid,
                win_rate=win_rate,
                avg_return_5d=avg_ret_5,
                avg_return_20d=avg_ret_20,
                count=len(cluster_cases)
            ))
        # 持久化
        await self.templates_coll.delete_many({"market": market})
        await self.templates_coll.insert_many([self._template_to_doc(t) for t in templates])
        logger.info(f"[图形挖掘] 生成 {len(templates)} 个模板，平均胜率 {np.mean([t.win_rate for t in templates]):.2%}")
        return templates

    async def _load_cases(self, market: str) -> List[UpswingCase]:
        """从 MongoDB 读取样本"""
        cursor = self.cases_coll.find({"market": market})
        cases = []
        async for doc in cursor:
            cases.append(UpswingCase(
                symbol=doc["symbol"],
                market=doc["market"],
                date=doc["date"],
                features=np.array(doc["features"]),
                return_5d=doc["return_5d"],
                return_20d=doc["return_20d"],
                win=doc["win"]
            ))
        return cases

    async def _load_templates(self, market: str) -> List[PatternTemplate]:
        """读取模板"""
        cursor = self.templates_coll.find({"market": market})
        templates = []
        async for doc in cursor:
            templates.append(PatternTemplate(
                id=doc["id"],
                name=doc["name"],
                centroid=np.array(doc["centroid"]),
                win_rate=doc["win_rate"],
                avg_return_5d=doc["avg_return_5d"],
                avg_return_20d=doc["avg_return_20d"],
                count=doc["count"]
            ))
        return templates

    async def _match_single(self, symbol: str, market: str, trade_date: datetime, templates: List[PatternTemplate]) -> Optional[Dict]:
        """单只股票与模板比对"""
        # 取最近 20 根 K 线
        begin = trade_date - timedelta(days=30)
        df = await self._fetch_kline(symbol, market, begin)
        if df is None or len(df) < 20:
            return None
        df = add_all_indicators(df, close_col="close")
        features = extract_feature_vector(df, -20, -1)   # 最近20根
        if features is None:
            return None
        features = self.scaler.transform(features.reshape(1, -1))[0]
        # 与所有模板比对
        best_tpl, best_sim = None, 0
        for tpl in templates:
            sim = cosine_similarity_1d(features, tpl.centroid)
            if sim > best_sim:
                best_sim, best_tpl = sim, tpl
        if best_sim < 0.92:
            return None
        return {
            "symbol": symbol,
            "market": market,
            "date": trade_date,
            "template_id": best_tpl.id,
            "template_name": best_tpl.name,
            "similarity": round(best_sim, 4),
            "win_rate": best_tpl.win_rate,
            "forecast_return_5d": best_tpl.avg_return_5d,
            "forecast_return_20d": best_tpl.avg_return_20d,
            "reason": self._build_reason(best_tpl, features)
        }

    def _guess_name(self, cases: List[UpswingCase]) -> str:
        """根据样本特征给模板起名字（简单规则）"""
        # 这里可以接入更复杂的 NLP 或人工命名
        return f"模板{len(cases)}例"

    def _build_reason(self, tpl: PatternTemplate, features: np.ndarray) -> str:
        """生成人类可读的理由"""
        # 简单映射，可扩展
        return f"与模板'{tpl.name}'相似度{cosine_similarity_1d(features, tpl.centroid):.1%}，历史胜率{tpl.win_rate:.1%}"

    def _template_to_doc(self, tpl: PatternTemplate) -> Dict:
        return {
            "id": tpl.id,
            "market": tpl.id[:2],   # CN/HK/US
            "name": tpl.name,
            "centroid": tpl.centroid.tolist(),
            "win_rate": tpl.win_rate,
            "avg_return_5d": tpl.avg_return_5d,
            "avg_return_20d": tpl.avg_return_20d,
            "count": tpl.count,
            "created_at": datetime.utcnow()
        }

    async def _get_last_trade_date(self, market: str) -> datetime:
        """获取最近有数据的交易日"""
        doc = await self.db.stock_historical_daily.find_one(
            {"market": market},
            sort=[("trade_date", -1)]
        )
        return doc["trade_date"] if doc else datetime.utcnow() - timedelta(days=1)


# -------------------- 单例 --------------------
_pattern_mining_service: Optional[PatternMiningService] = None


def get_pattern_mining_service() -> PatternMiningService:
    global _pattern_mining_service
    if _pattern_mining_service is None:
        _pattern_mining_service = PatternMiningService()
    return _pattern_mining_service