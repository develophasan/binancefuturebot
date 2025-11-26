from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum
import uuid


class PositionSizeMode(str, Enum):
    FIXED_USDT = "FIXED_USDT"
    PERCENT_OF_EQUITY = "PERCENT_OF_EQUITY"


class RiskProfile(str, Enum):
    CONSERVATIVE = "CONSERVATIVE"
    MODERATE = "MODERATE"
    AGGRESSIVE = "AGGRESSIVE"


class TradeAction(str, Enum):
    OPEN_LONG = "OPEN_LONG"
    SKIP = "SKIP"


class TradeSide(str, Enum):
    LONG = "LONG"


class TradeStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class UserSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = "default_user"
    
    # Position sizing
    position_size_mode: PositionSizeMode = PositionSizeMode.FIXED_USDT
    position_size_value: float = 50.0  # USDT or percentage (min 100 USDT notional for Futures)
    
    # Leverage
    max_leverage: int = 5
    min_leverage: int = 2
    
    # Risk parameters (aggressive for crypto futures)
    target_profit_percent: float = 4.0  # 4% TP (agresif)
    stop_loss_percent: float = 2.0  # 2% SL (R/R = 2:1, agresif)
    max_risk_per_trade_percent: float = 0.02  # 2% of equity per trade
    risk_profile: RiskProfile = RiskProfile.MODERATE
    
    # Limits
    max_open_positions: int = 3
    max_trades_per_day: int = 10
    max_daily_loss_usdt: float = 10.0
    
    # Trading hours (24/7 by default)
    trading_start_hour: int = 0
    trading_end_hour: int = 23
    
    # Symbol whitelist (Top 10 popular coins)
    symbol_whitelist: List[str] = Field(default_factory=lambda: [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
        "ADAUSDT", "DOGEUSDT", "MATICUSDT", "DOTUSDT", "AVAXUSDT"
    ])
    
    # Enable/disable bot
    is_active: bool = True
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserSettingsUpdate(BaseModel):
    position_size_mode: Optional[PositionSizeMode] = None
    position_size_value: Optional[float] = None
    max_leverage: Optional[int] = None
    min_leverage: Optional[int] = None
    target_profit_percent: Optional[float] = None
    stop_loss_percent: Optional[float] = None
    max_risk_per_trade_percent: Optional[float] = None
    risk_profile: Optional[RiskProfile] = None
    max_open_positions: Optional[int] = None
    max_trades_per_day: Optional[int] = None
    max_daily_loss_usdt: Optional[float] = None
    trading_start_hour: Optional[int] = None
    trading_end_hour: Optional[int] = None
    symbol_whitelist: Optional[List[str]] = None
    is_active: Optional[bool] = None


class ManualTradeRequest(BaseModel):
    symbol: str
    position_size_usdt: float
    leverage: int
    target_profit_percent: float
    stop_loss_percent: float


class Position(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = "default_user"
    
    symbol: str
    side: TradeSide = TradeSide.LONG
    status: TradeStatus = TradeStatus.OPEN
    
    # Entry
    entry_price: float
    position_size_usdt: float
    leverage: int
    quantity: float
    
    # Exit targets
    take_profit_price: float
    stop_loss_price: float
    
    # Exit actual
    exit_price: Optional[float] = None
    realized_pnl_usdt: Optional[float] = None
    
    # Binance order IDs
    entry_order_id: Optional[str] = None
    tp_order_id: Optional[str] = None
    sl_order_id: Optional[str] = None
    
    # Timestamps
    opened_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    closed_at: Optional[datetime] = None


class Trade(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = "default_user"
    position_id: str
    
    symbol: str
    side: TradeSide
    status: TradeStatus
    
    entry_price: float
    exit_price: Optional[float] = None
    quantity: float
    leverage: int
    
    realized_pnl_usdt: Optional[float] = None
    
    opened_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    closed_at: Optional[datetime] = None


class AIDecision(BaseModel):
    action: TradeAction
    confidence: float
    reason: str
    position: Optional[Dict[str, Any]] = None
    risk: Optional[Dict[str, Any]] = None


class AIDecisionLog(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = "default_user"
    
    symbol: str
    timeframe: str
    
    decision: AIDecision
    input_data: Dict[str, Any]
    
    was_executed: bool = False
    execution_error: Optional[str] = None
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BotStatus(BaseModel):
    is_running: bool
    is_active: bool
    open_positions_count: int
    trades_today: int
    daily_pnl_usdt: float
    total_equity_usdt: float
    last_signal_time: Optional[datetime] = None


class TopGainer(BaseModel):
    symbol: str
    price_change_percent: float
    volume_24h: float
    price: float