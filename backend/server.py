from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
from pathlib import Path
from typing import List
from datetime import datetime, timezone

from models import (
    UserSettings, UserSettingsUpdate, Position, Trade,
    AIDecisionLog, BotStatus, TopGainer, ManualTradeRequest,
    TradeSide, TradeStatus
)
from services.trade_engine import TradeEngine
from services.binance_service import BinanceService
from services.position_monitor import PositionMonitor

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI(title="Binance Futures AI Trading Bot")

# Create router with /api prefix
api_router = APIRouter(prefix="/api")

# Trade engine and position monitor instances
trade_engine = None
position_monitor = None
binance_service = BinanceService(testnet=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def startup_event():
    global trade_engine, position_monitor
    trade_engine = TradeEngine(db)
    position_monitor = PositionMonitor(db, binance_service)
    
    # Auto-start trade engine and position monitor
    await trade_engine.start()
    await position_monitor.start()
    logger.info("Application started with WebSocket real-time price feeds")


@app.on_event("shutdown")
async def shutdown_event():
    if trade_engine:
        await trade_engine.stop()
    if position_monitor:
        await position_monitor.stop()
    client.close()
    logger.info("Application shutdown")


# ===== BOT CONTROL =====

@api_router.get("/bot/status", response_model=BotStatus)
async def get_bot_status():
    """Get current bot status"""
    if not trade_engine:
        raise HTTPException(status_code=500, detail="Trade engine not initialized")
    return await trade_engine.get_status()


@api_router.post("/bot/start")
async def start_bot():
    """Start the trading bot"""
    if not trade_engine:
        raise HTTPException(status_code=500, detail="Trade engine not initialized")
    await trade_engine.start()
    return {"message": "Bot started successfully"}


@api_router.post("/bot/stop")
async def stop_bot():
    """Stop the trading bot"""
    if not trade_engine:
        raise HTTPException(status_code=500, detail="Trade engine not initialized")
    await trade_engine.stop()
    return {"message": "Bot stopped successfully"}


# ===== SETTINGS =====

@api_router.get("/settings", response_model=UserSettings)
async def get_settings():
    """Get user settings"""
    settings_doc = await db.settings.find_one({"user_id": "default_user"})
    
    if settings_doc:
        # Convert ISO strings back to datetime
        if isinstance(settings_doc.get('created_at'), str):
            settings_doc['created_at'] = datetime.fromisoformat(settings_doc['created_at'])
        if isinstance(settings_doc.get('updated_at'), str):
            settings_doc['updated_at'] = datetime.fromisoformat(settings_doc['updated_at'])
        settings_doc.pop('_id', None)
        return UserSettings(**settings_doc)
    
    # Create default
    default_settings = UserSettings()
    settings_dict = default_settings.model_dump()
    settings_dict['created_at'] = settings_dict['created_at'].isoformat()
    settings_dict['updated_at'] = settings_dict['updated_at'].isoformat()
    await db.settings.insert_one(settings_dict)
    return default_settings


@api_router.put("/settings", response_model=UserSettings)
async def update_settings(update: UserSettingsUpdate):
    """Update user settings"""
    # Get current settings
    current = await get_settings()
    
    # Update fields
    update_dict = update.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(current, key, value)
    
    current.updated_at = datetime.now()
    
    # Save to database
    settings_dict = current.model_dump()
    settings_dict['created_at'] = settings_dict['created_at'].isoformat()
    settings_dict['updated_at'] = settings_dict['updated_at'].isoformat()
    
    await db.settings.update_one(
        {"user_id": "default_user"},
        {"$set": settings_dict},
        upsert=True
    )
    
    return current


# ===== POSITIONS =====

@api_router.get("/positions")
async def get_positions(status: str = "OPEN"):
    """Get positions by status with real-time PnL"""
    query = {"user_id": "default_user"}
    if status:
        query["status"] = status
    
    positions = await db.positions.find(query, {"_id": 0}).to_list(1000)
    
    # Convert ISO strings back to datetime and add real-time PnL
    for pos in positions:
        if isinstance(pos.get('opened_at'), str):
            pos['opened_at'] = datetime.fromisoformat(pos['opened_at'])
        if pos.get('closed_at') and isinstance(pos.get('closed_at'), str):
            pos['closed_at'] = datetime.fromisoformat(pos['closed_at'])
        
        # Add real-time PnL for open positions
        if status == "OPEN":
            if position_monitor:
                pnl_data = await position_monitor.get_position_pnl(pos)
                pos['current_price'] = pnl_data['current_price']
                pos['unrealized_pnl_usdt'] = pnl_data['unrealized_pnl']
                pos['price_change_percent'] = pnl_data['price_change_percent']
            else:
                # Fallback if monitor not available
                pos['current_price'] = pos['entry_price']
                pos['unrealized_pnl_usdt'] = 0.0
                pos['price_change_percent'] = 0.0
    
    return positions


@api_router.get("/positions/{position_id}", response_model=Position)
async def get_position(position_id: str):
    """Get a specific position"""
    position = await db.positions.find_one({"id": position_id}, {"_id": 0})
    
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    
    # Convert ISO strings
    if isinstance(position.get('opened_at'), str):
        position['opened_at'] = datetime.fromisoformat(position['opened_at'])
    if position.get('closed_at') and isinstance(position['closed_at'], str):
        position['closed_at'] = datetime.fromisoformat(position['closed_at'])
    
    return Position(**position)

@api_router.post("/positions/{position_id}/close")
async def close_position(position_id: str):
    """Close a specific position at market price with order tracking"""
    try:
        # Get position
        position = await db.positions.find_one({
            "id": position_id,
            "status": TradeStatus.OPEN.value
        }, {"_id": 0})
        
        if not position:
            raise HTTPException(status_code=404, detail="Pozisyon bulunamadı veya zaten kapalı")
        
        symbol = position['symbol']
        quantity = position['quantity']
        entry_price = position['entry_price']
        leverage = position.get('leverage', 1)
        
        logger.info(f"🔄 Starting close process for {symbol} position...")
        
        # Step 1: Get current market price
        ticker = await binance_service.get_ticker(symbol)
        if not ticker:
            raise HTTPException(status_code=400, detail=f"{symbol} için anlık fiyat alınamadı")
        
        current_market_price = float(ticker['price'])
        logger.info(f"📊 Current market price for {symbol}: ${current_market_price}")
        
        # Step 2: Cancel TP and SL orders
        logger.info(f"🔄 Cancelling TP/SL orders for {symbol}...")
        try:
            if position.get('tp_order_id'):
                await binance_service.cancel_order(symbol, position['tp_order_id'])
                logger.info(f"✅ TP order cancelled")
            if position.get('sl_order_id'):
                await binance_service.cancel_order(symbol, position['sl_order_id'])
                logger.info(f"✅ SL order cancelled")
        except Exception as e:
            logger.warning(f"⚠️ Failed to cancel orders for {symbol}: {e}")
        
        # Step 3: Place market SELL order
        logger.info(f"🔄 Placing market SELL order for {symbol}: {quantity} units...")
        close_order = await binance_service.place_market_order(
            symbol=symbol,
            side="SELL",
            quantity=quantity
        )
        
        if not close_order:
            raise HTTPException(status_code=500, detail="Market SELL order yerleştirilemedi")
        
        order_id = str(close_order.get('orderId', ''))
        logger.info(f"✅ Market order placed. Order ID: {order_id}")
        
        # Step 4: Wait and get actual execution details
        logger.info(f"⏳ Waiting for order execution...")
        await asyncio.sleep(2)  # Wait for order to be filled
        
        # Get order status and actual fill price
        order_details = await binance_service.get_order_status(symbol, order_id)
        
        if order_details:
            order_status = order_details.get('status')
            avg_price = float(order_details.get('avgPrice', 0))
            executed_qty = float(order_details.get('executedQty', 0))
            
            logger.info(f"📋 Order Status: {order_status}")
            logger.info(f"💰 Actual Fill Price: ${avg_price}")
            logger.info(f"📦 Executed Quantity: {executed_qty}")
            
            # Use actual execution price
            if avg_price > 0:
                exit_price = avg_price
            else:
                # Fallback to market price if avg_price not available
                exit_price = current_market_price
                logger.warning(f"⚠️ Using market price as fallback: ${exit_price}")
        else:
            # Fallback to market price if order details not available
            exit_price = current_market_price
            logger.warning(f"⚠️ Could not get order details, using market price: ${exit_price}")
        
        # Step 5: Calculate realized PnL with ACTUAL execution price
        price_diff = exit_price - entry_price
        realized_pnl = (price_diff / entry_price) * position['position_size_usdt'] * leverage
        
        pnl_percent = (price_diff / entry_price) * 100
        
        logger.info(f"💵 Entry Price: ${entry_price}")
        logger.info(f"💵 Exit Price: ${exit_price}")
        logger.info(f"📊 Price Difference: ${price_diff} ({pnl_percent:.2f}%)")
        logger.info(f"💰 Realized PnL: ${realized_pnl:.2f}")
        
        # Step 6: Update position in database
        await db.positions.update_one(
            {"id": position_id},
            {
                "$set": {
                    "status": TradeStatus.CLOSED.value,
                    "exit_price": exit_price,
                    "realized_pnl_usdt": realized_pnl,
                    "closed_at": datetime.now(timezone.utc).isoformat(),
                    "close_order_id": order_id
                }
            }
        )
        
        logger.info(f"✅ Position {symbol} closed successfully!")
        
        return {
            "success": True,
            "message": f"{symbol} pozisyonu başarıyla kapatıldı",
            "details": {
                "symbol": symbol,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "market_price": current_market_price,
                "quantity": quantity,
                "realized_pnl": realized_pnl,
                "pnl_percent": pnl_percent,
                "order_id": order_id,
                "order_status": order_details.get('status') if order_details else "UNKNOWN"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error closing position {position_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/positions/close-all")
async def close_all_positions():
    """Close all open positions at market price"""
    try:
        # Get all open positions
        open_positions = await db.positions.find({
            "user_id": "default_user",
            "status": TradeStatus.OPEN.value
        }, {"_id": 0}).to_list(1000)
        
        if not open_positions:
            return {
                "success": True,
                "message": "Kapatılacak açık pozisyon yok",
                "closed_count": 0
            }
        
        closed_count = 0
        errors = []
        
        for position in open_positions:
            try:
                symbol = position['symbol']
                quantity = position['quantity']
                entry_price = position['entry_price']
                
                # Get current price
                ticker = await binance_service.get_ticker(symbol)
                if not ticker:
                    errors.append(f"{symbol}: Fiyat alınamadı")
                    continue
                
                exit_price = float(ticker['price'])
                
                # Cancel TP and SL orders
                try:
                    if position.get('tp_order_id'):
                        await binance_service.cancel_order(symbol, position['tp_order_id'])
                    if position.get('sl_order_id'):
                        await binance_service.cancel_order(symbol, position['sl_order_id'])
                except Exception as e:
                    logger.warning(f"Failed to cancel orders for {symbol}: {e}")
                
                # Close position with market order
                close_order = await binance_service.place_market_order(
                    symbol=symbol,
                    side="SELL",
                    quantity=quantity
                )
                
                if not close_order:
                    errors.append(f"{symbol}: Pozisyon kapatılamadı")
                    continue
                
                # Calculate realized PnL
                price_diff = exit_price - entry_price
                leverage = position.get('leverage', 1)
                realized_pnl = (price_diff / entry_price) * position['position_size_usdt'] * leverage
                
                # Update position in database
                await db.positions.update_one(
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
                
                closed_count += 1
                logger.info(f"✅ Closed {symbol}: PnL ${realized_pnl:.2f}")
                
            except Exception as e:
                errors.append(f"{position['symbol']}: {str(e)}")
                logger.error(f"Error closing {position['symbol']}: {e}")
        
        message = f"{closed_count} pozisyon başarıyla kapatıldı"
        if errors:
            message += f". {len(errors)} hata: {', '.join(errors[:3])}"
        
        return {
            "success": True,
            "message": message,
            "closed_count": closed_count,
            "errors": errors
        }
        
    except Exception as e:
        logger.error(f"Error closing all positions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/positions/manual")
async def open_manual_position(request: ManualTradeRequest):
    """Open a manual position with custom parameters"""
    try:
        # Get current price
        ticker = await binance_service.get_ticker(request.symbol)
        if not ticker:
            raise HTTPException(status_code=400, detail=f"Failed to get price for {request.symbol}")
        
        current_price = float(ticker['price'])
        
        # Calculate TP and SL prices
        raw_tp_price = current_price * (1 + request.target_profit_percent / 100)
        raw_sl_price = current_price * (1 - request.stop_loss_percent / 100)
        
        # Round prices based on magnitude
        if current_price >= 1000:
            tp_price = round(raw_tp_price, 1)
            sl_price = round(raw_sl_price, 1)
        elif current_price >= 100:
            tp_price = round(raw_tp_price, 2)
            sl_price = round(raw_sl_price, 2)
        elif current_price >= 1:
            tp_price = round(raw_tp_price, 3)
            sl_price = round(raw_sl_price, 3)
        else:
            tp_price = round(raw_tp_price, 6)
            sl_price = round(raw_sl_price, 6)
        
        # Calculate quantity
        raw_quantity = (request.position_size_usdt * request.leverage) / current_price
        
        if current_price > 1000:
            quantity = round(raw_quantity, 3)
        elif current_price > 100:
            quantity = round(raw_quantity, 2)
        elif current_price > 1:
            quantity = round(raw_quantity, 1)
        else:
            quantity = round(raw_quantity, 0)
        
        if quantity <= 0:
            quantity = 0.001 if current_price > 1000 else 1
        
        # Set leverage
        await binance_service.set_leverage(request.symbol, request.leverage)
        
        # Place market order
        entry_order = await binance_service.place_market_order(
            symbol=request.symbol,
            side="BUY",
            quantity=quantity
        )
        
        if not entry_order:
            raise HTTPException(status_code=500, detail="Failed to place entry order")
        
        # Place TP order
        tp_order = await binance_service.place_take_profit_market_order(
            symbol=request.symbol,
            side="SELL",
            quantity=quantity,
            stop_price=tp_price
        )
        
        # Place SL order
        sl_order = await binance_service.place_stop_market_order(
            symbol=request.symbol,
            side="SELL",
            quantity=quantity,
            stop_price=sl_price
        )
        
        # Save to database
        position = Position(
            symbol=request.symbol,
            side=TradeSide.LONG,
            status=TradeStatus.OPEN,
            entry_price=current_price,
            position_size_usdt=request.position_size_usdt,
            leverage=request.leverage,
            quantity=quantity,
            take_profit_price=tp_price,
            stop_loss_price=sl_price,
            entry_order_id=str(entry_order.get('orderId', '')),
            tp_order_id=str(tp_order.get('orderId', '')) if tp_order else None,
            sl_order_id=str(sl_order.get('orderId', '')) if sl_order else None
        )
        
        position_dict = position.model_dump()
        position_dict['opened_at'] = position_dict['opened_at'].isoformat()
        
        await db.positions.insert_one(position_dict)
        
        logger.info(f"Manual position opened: {request.symbol} at {current_price}, TP: {tp_price}, SL: {sl_price}")
        
        return {
            "success": True,
            "message": "Pozisyon başarıyla açıldı",
            "position": position_dict
        }
        
    except Exception as e:
        logger.error(f"Error opening manual position: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ===== AI DECISIONS =====

@api_router.get("/decisions", response_model=List[AIDecisionLog])
async def get_ai_decisions(limit: int = 50):
    """Get recent AI decisions"""
    decisions = await db.ai_decisions.find(
        {"user_id": "default_user"},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    # Convert ISO strings
    for dec in decisions:
        if isinstance(dec.get('created_at'), str):
            dec['created_at'] = datetime.fromisoformat(dec['created_at'])
    
    return decisions


# ===== MARKET DATA =====

@api_router.get("/market/top-gainers", response_model=List[TopGainer])
async def get_top_gainers(limit: int = 10):
    """Get top gaining symbols"""
    try:
        gainers = await binance_service.get_top_gainers(limit=limit)
        return gainers
    except Exception as e:
        logger.error(f"Error fetching top gainers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/market/all-symbols")
async def get_all_futures_symbols():
    """Get all available futures trading symbols"""
    try:
        symbols = await binance_service.get_top_gainers(limit=200)  # Get many symbols
        # Return unique symbols sorted
        symbol_list = sorted(list(set([s['symbol'] for s in symbols])))
        return symbol_list
    except Exception as e:
        logger.error(f"Error fetching symbols: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/market/analyze-symbol")
async def analyze_symbol(symbol: str):
    """Analyze a specific symbol with AI"""
    try:
        logger.info(f"🔍 Analyzing {symbol}...")
        
        # Fetch market data
        candles = await binance_service.get_candles(symbol, interval="5m", limit=100)
        if not candles or len(candles) < 50:
            raise HTTPException(status_code=400, detail=f"{symbol} için yeterli veri yok")
        
        # Calculate indicators
        from services.indicators import calculate_indicators
        indicators = calculate_indicators(candles)
        if not indicators:
            raise HTTPException(status_code=400, detail="Göstergeler hesaplanamadı")
        
        # Get account info
        account = await binance_service.get_account_balance()
        
        # Get funding rate and OI
        funding_rate = await binance_service.get_funding_rate(symbol)
        oi_data = await binance_service.get_open_interest(symbol)
        
        # Get settings for user params
        settings = await db.settings.find_one({"user_id": "default_user"}, {"_id": 0})
        if settings:
            if isinstance(settings.get('created_at'), str):
                settings['created_at'] = datetime.fromisoformat(settings['created_at'])
            if isinstance(settings.get('updated_at'), str):
                settings['updated_at'] = datetime.fromisoformat(settings['updated_at'])
        
        from models import UserSettings
        user_settings = UserSettings(**settings) if settings else UserSettings()
        
        # Build decision input
        decision_input = {
            "symbol": symbol,
            "timeframe": "5m",
            "candles": candles[-10:],
            "indicators": indicators,
            "account": {
                "equity_usdt": account['total_equity_usdt'],
                "free_margin_usdt": account['available_balance_usdt'],
            },
            "user_params": {
                "position_size_mode": user_settings.position_size_mode.value,
                "position_size_value": user_settings.position_size_value,
                "max_leverage": user_settings.max_leverage,
                "min_leverage": user_settings.min_leverage,
                "target_profit_percent": user_settings.target_profit_percent,
                "stop_loss_percent": user_settings.stop_loss_percent,
            }
        }
        
        decision_input["indicators"]["funding_rate"] = funding_rate
        decision_input["indicators"]["oi_24h_change_percent"] = oi_data['change_24h_percent']
        
        # Get AI decision
        from services.ai_service import AIDecisionService
        ai_service = AIDecisionService()
        decision = await ai_service.make_decision(decision_input)
        
        # Log to database
        from models import AIDecisionLog
        log = AIDecisionLog(
            symbol=symbol,
            timeframe="5m",
            decision=decision,
            input_data=decision_input,
            was_executed=False
        )
        
        log_dict = log.model_dump()
        log_dict['created_at'] = log_dict['created_at'].isoformat()
        await db.ai_decisions.insert_one(log_dict)
        
        logger.info(f"✅ Analysis complete for {symbol}: {decision.action.value}")
        
        return {
            "symbol": symbol,
            "decision": decision.model_dump(),
            "current_price": candles[-1]['close'],
            "indicators": {
                "rsi": indicators['rsi'],
                "ema_trend": indicators['ema_trend'],
                "volume_ma_ratio": indicators['volume_ma_ratio'],
                "funding_rate": funding_rate,
                "oi_change": oi_data['change_24h_percent']
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/market/prices")
async def get_current_prices():
    """Get current prices for all tracked symbols"""
    if not position_monitor:
        return {}
    return position_monitor.current_prices


# Include router
app.include_router(api_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)