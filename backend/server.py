from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from typing import List
from datetime import datetime

from models import (
    UserSettings, UserSettingsUpdate, Position, Trade,
    AIDecisionLog, BotStatus, TopGainer
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
    position_monitor = PositionMonitor(db)
    
    # Auto-start trade engine and position monitor
    await trade_engine.start()
    await position_monitor.start()
    logger.info("Application started, trade engine and position monitor initialized")


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
    gainers = await binance_service.get_top_gainers(limit=limit)
    return gainers


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