"""
图形挖掘 REST 接口
POST /api/pattern/mine    全市场挖掘
GET  /api/pattern/templates 查看模板
POST /api/pattern/scan    收盘后扫描潜在上涨标的
"""

from fastapi import APIRouter, Query, HTTPException, Depends
from typing import List, Dict
from app.services.pattern_mining_service import get_pattern_mining_service, PatternMiningService

router = APIRouter()

async def get_service() -> PatternMiningService:
    return get_pattern_mining_service()


@router.post("/mine")
async def mine_patterns(
    market: str = Query("CN", description="市场代码 CN/HK/US"),
    years: int = Query(5, ge=1, le=10, description="回溯年数"),
    svc: PatternMiningService = Depends(get_service)
) -> Dict:
    """全市场图形挖掘，生成起涨点样本和模板"""
    try:
        return await svc.mine_all_market(market, years)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates")
async def get_templates(
    market: str = Query("CN"),
    svc: PatternMiningService = Depends(get_service)
) -> List[Dict]:
    """获取当前市场已生成的模板列表"""
    templates = await svc.generate_templates(market)
    return [
        {
            "id": t.id,
            "name": t.name,
            "win_rate": t.win_rate,
            "avg_return_5d": t.avg_return_5d,
            "avg_return_20d": t.avg_return_20d,
            "count": t.count
        }
        for t in templates
    ]


@router.post("/scan")
async def scan_upcoming(
    market: str = Query("CN"),
    top_k: int = Query(10, ge=1, le=50),
    svc: PatternMiningService = Depends(get_service)
) -> List[Dict]:
    """收盘后扫描最新形态，返回相似度最高的标的"""
    try:
        return await svc.scan_upcoming(market, top_k)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/upcoming")
async def list_upcoming(
    market: str = Query("CN"),
    svc: PatternMiningService = Depends(get_service)
) -> List[Dict]:
    """查看最近一次扫描的潜在上涨列表"""
    docs = await svc.upcoming_coll.find({"market": market}).sort("similarity", -1).to_list(None)
    for doc in docs:
        if "_id" in doc:
            del doc["_id"]
    return docs