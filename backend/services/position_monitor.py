import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from services.binance_service import BinanceService
from services.websocket_price_feed import get_price_feed
from models import TradeStatus

logger = logging.getLogger(__name__)


class PositionMonitor:
    """Monitor open positions and check TP/SL conditions"""
    
    def __init__(self, db: AsyncIOMotorDatabase, binance_service: BinanceService):
        self.db = db
        self.binance = binance_service
        self.current_prices: Dict[str, float] = {}
        self.is_running = False
        self.price_feed = get_price_feed(testnet=binance_service.testnet)
        
        # Register price callback
        self.price_feed.add_price_callback(self._on_price_update)
    
    def _on_price_update(self, symbol: str, price: float):
        """Callback when price updates from WebSocket"""
        self.current_prices[symbol] = price
    
    async def start(self):
        """Start position monitoring"""
        if self.is_running:
            logger.warning("Position monitor already running")
            return
        
        self.is_running = True
        logger.info("🚀 Position monitor started with WebSocket real-time feeds")
        
        # Start WebSocket price feed
        await self.price_feed.start()
        
        # Run monitoring loop (lighter now, just checks TP/SL)
        asyncio.create_task(self._monitor_loop())
    
    async def stop(self):
        """Stop position monitoring"""
        self.is_running = False
        await self.price_feed.stop()
        logger.info("Position monitor stopped")
    
    async def _monitor_loop(self):
        """Main monitoring loop - checks positions every 1 second"""
        while self.is_running:
            try:
                await self._check_all_positions()
                await asyncio.sleep(1)  # Check every 1 second for ultra-fast updates
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}", exc_info=True)
                await asyncio.sleep(2)
    
    async def _check_all_positions(self):
        """Check all open positions"""
        try:
            # Get all open positions
            positions = await self.db.positions.find({
                "status": TradeStatus.OPEN.value
            }).to_list(100)
            
            if not positions:
                logger.debug("No open positions to monitor")
                return
            
            # Get unique symbols
            symbols = list(set([pos['symbol'] for pos in positions]))
            logger.info(f"📊 Monitoring {len(positions)} positions: {symbols}")
            
            # Fetch current prices for all symbols
            await self._update_prices(symbols)
            logger.info(f"💰 Current prices: {self.current_prices}")
            
            # Check each position
            for position in positions:
                await self._check_position(position)
                
        except Exception as e:
            logger.error(f"Error checking positions: {e}")
    
    async def _update_prices(self, symbols: list):
        """Update current prices for symbols"""
        for symbol in symbols:
            try:
                # Get latest candle (1 candle is enough for current price)
                candles = await self.binance.get_candles(symbol, interval="1m", limit=1)
                if candles:
                    self.current_prices[symbol] = candles[0]['close']
            except Exception as e:
                logger.error(f"Error fetching price for {symbol}: {e}")
    
    async def _check_position(self, position: Dict[str, Any]):
        """Check if position should be closed (TP/SL hit)"""
        try:
            symbol = position['symbol']
            current_price = self.current_prices.get(symbol)
            
            if not current_price:
                return
            
            entry_price = position['entry_price']
            tp_price = position['take_profit_price']
            sl_price = position['stop_loss_price']
            
            # Calculate unrealized PnL
            side = position['side']
            quantity = position['quantity']
            leverage = position['leverage']
            position_size_usdt = position['position_size_usdt']
            
            if side == "LONG":
                price_change_percent = ((current_price - entry_price) / entry_price) * 100
                unrealized_pnl = (current_price - entry_price) * quantity * leverage
                
                # Check TP hit
                if current_price >= tp_price:
                    logger.info(f"✅ TP HIT! {symbol} at {current_price} (target: {tp_price})")
                    await self._close_position(position, current_price, "TP_HIT")
                    return
                
                # Check SL hit
                if current_price <= sl_price:
                    logger.info(f"❌ SL HIT! {symbol} at {current_price} (stop: {sl_price})")
                    await self._close_position(position, current_price, "SL_HIT")
                    return
                
                # Log unrealized PnL periodically
                if abs(unrealized_pnl) > 0.1:
                    logger.debug(f"💰 {symbol}: ${unrealized_pnl:.2f} ({price_change_percent:+.2f}%)")
                
        except Exception as e:
            logger.error(f"Error checking position {position.get('id')}: {e}")
    
    async def _close_position(self, position: Dict[str, Any], exit_price: float, reason: str):
        """Close position and calculate realized PnL"""
        try:
            symbol = position['symbol']
            entry_price = position['entry_price']
            quantity = position['quantity']
            leverage = position['leverage']
            position_size_usdt = position['position_size_usdt']
            
            # Calculate realized PnL
            if position['side'] == "LONG":
                price_change = exit_price - entry_price
                realized_pnl = price_change * quantity * leverage
            
            # Update position in database
            await self.db.positions.update_one(
                {"id": position['id']},
                {
                    "$set": {
                        "status": TradeStatus.CLOSED.value,
                        "exit_price": exit_price,
                        "realized_pnl_usdt": realized_pnl,
                        "closed_at": datetime.now(timezone.utc).isoformat()
                    }
                }
            )
            
            pnl_emoji = "🟢" if realized_pnl > 0 else "🔴"
            logger.info(
                f"{pnl_emoji} POSITION CLOSED: {symbol} | "
                f"Entry: ${entry_price:.2f} → Exit: ${exit_price:.2f} | "
                f"PnL: ${realized_pnl:.2f} | Reason: {reason}"
            )
            
        except Exception as e:
            logger.error(f"Error closing position: {e}", exc_info=True)
    
    def get_current_price(self, symbol: str) -> float:
        """Get cached current price for a symbol"""
        return self.current_prices.get(symbol, 0.0)
    
    async def get_position_pnl(self, position: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate current PnL for a position"""
        try:
            symbol = position['symbol']
            current_price = self.current_prices.get(symbol, position['entry_price'])
            entry_price = position['entry_price']
            quantity = position['quantity']
            leverage = position['leverage']
            
            if position['side'] == "LONG":
                price_change_percent = ((current_price - entry_price) / entry_price) * 100
                unrealized_pnl = (current_price - entry_price) * quantity * leverage
            else:
                price_change_percent = ((entry_price - current_price) / entry_price) * 100
                unrealized_pnl = (entry_price - current_price) * quantity * leverage
            
            return {
                "current_price": current_price,
                "unrealized_pnl": unrealized_pnl,
                "price_change_percent": price_change_percent
            }
        except Exception as e:
            logger.error(f"Error calculating PnL: {e}")
            return {
                "current_price": position['entry_price'],
                "unrealized_pnl": 0.0,
                "price_change_percent": 0.0
            }
