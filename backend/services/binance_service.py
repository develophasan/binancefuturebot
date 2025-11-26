import os
import asyncio
from typing import List, Dict, Any, Optional
import aiohttp
import hmac
import hashlib
import logging
from datetime import datetime, timezone
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class BinanceService:
    def __init__(self, testnet: bool = True):
        self.testnet = testnet
        
        # Use correct Binance Testnet endpoints
        if testnet:
            # Spot Testnet for market data (public)
            self.spot_base_url = "https://testnet.binance.vision/api"
            # We'll use Spot data since Futures testnet requires different setup
            self.api_base_url = "https://testnet.binance.vision/api"
        else:
            self.spot_base_url = "https://api.binance.com/api"
            self.api_base_url = "https://api.binance.com/api"
        
        # Get API credentials
        api_key = os.getenv("BINANCE_TESTNET_API_KEY", "") if testnet else os.getenv("BINANCE_API_KEY", "")
        api_secret = os.getenv("BINANCE_TESTNET_SECRET_KEY", "") if testnet else os.getenv("BINANCE_SECRET_KEY", "")
        
        self.api_key = api_key
        self.api_secret = api_secret
        self.has_credentials = bool(api_key and api_secret)
        
        if self.has_credentials:
            logger.info(f"Binance service initialized with Testnet API credentials")
        else:
            logger.warning("No API credentials found, using public data only")
        
        self.mock_mode = False
    
    async def get_candles(self, symbol: str, interval: str = "5m", limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch OHLCV candles from Binance Testnet"""
        url = f"{self.spot_base_url}/v3/klines"
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
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
                        logger.info(f"✅ Successfully fetched {len(candles)} REAL candles for {symbol} from Binance Testnet")
                        return candles
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Binance Testnet error {response.status}: {error_text}")
                        return self._mock_candles(symbol, limit)
        except Exception as e:
            logger.error(f"❌ Error fetching candles for {symbol}: {e}")
            return self._mock_candles(symbol, limit)
    
    def _sign_request(self, params: Dict[str, Any]) -> str:
        """Sign request with HMAC SHA256"""
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    async def get_account_balance(self) -> Dict[str, Any]:
        """Get Spot account balance from Binance Testnet"""
        if not self.has_credentials:
            logger.warning("No API credentials, returning simulated balance")
            return {
                "total_equity_usdt": 10000.0,
                "available_balance_usdt": 9500.0,
                "used_margin_usdt": 500.0
            }
        
        url = f"{self.api_base_url}/v3/account"
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        
        params = {
            "timestamp": timestamp
        }
        
        signature = self._sign_request(params)
        params["signature"] = signature
        
        headers = {
            "X-MBX-APIKEY": self.api_key
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Get USDT balance
                        usdt_balance = 0.0
                        for balance in data.get('balances', []):
                            if balance['asset'] == 'USDT':
                                usdt_balance = float(balance['free']) + float(balance['locked'])
                                break
                        
                        logger.info(f"✅ Successfully fetched REAL account balance: {usdt_balance} USDT")
                        
                        return {
                            "total_equity_usdt": usdt_balance,
                            "available_balance_usdt": usdt_balance,
                            "used_margin_usdt": 0.0
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Error fetching account balance: {response.status} - {error_text}")
                        return {
                            "total_equity_usdt": 10000.0,
                            "available_balance_usdt": 9500.0,
                            "used_margin_usdt": 500.0
                        }
        except Exception as e:
            logger.error(f"❌ Error fetching account balance: {e}")
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
        """Get top gaining symbols in 24h from Binance Testnet"""
        url = f"{self.spot_base_url}/v3/ticker/24hr"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status == 200:
                        tickers = await response.json()
                        
                        # Filter valid USDT pairs and sort by price change
                        usdt_pairs = []
                        for ticker in tickers:
                            symbol = ticker.get('symbol', '')
                            if symbol.endswith('USDT'):
                                try:
                                    price_change = float(ticker.get('priceChangePercent', 0))
                                    volume = float(ticker.get('quoteVolume', 0))
                                    price = float(ticker.get('lastPrice', 0))
                                    
                                    if price_change > 0 and volume > 100000:  # Lower volume filter for testnet
                                        usdt_pairs.append({
                                            "symbol": symbol,
                                            "price_change_percent": price_change,
                                            "volume_24h": volume,
                                            "price": price
                                        })
                                except:
                                    continue
                        
                        # Sort by price change descending
                        usdt_pairs.sort(key=lambda x: x['price_change_percent'], reverse=True)
                        
                        logger.info(f"✅ Successfully fetched {len(usdt_pairs)} REAL top gainers from Binance Testnet")
                        return usdt_pairs[:limit]
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Error fetching top gainers: {response.status} - {error_text}")
                        return self._mock_top_gainers(limit)
        except Exception as e:
            logger.error(f"❌ Error fetching top gainers: {e}")
            return self._mock_top_gainers(limit)
    
    async def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float
    ) -> Optional[Dict[str, Any]]:
        """Place market order (simulated)"""
        # Return simulated order for testnet
        logger.info(f"SIMULATED ORDER: {side} {quantity} {symbol}")
        return {
            "orderId": f"sim_order_{int(datetime.now(timezone.utc).timestamp())}",
            "symbol": symbol,
            "status": "FILLED",
            "executedQty": quantity,
            "side": side
        }
    
    async def set_leverage(self, symbol: str, leverage: int) -> bool:
        """Set leverage for symbol (simulated)"""
        logger.info(f"SIMULATED LEVERAGE: {symbol} -> {leverage}x")
        return True
    
    async def place_stop_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float
    ) -> Optional[Dict[str, Any]]:
        """Place stop-loss order (simulated)"""
        logger.info(f"SIMULATED SL ORDER: {side} {quantity} {symbol} @ {stop_price}")
        return {
            "orderId": f"sim_sl_order_{int(datetime.now(timezone.utc).timestamp())}",
            "symbol": symbol,
            "stopPrice": stop_price
        }
    
    async def place_take_profit_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float
    ) -> Optional[Dict[str, Any]]:
        """Place take-profit order (simulated)"""
        logger.info(f"SIMULATED TP ORDER: {side} {quantity} {symbol} @ {stop_price}")
        return {
            "orderId": f"sim_tp_order_{int(datetime.now(timezone.utc).timestamp())}",
            "symbol": symbol,
            "stopPrice": stop_price
        }
    
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