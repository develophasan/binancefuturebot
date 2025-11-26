import numpy as np
from typing import List, Dict, Any
import talib
import logging

logger = logging.getLogger(__name__)


def calculate_ema(closes: np.ndarray, period: int) -> float:
    """Calculate Exponential Moving Average"""
    try:
        ema_values = talib.EMA(closes, timeperiod=period)
        return float(ema_values[-1]) if not np.isnan(ema_values[-1]) else closes[-1]
    except Exception as e:
        logger.error(f"Error calculating EMA: {e}")
        return closes[-1]


def calculate_rsi(closes: np.ndarray, period: int = 14) -> float:
    """Calculate Relative Strength Index"""
    try:
        rsi_values = talib.RSI(closes, timeperiod=period)
        return float(rsi_values[-1]) if not np.isnan(rsi_values[-1]) else 50.0
    except Exception as e:
        logger.error(f"Error calculating RSI: {e}")
        return 50.0


def calculate_atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> float:
    """Calculate Average True Range"""
    try:
        atr_values = talib.ATR(highs, lows, closes, timeperiod=period)
        return float(atr_values[-1]) if not np.isnan(atr_values[-1]) else 0.0
    except Exception as e:
        logger.error(f"Error calculating ATR: {e}")
        return 0.0


def calculate_indicators(candles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate all technical indicators from candle data"""
    if len(candles) < 50:
        logger.warning(f"Not enough candles for indicator calculation: {len(candles)}")
        return {}
    
    # Convert to numpy arrays
    closes = np.array([c['close'] for c in candles])
    highs = np.array([c['high'] for c in candles])
    lows = np.array([c['low'] for c in candles])
    volumes = np.array([c['volume'] for c in candles])
    
    # EMAs
    ema_fast = calculate_ema(closes, 9)
    ema_slow = calculate_ema(closes, 21)
    ema_trend = "UP" if ema_fast > ema_slow else "DOWN" if ema_fast < ema_slow else "FLAT"
    
    # RSI
    rsi = calculate_rsi(closes, 14)
    if rsi <= 30:
        rsi_state = "OVERSOLD"
    elif rsi >= 70:
        rsi_state = "OVERBOUGHT"
    else:
        rsi_state = "NEUTRAL"
    
    # ATR
    atr = calculate_atr(highs, lows, closes, 14)
    
    # Volatility (standard deviation of returns)
    returns = np.diff(closes) / closes[:-1]
    volatility = float(np.std(returns)) if len(returns) > 0 else 0.0
    
    # Volume analysis
    volume_ma = float(np.mean(volumes[-20:]))
    current_volume = float(volumes[-1])
    volume_ma_ratio = current_volume / volume_ma if volume_ma > 0 else 1.0
    
    return {
        "ema_fast": ema_fast,
        "ema_slow": ema_slow,
        "ema_trend": ema_trend,
        "rsi": rsi,
        "rsi_state": rsi_state,
        "atr": atr,
        "volatility": volatility,
        "volume_ma_ratio": volume_ma_ratio
    }