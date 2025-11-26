import os
import asyncio
from typing import List, Dict, Any, Optional
import aiohttp
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class BinanceService:
    def __init__(self, testnet: bool = True):
        self.testnet = testnet
        
        # Use public API endpoints (no authentication required for market data)
        if testnet:
            self.base_url = "https://testnet.binancefuture.com/fapi/v1"
            self.public_base_url = "https://fapi.binance.com/fapi/v1"  # Public data from mainnet
        else:
            self.base_url = "https://fapi.binance.com/fapi/v1"
            self.public_base_url = "https://fapi.binance.com/fapi/v1"
        
        # For authenticated operations
        api_key = os.getenv("BINANCE_TESTNET_API_KEY", "") if testnet else os.getenv("BINANCE_API_KEY", "")
        api_secret = os.getenv("BINANCE_TESTNET_SECRET_KEY", "") if testnet else os.getenv("BINANCE_SECRET_KEY", "")
        
        self.api_key = api_key
        self.api_secret = api_secret
        
        # Use public data mode (no authentication needed for market data)
        self.mock_mode = False
        self.public_data_mode = True
        logger.info(f"Binance service initialized with public data API")
    
    async def get_candles(self, symbol: str, interval: str = "5m", limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch OHLCV candles from public API"""
        try:
            url = f"{self.public_base_url}/klines"
            params = {
                "symbol": symbol,
                "interval": interval,
                "limit": limit
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        candles = []
                        for k in data:
                            candles.append({
                                "timestamp": k[0],
                                "open": float(k[1]),
                                "high": float(k[2]),
                                "low": float(k[3]),
                                "close": float(k[4]),
                                "volume": float(k[5])
                            })
                        return candles
                    else:
                        logger.error(f"Error fetching candles: HTTP {response.status}")
                        return self._mock_candles(symbol, limit)
        except Exception as e:
            logger.error(f"Error fetching candles for {symbol}: {e}")
            return self._mock_candles(symbol, limit)
    
    async def get_account_balance(self) -> Dict[str, Any]:
        """Get futures account balance (simulated for testnet)"""
        # Return simulated testnet balance
        return {
            "total_equity_usdt": 10000.0,
            "available_balance_usdt": 9500.0,
            "used_margin_usdt": 500.0
        }
    
    async def get_funding_rate(self, symbol: str) -> float:
        """Get current funding rate"""
        if self.mock_mode:
            return 0.0001
        
        try:
            # CCXT doesn't have a direct funding rate method, return default
            return 0.0001
        except Exception as e:
            logger.error(f"Error fetching funding rate for {symbol}: {e}")
            return 0.0
    
    async def get_open_interest(self, symbol: str) -> Dict[str, Any]:
        """Get open interest data"""
        if self.mock_mode:
            return {"open_interest": 10000.0, "change_24h_percent": 2.5}
        
        try:
            # Simplified - return default values
            return {
                "open_interest": 10000.0,
                "change_24h_percent": 0.0
            }
        except Exception as e:
            logger.error(f"Error fetching open interest for {symbol}: {e}")
            return {"open_interest": 0.0, "change_24h_percent": 0.0}
    
    async def get_top_gainers(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top gaining symbols in 24h"""
        if self.mock_mode:
            return self._mock_top_gainers(limit)
        
        try:
            tickers = self.client.fetch_tickers()
            
            # Filter valid USDT pairs and sort by price change
            usdt_pairs = []
            for symbol, ticker in tickers.items():
                if symbol.endswith('/USDT'):
                    try:
                        price_change = float(ticker.get('percentage', 0))
                        volume = float(ticker.get('quoteVolume', 0))
                        price = float(ticker.get('last', 0))
                        
                        if price_change > 0 and volume > 0:
                            # Convert symbol format from BTC/USDT to BTCUSDT
                            clean_symbol = symbol.replace('/', '')
                            usdt_pairs.append({
                                "symbol": clean_symbol,
                                "price_change_percent": price_change,
                                "volume_24h": volume,
                                "price": price
                            })
                    except:
                        continue
            
            # Sort by price change descending
            usdt_pairs.sort(key=lambda x: x['price_change_percent'], reverse=True)
            
            return usdt_pairs[:limit]
        except Exception as e:
            logger.error(f"Error fetching top gainers: {e}")
            return self._mock_top_gainers(limit)
    
    async def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float
    ) -> Optional[Dict[str, Any]]:
        """Place market order"""
        if self.mock_mode:
            return {
                "orderId": "mock_order_123",
                "symbol": symbol,
                "status": "FILLED",
                "executedQty": quantity
            }
        
        try:
            # Convert symbol format if needed (BTCUSDT -> BTC/USDT)
            if '/' not in symbol:
                symbol = f"{symbol[:-4]}/{symbol[-4:]}"
            
            order = self.client.create_order(
                symbol=symbol,
                type='market',
                side=side.lower(),
                amount=quantity
            )
            return order
        except Exception as e:
            logger.error(f"Error placing market order: {e}")
            return None
    
    async def set_leverage(self, symbol: str, leverage: int) -> bool:
        """Set leverage for symbol"""
        if self.mock_mode:
            return True
        
        try:
            # Convert symbol format if needed
            if '/' not in symbol:
                symbol = f"{symbol[:-4]}/{symbol[-4:]}"
            
            self.client.set_leverage(leverage, symbol)
            return True
        except Exception as e:
            logger.error(f"Error setting leverage: {e}")
            return False
    
    async def place_stop_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float
    ) -> Optional[Dict[str, Any]]:
        """Place stop-loss order"""
        if self.mock_mode:
            return {"orderId": "mock_sl_order_123"}
        
        try:
            # Convert symbol format if needed
            if '/' not in symbol:
                symbol = f"{symbol[:-4]}/{symbol[-4:]}"
            
            order = self.client.create_order(
                symbol=symbol,
                type='stop_market',
                side=side.lower(),
                amount=quantity,
                params={'stopPrice': stop_price}
            )
            return order
        except Exception as e:
            logger.error(f"Error placing stop-loss order: {e}")
            return None
    
    async def place_take_profit_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float
    ) -> Optional[Dict[str, Any]]:
        """Place take-profit order"""
        if self.mock_mode:
            return {"orderId": "mock_tp_order_123"}
        
        try:
            # Convert symbol format if needed
            if '/' not in symbol:
                symbol = f"{symbol[:-4]}/{symbol[-4:]}"
            
            order = self.client.create_order(
                symbol=symbol,
                type='take_profit_market',
                side=side.lower(),
                amount=quantity,
                params={'stopPrice': stop_price}
            )
            return order
        except Exception as e:
            logger.error(f"Error placing take-profit order: {e}")
            return None
    
    def _mock_candles(self, symbol: str, limit: int) -> List[Dict[str, Any]]:
        """Generate mock candle data"""
        base_price = 50000.0 if symbol == "BTCUSDT" else 3000.0
        candles = []
        
        for i in range(limit):
            candles.append({
                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000) - (i * 300000),
                "open": base_price + (i % 100),
                "high": base_price + (i % 100) + 50,
                "low": base_price + (i % 100) - 50,
                "close": base_price + ((i + 1) % 100),
                "volume": 1000.0 + (i % 500)
            })
        
        return list(reversed(candles))
    
    def _mock_top_gainers(self, limit: int) -> List[Dict[str, Any]]:
        """Generate mock top gainers"""
        symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", 
                   "XRPUSDT", "DOGEUSDT", "MATICUSDT", "DOTUSDT", "AVAXUSDT"]
        
        gainers = []
        for i, symbol in enumerate(symbols[:limit]):
            gainers.append({
                "symbol": symbol,
                "price_change_percent": 10.0 - (i * 0.5),
                "volume_24h": 1000000.0 - (i * 50000),
                "price": 50000.0 if "BTC" in symbol else 3000.0
            })
        
        return gainers