import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
from services.binance_service import BinanceService
from services.ai_service import AIDecisionService
from services.indicators import calculate_indicators
from models import (
    UserSettings, Position, Trade, AIDecisionLog,
    TradeAction, TradeSide, TradeStatus, BotStatus
)
import asyncio

logger = logging.getLogger(__name__)


class TradeEngine:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.binance = BinanceService(testnet=True)
        self.ai_service = AIDecisionService()
        self.is_running = False
        self.last_signal_time = None
    
    async def start(self):
        """Start the trading engine"""
        if self.is_running:
            logger.warning("Trade engine already running")
            return
        
        self.is_running = True
        logger.info("Trade engine started")
        
        # Run main loop
        asyncio.create_task(self._main_loop())
    
    async def stop(self):
        """Stop the trading engine"""
        self.is_running = False
        logger.info("Trade engine stopped")
    
    async def _main_loop(self):
        """Main trading loop"""
        while self.is_running:
            try:
                # Get user settings
                settings = await self._get_settings()
                
                if not settings.is_active:
                    logger.info("Bot is inactive, waiting...")
                    await asyncio.sleep(60)
                    continue
                
                # Check trading hours
                if not self._is_trading_hours(settings):
                    logger.info("Outside trading hours")
                    await asyncio.sleep(300)  # 5 minutes
                    continue
                
                # Get dynamic symbol list
                symbol_list = await self._get_symbol_list(settings)
                
                # Process each symbol
                for symbol in symbol_list:
                    try:
                        await self._process_symbol(symbol, settings)
                    except Exception as e:
                        logger.error(f"Error processing {symbol}: {e}")
                    
                    await asyncio.sleep(2)  # Rate limiting
                
                # Update last signal time
                self.last_signal_time = datetime.now(timezone.utc)
                
                # Wait before next cycle (60 seconds for quality analysis)
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                await asyncio.sleep(60)
    
    async def _process_symbol(self, symbol: str, settings: UserSettings):
        """Process trading signal for a symbol"""
        logger.info(f"Processing {symbol}")
        
        # Fetch market data
        candles = await self.binance.get_candles(symbol, interval="5m", limit=100)
        if not candles or len(candles) < 50:
            logger.warning(f"Insufficient candles for {symbol}")
            return
        
        # Calculate indicators
        indicators = calculate_indicators(candles)
        if not indicators:
            logger.warning(f"Failed to calculate indicators for {symbol}")
            return
        
        # Get account info
        account = await self.binance.get_account_balance()
        
        # Get funding rate
        funding_rate = await self.binance.get_funding_rate(symbol)
        
        # Get open interest
        oi_data = await self.binance.get_open_interest(symbol)
        
        # Get risk state
        risk_state = await self._get_risk_state(settings)
        
        # Build decision input
        decision_input = {
            "symbol": symbol,
            "timeframe": "5m",
            "candles": candles[-10:],  # Last 10 candles for context
            "indicators": indicators,
            "account": {
                "equity_usdt": account['total_equity_usdt'],
                "free_margin_usdt": account['available_balance_usdt'],
                "used_margin_usdt": account['used_margin_usdt'],
                "daily_realized_pnl_usdt": risk_state['daily_pnl'],
                "daily_unrealized_pnl_usdt": 0.0,
                "max_daily_loss_usdt": settings.max_daily_loss_usdt
            },
            "risk_state": risk_state,
            "user_params": {
                "position_size_mode": settings.position_size_mode.value,
                "position_size_value": settings.position_size_value,
                "max_leverage": settings.max_leverage,
                "min_leverage": settings.min_leverage,
                "target_profit_percent": settings.target_profit_percent,
                "stop_loss_percent": settings.stop_loss_percent,
                "max_risk_per_trade_percent": settings.max_risk_per_trade_percent,
                "risk_profile": settings.risk_profile.value
            },
            "context": {
                "now_iso": datetime.now(timezone.utc).isoformat(),
                "timezone": "UTC",
                "symbol_whitelist": settings.symbol_whitelist
            }
        }
        
        # Add market context
        decision_input["indicators"]["funding_rate"] = funding_rate
        decision_input["indicators"]["oi_24h_change_percent"] = oi_data['change_24h_percent']
        
        # Get AI decision
        decision = await self.ai_service.make_decision(decision_input)
        
        # Log decision
        await self._log_decision(symbol, decision, decision_input)
        
        # Execute if needed (professional threshold for profitability)
        if decision.action == TradeAction.OPEN_LONG and decision.confidence >= 0.55:
            if risk_state['trading_allowed']:
                await self._execute_long(symbol, decision, settings, candles[-1]['close'])
            else:
                logger.info(f"Trading not allowed for {symbol}, skipping execution")
        else:
            logger.info(f"Decision for {symbol}: {decision.action.value} - {decision.reason}")
    
    async def _execute_long(self, symbol: str, decision, settings: UserSettings, current_price: float):
        """Execute a long position"""
        try:
            logger.info(f"Executing LONG for {symbol}")
            
            # Extract position parameters
            position_params = decision.position or {}
            risk_params = decision.risk or {}
            
            leverage = position_params.get('leverage', settings.min_leverage)
            leverage = max(settings.min_leverage, min(settings.max_leverage, leverage))
            
            position_size_usdt = position_params.get('position_size_value', settings.position_size_value)
            
            # Calculate TP and SL with AI recommendations (or defaults)
            tp_percent = risk_params.get('target_profit_percent', 1.5)  # Default 1.5% TP
            sl_percent = risk_params.get('stop_loss_percent', 0.4)  # Default 0.4% SL
            
            # Ensure minimum Risk/Reward ratio of 2:1
            if tp_percent / sl_percent < 2.0:
                tp_percent = sl_percent * 2.5  # Force 2.5:1 R/R minimum
            
            raw_tp_price = current_price * (1 + tp_percent / 100)
            raw_sl_price = current_price * (1 - sl_percent / 100)
            
            # Round TP/SL prices based on current price magnitude
            if current_price >= 1000:  # BTC-like
                tp_price = round(raw_tp_price, 1)
                sl_price = round(raw_sl_price, 1)
            elif current_price >= 100:  # ETH-like
                tp_price = round(raw_tp_price, 2)
                sl_price = round(raw_sl_price, 2)
            elif current_price >= 1:  # Mid-range
                tp_price = round(raw_tp_price, 3)
                sl_price = round(raw_sl_price, 3)
            else:  # Low price coins
                tp_price = round(raw_tp_price, 6)
                sl_price = round(raw_sl_price, 6)
            
            # Calculate quantity and round to proper precision
            raw_quantity = (position_size_usdt * leverage) / current_price
            
            # Round to 3 decimal places (works for most futures contracts)
            # BTC/ETH typically need 3 decimals, altcoins may need more
            if current_price > 1000:  # BTC-like
                quantity = round(raw_quantity, 3)
            elif current_price > 100:  # ETH-like
                quantity = round(raw_quantity, 2)
            elif current_price > 1:  # Mid-range
                quantity = round(raw_quantity, 1)
            else:  # Low price coins
                quantity = round(raw_quantity, 0)
            
            # Ensure minimum quantity
            if quantity <= 0:
                quantity = 0.001 if current_price > 1000 else 1
            
            # Set leverage
            await self.binance.set_leverage(symbol, leverage)
            
            # Place market order
            entry_order = await self.binance.place_market_order(
                symbol=symbol,
                side="BUY",
                quantity=quantity
            )
            
            if not entry_order:
                logger.error(f"Failed to place entry order for {symbol}")
                return
            
            # Place TP order
            tp_order = await self.binance.place_take_profit_market_order(
                symbol=symbol,
                side="SELL",
                quantity=quantity,
                stop_price=tp_price
            )
            
            # Place SL order
            sl_order = await self.binance.place_stop_market_order(
                symbol=symbol,
                side="SELL",
                quantity=quantity,
                stop_price=sl_price
            )
            
            # Save position to database
            position = Position(
                symbol=symbol,
                side=TradeSide.LONG,
                status=TradeStatus.OPEN,
                entry_price=current_price,
                position_size_usdt=position_size_usdt,
                leverage=leverage,
                quantity=quantity,
                take_profit_price=tp_price,
                stop_loss_price=sl_price,
                entry_order_id=str(entry_order.get('orderId', '')),
                tp_order_id=str(tp_order.get('orderId', '')) if tp_order else None,
                sl_order_id=str(sl_order.get('orderId', '')) if sl_order else None
            )
            
            position_dict = position.model_dump()
            position_dict['opened_at'] = position_dict['opened_at'].isoformat()
            
            await self.db.positions.insert_one(position_dict)
            
            logger.info(f"Position opened: {symbol} at {current_price}, TP: {tp_price}, SL: {sl_price}")
            
        except Exception as e:
            logger.error(f"Error executing long for {symbol}: {e}", exc_info=True)
    
    async def _get_symbol_list(self, settings: UserSettings) -> List[str]:
        """Get dynamic symbol list (whitelist + top gainers) - AGGRESSIVE for testnet"""
        symbols = list(settings.symbol_whitelist)
        
        # Add BEST top gainers only (quality over quantity)
        try:
            top_gainers = await self.binance.get_top_gainers(limit=5)  # Only top 5 strongest
            for gainer in top_gainers:
                symbol = gainer['symbol']
                # Only add if volume is significant (>5M USDT)
                if symbol not in symbols and gainer['volume_24h'] > 5000000:
                    symbols.append(symbol)
                    logger.info(f"🎯 Tracking strong gainer: {symbol} (+{gainer['price_change_percent']:.2f}%, Vol: ${gainer['volume_24h']/1000000:.1f}M)")
        except Exception as e:
            logger.error(f"Error fetching top gainers: {e}")
        
        logger.info(f"📊 Analyzing {len(symbols)} HIGH-QUALITY symbols this cycle")
        return symbols
    
    async def _get_settings(self) -> UserSettings:
        """Get user settings from database"""
        settings_doc = await self.db.settings.find_one({"user_id": "default_user"})
        
        if settings_doc:
            # Convert ISO strings back to datetime
            if isinstance(settings_doc.get('created_at'), str):
                settings_doc['created_at'] = datetime.fromisoformat(settings_doc['created_at'])
            if isinstance(settings_doc.get('updated_at'), str):
                settings_doc['updated_at'] = datetime.fromisoformat(settings_doc['updated_at'])
            
            settings_doc.pop('_id', None)
            return UserSettings(**settings_doc)
        
        # Create default settings
        default_settings = UserSettings()
        settings_dict = default_settings.model_dump()
        settings_dict['created_at'] = settings_dict['created_at'].isoformat()
        settings_dict['updated_at'] = settings_dict['updated_at'].isoformat()
        
        await self.db.settings.insert_one(settings_dict)
        return default_settings
    
    async def _get_risk_state(self, settings: UserSettings) -> Dict[str, Any]:
        """Calculate current risk state"""
        # Count open positions
        open_positions = await self.db.positions.count_documents({
            "user_id": "default_user",
            "status": TradeStatus.OPEN.value
        })
        
        # Count trades today
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        trades_today = await self.db.positions.count_documents({
            "user_id": "default_user",
            "opened_at": {"$gte": today_start.isoformat()}
        })
        
        # Calculate daily PnL
        closed_positions = await self.db.positions.find({
            "user_id": "default_user",
            "status": TradeStatus.CLOSED.value,
            "closed_at": {"$gte": today_start.isoformat()}
        }).to_list(1000)
        
        daily_pnl = sum([p.get('realized_pnl_usdt', 0) for p in closed_positions])
        
        # Check if trading allowed
        trading_allowed = (
            open_positions < settings.max_open_positions and
            trades_today < settings.max_trades_per_day and
            abs(daily_pnl) < settings.max_daily_loss_usdt
        )
        
        remaining_loss_capacity = settings.max_daily_loss_usdt - abs(daily_pnl)
        
        return {
            "open_positions_count": open_positions,
            "max_open_positions": settings.max_open_positions,
            "trades_opened_today": trades_today,
            "max_trades_per_day": settings.max_trades_per_day,
            "trading_allowed": trading_allowed,
            "remaining_daily_loss_capacity_usdt": remaining_loss_capacity,
            "daily_pnl": daily_pnl
        }
    
    def _is_trading_hours(self, settings: UserSettings) -> bool:
        """Check if current time is within trading hours"""
        now = datetime.now(timezone.utc)
        current_hour = now.hour
        
        if settings.trading_start_hour <= settings.trading_end_hour:
            return settings.trading_start_hour <= current_hour <= settings.trading_end_hour
        else:
            # Handle overnight trading (e.g., 22:00 - 06:00)
            return current_hour >= settings.trading_start_hour or current_hour <= settings.trading_end_hour
    
    async def _log_decision(self, symbol: str, decision, decision_input: Dict[str, Any]):
        """Log AI decision to database"""
        log = AIDecisionLog(
            symbol=symbol,
            timeframe="5m",
            decision=decision,
            input_data=decision_input,
            was_executed=(decision.action == TradeAction.OPEN_LONG)
        )
        
        log_dict = log.model_dump()
        log_dict['created_at'] = log_dict['created_at'].isoformat()
        
        await self.db.ai_decisions.insert_one(log_dict)
    
    async def get_status(self) -> BotStatus:
        """Get current bot status"""
        settings = await self._get_settings()
        risk_state = await self._get_risk_state(settings)
        account = await self.binance.get_account_balance()
        
        return BotStatus(
            is_running=self.is_running,
            is_active=settings.is_active,
            open_positions_count=risk_state['open_positions_count'],
            trades_today=risk_state['trades_opened_today'],
            daily_pnl_usdt=risk_state['daily_pnl'],
            total_equity_usdt=account['total_equity_usdt'],
            last_signal_time=self.last_signal_time
        )