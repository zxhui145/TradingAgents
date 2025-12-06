"""
图形识别工具包
1. 起涨点标注
2. 特征向量提取（33维）
3. 相似度计算
"""

import numpy as np
import pandas as pd
from typing import Optional


def upswing_label(df: pd.DataFrame) -> pd.Series:
    """
    标注起涨点：
    1. 收盘价 > MA20*1.02（突破均线）
    2. 成交量 > MA20*1.5（放量）
    3. MACD柱 > 0（翻红）
    """
    ma20 = df["close"].rolling(20).mean()
    vol20 = df["volume"].rolling(20).mean()
    macd = df.get("macd", 0)
    cond1 = df["close"] > ma20 * 1.02
    cond2 = df["volume"] > vol20 * 1.5
    cond3 = macd > 0
    return cond1 & cond2 & cond3


def extract_feature_vector(df: pd.DataFrame, start_idx: int, end_idx: int) -> Optional[np.ndarray]:
    """
    提取 [start_idx, end_idx] 区间内的 33 维特征向量
    特征包括：价格斜率、波动率、成交量萎缩率、MACD/RSI/布林带位置等
    """
    try:
        sub = df.iloc[start_idx:end_idx+1].copy()
        if len(sub) < 20:
            return None
        # 价格序列（归一化到首根K线）
        price = sub["close"].values
        price0 = price[0]
        price_norm = price / price0 - 1
        # 成交量序列（归一化）
        vol = sub["volume"].values
        vol0 = vol[0] if vol[0] != 0 else 1
        vol_norm = vol / vol0

        feats = []

        # 1. 价格斜率（线性回归系数）
        x = np.arange(len(price_norm))
        slope = np.polyfit(x, price_norm, 1)[0]
        feats.append(slope)

        # 2. 价格均值
        feats.append(price_norm.mean())

        # 3. 价格标准差（波动率）
        feats.append(price_norm.std())

        # 4. 最大回撤
        running_max = np.maximum.accumulate(price_norm)
        drawdown = (running_max - price_norm).max()
        feats.append(drawdown)

        # 5. 收盘价相对MA20位置（末根）
        ma20_last = sub["ma20"].iloc[-1]
        pos_ma20 = (price[-1] - ma20_last) / ma20_last
        feats.append(pos_ma20)

        # 6. 成交量萎缩率（末5日平均 vs 前5日平均）
        if len(vol_norm) >= 10:
            vol_recent = vol_norm[-5:].mean()
            vol_early = vol_norm[-10:-5].mean()
            vol_shrink = vol_recent / (vol_early + 1e-6) - 1
        else:
            vol_shrink = 0
        feats.append(vol_shrink)

        # 7. 成交量是否连续3日缩量
        vol_3dec = (np.diff(vol_norm[-4:]) < 0).sum() >= 3
        feats.append(float(vol_3dec))

        # 8. MACD 柱末值
        macd_last = sub.get("macd", [0])[-1]
        feats.append(macd_last)

        # 9. MACD 是否金叉（末根 DIF > DEA 且前一根<=）
        dif = sub.get("macd_dif", [0])
        dea = sub.get("macd_dea", [0])
        if len(dif) >= 2:
            gold = (dif[-1] > dea[-1]) and (dif[-2] <= dea[-2])
        else:
            gold = False
        feats.append(float(gold))

        # 10. RSI 末值
        rsi_last = sub.get("rsi", [50])[-1]
        feats.append(rsi_last)

        # 11. RSI 是否刚从超卖区回升（<30 → >30）
        if len(sub) >= 2:
            rsi_prev = sub["rsi"].iloc[-2]
            rsi_curr = sub["rsi"].iloc[-1]
            bounce = (rsi_prev < 30) and (rsi_curr > 30)
        else:
            bounce = False
        feats.append(float(bounce))

        # 12. 布林带位置（末根）(close - lower)/(upper - lower)
        boll_u = sub.get("boll_upper", [0])[-1]
        boll_l = sub.get("boll_lower", [0])[-1]
        if boll_u != boll_l:
            boll_pos = (price[-1] - boll_l) / (boll_u - boll_l)
        else:
            boll_pos = 0.5
        feats.append(boll_pos)

        # 13. 是否突破布林上轨
        break_upper = price[-1] > boll_u
        feats.append(float(break_upper))

        # 14. KDJ-K 末值
        kdj_k_last = sub.get("kdj_k", [50])[-1]
        feats.append(kdj_k_last)

        # 15. KDJ 金叉（K>D 且前一根<=）
        kdj_d = sub.get("kdj_d", [50])
        if len(kdj_k_last) >= 2:
            kdj_gold = (kdj_k_last[-1] > kdj_d[-1]) and (kdj_k_last[-2] <= kdj_d[-2])
        else:
            kdj_gold = False
        feats.append(float(kdj_gold))

        # 16. 连续阳线数量（末段）
        returns = np.diff(price_norm)
        pos_seq = 0
        for r in reversed(returns):
            if r > 0:
                pos_seq += 1
            else:
                break
        feats.append(pos_seq)

        # 17. 末3日涨幅平均值
        if len(returns) >= 3:
            last3 = returns[-3:]
            avg_ret3 = last3.mean()
        else:
            avg_ret3 = 0
        feats.append(avg_ret3)

        # 18. 末日涨幅
        last_ret = returns[-1] if len(returns) > 0 else 0
        feats.append(last_ret)

        # 19. 价格是否站上所有短期均线（MA5/10/20）
        ma5_last = sub.get("ma5", [0])[-1]
        ma10_last = sub.get("ma10", [0])[-1]
        above_mas = (price[-1] > ma5_last) and (price[-1] > ma10_last) and (price[-1] > ma20_last)
        feats.append(float(above_mas))

        # 20. 均线多头排列（MA5>MA10>MA20）
        mas_asc = (ma5_last > ma10_last) and (ma10_last > ma20_last)
        feats.append(float(mas_asc))

        # 21. 成交量变异系数（末10日）
        if len(vol_norm) >= 10:
            vol_cv = vol_norm[-10:].std() / (vol_norm[-10:].mean() + 1e-6)
        else:
            vol_cv = 0
        feats.append(vol_cv)

        # 22. 末5日成交量是否逐日放大
        if len(vol_norm) >= 6:
            vol_inc = np.all(np.diff(vol_norm[-5:]) > 0)
        else:
            vol_inc = False
        feats.append(float(vol_inc))

        # 23. 换手率末值（如字段存在）
        turnover_last = sub.get("turnover_rate", [0])[-1]
        feats.append(turnover_last)

        # 24. 量比末值（如字段存在）
        vol_ratio_last = sub.get("volume_ratio", [1])[-1]
        feats.append(vol_ratio_last)

        # 25. 日内振幅（末根）(high-low)/close
        high_last = sub["high"].iloc[-1]
        low_last = sub["low"].iloc[-1]
        amplitude = (high_last - low_last) / price[-1]
        feats.append(amplitude)

        # 26. 收盘价位于日内位置 (close-low)/(high-low)
        if high_last != low_last:
            close_pos = (price[-1] - low_last) / (high_last - low_last)
        else:
            close_pos = 0.5
        feats.append(close_pos)

        # 27. ATR 末值（如字段存在）
        atr_last = sub.get("atr14", [0])[-1] / price0   # 归一化
        feats.append(atr_last)

        # 28. 价格是否创20日新高
        recent_20_high = sub["high"].iloc[-20:].max()
        new_high = price[-1] >= recent_20_high
        feats.append(float(new_high))

        # 29. 价格是否创20日新低
        recent_20_low = sub["low"].iloc[-20:].min()
        new_low = price[-1] <= recent_20_low
        feats.append(float(new_low))

        # 30. 末3日每日收盘价>开盘价（阳线）
        if len(sub) >= 3:
            sub3 = sub.iloc[-3:]
            all_yang = (sub3["close"] > sub3["open"]).all()
        else:
            all_yang = False
        feats.append(float(all_yang))

        # 31. 末日OBV（能量潮）方向（简化版）
        if len(sub) >= 2:
            obv_dir = 1 if (price[-1] > price[-2] and vol[-1] > vol[-2]) else -1
        else:
            obv_dir = 0
        feats.append(obv_dir)

        # 32. 末5日价格斜率（线性回归 R²）
        if len(price_norm) >= 5:
            x = np.arange(5)
            y = price_norm[-5:]
            slope, _, r_value, _, _ = np.polyfit(x, y, 1, full=True)
            r2 = r_value[0] if len(r_value) > 0 else 0
        else:
            r2 = 0
        feats.append(r2)

        # 33. 末10日价格重心（时间加权平均）
        if len(price_norm) >= 10:
            weights = np.arange(1, 11)   # 越近权重越高
            重心 = np.average(price_norm[-10:], weights=weights)
        else:
            重心 = price_norm.mean() if len(price_norm) > 0 else 0
        feats.append(重心)

        return np.array(feats, dtype=np.float32)
    except Exception as e:
        # 任意一步失败返回 None，样本丢弃
        return None


def cosine_similarity_1d(a: np.ndarray, b: np.ndarray) -> float:
    """一维余弦相似度"""
    a_norm = np.linalg.norm(a)
    b_norm = np.linalg.norm(b)
    if a_norm == 0 or b_norm == 0:
        return 0.0
    return float(np.dot(a, b) / (a_norm * b_norm))