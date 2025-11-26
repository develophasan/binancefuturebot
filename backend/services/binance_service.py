import os
import asyncio
from typing import List, Dict, Any, Optional
import aiohttp
import hmac
import hashlib
import logging
import random
from datetime import datetime, timezone
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class BinanceService:
    def __init__(self, testnet: bool = True):
        self.testnet = testnet
        
        # Binance FUTURES endpoints
        if testnet:
            # Futures Testnet
            self.futures_base_url = "https://testnet.binancefuture.com"
            self.api_base_url = "https://testnet.binancefuture.com"
        else:
            # Futures Mainnet
            self.futures_base_url = "https://fapi.binance.com"
            self.api_base_url = "https://fapi.binance.com"
        
        # Get API credentials
        api_key = os.getenv("BINANCE_TESTNET_API_KEY", "") if testnet else os.getenv("BINANCE_API_KEY", "")
        api_secret = os.getenv("BINANCE_TESTNET_SECRET_KEY", "") if testnet else os.getenv("BINANCE_SECRET_KEY", "")
        
        self.api_key = api_key
        self.api_secret = api_secret
        self.has_credentials = bool(api_key and api_secret)
        
        # Setup proxy list
        self.proxy_list = []
        proxy_list_str = os.getenv("PROXY_LIST", "")
        if proxy_list_str:
            for proxy_str in proxy_list_str.split(','):
                parts = proxy_str.strip().split(':')
                if len(parts) == 4:
                    ip, port, username, password = parts
                    proxy_url = f"http://{username}:{password}@{ip}:{port}"
                    self.proxy_list.append(proxy_url)
            logger.info(f"🌐 Loaded {len(self.proxy_list)} proxies for Binance API")
        else:
            logger.warning("⚠️ No proxies configured, direct connection will be attempted")
        
        if self.has_credentials:
            logger.info(f"✅ Binance service initialized with Testnet API credentials")
        else:
            logger.warning("⚠️ No API credentials found, using public data only")
        
        self.mock_mode = False
        self.current_proxy_index = 0
    
    def _get_next_proxy(self) -> Optional[str]:
        """Get next proxy from rotation"""
        if not self.proxy_list:
            return None
        
        # Round-robin proxy selection
        proxy = self.proxy_list[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_list)
        return proxy
    
    async def get_candles(self, symbol: str, interval: str = "5m", limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch OHLCV candles from Binance FUTURES via proxy"""
        url = f"{self.futures_base_url}/fapi/v1/klines"
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        
        proxy = self._get_next_proxy()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, 
                    params=params, 
                    proxy=proxy,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
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
                        logger.info(f"✅ Fetched {len(candles)} FUTURES candles for {symbol}")
                        return candles
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Futures API error {response.status}: {error_text[:100]}")
                        return self._mock_candles(symbol, limit)
        except Exception as e:
            logger.error(f"❌ Error fetching FUTURES candles for {symbol}: {e}")
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
        """Get FUTURES account balance from Binance via proxy"""
        if not self.has_credentials:
            logger.warning("No API credentials, returning simulated balance")
            return {
                "total_equity_usdt": 10000.0,
                "available_balance_usdt": 9500.0,
                "used_margin_usdt": 500.0
            }
        
        url = f"{self.api_base_url}/fapi/v2/account"
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        
        params = {
            "timestamp": timestamp
        }
        
        signature = self._sign_request(params)
        params["signature"] = signature
        
        headers = {
            "X-MBX-APIKEY": self.api_key
        }
        
        proxy = self._get_next_proxy()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, 
                    params=params, 
                    headers=headers,
                    proxy=proxy,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Futures account structure
                        total_wallet = float(data.get('totalWalletBalance', 0))
                        available = float(data.get('availableBalance', 0))
                        
                        logger.info(f"✅ Fetched FUTURES balance: {total_wallet} USDT")
                        
                        return {
                            "total_equity_usdt": total_wallet,
                            "available_balance_usdt": available,
                            "used_margin_usdt": total_wallet - available
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Futures account error {response.status}: {error_text[:100]}")
                        return {
                            "total_equity_usdt": 10000.0,
                            "available_balance_usdt": 9500.0,
                            "used_margin_usdt": 500.0
                        }
        except Exception as e:
            logger.error(f"❌ Error fetching FUTURES balance: {e}")
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
    
    async def get_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current price for a symbol"""
        url = f"{self.futures_base_url}/fapi/v1/ticker/price"
        proxy = self._get_next_proxy()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params={"symbol": symbol},
                    proxy=proxy,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"Failed to get ticker for {symbol}: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error getting ticker for {symbol}: {e}")
            return None
    
    async def get_top_gainers(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top gaining FUTURES symbols in 24h via proxy"""
        url = f"{self.futures_base_url}/fapi/v1/ticker/24hr"
        proxy = self._get_next_proxy()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, 
                    proxy=proxy,
                    timeout=aiohttp.ClientTimeout(total=20)
                ) as response:
                    if response.status == 200:
                        tickers = await response.json()
                        
                        # Filter valid USDT perpetual contracts and sort by price change
                        usdt_pairs = []
                        for ticker in tickers:
                            symbol = ticker.get('symbol', '')
                            # Only perpetual USDT contracts
                            if symbol.endswith('USDT'):
                                try:
                                    price_change = float(ticker.get('priceChangePercent', 0))
                                    volume = float(ticker.get('quoteVolume', 0))
                                    price = float(ticker.get('lastPrice', 0))
                                    
                                    # Higher volume filter for futures (more liquid)
                                    if price_change > 0 and volume > 1000000:
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
                        
                        logger.info(f"✅ Fetched {len(usdt_pairs)} FUTURES top gainers (24h)")
                        return usdt_pairs[:limit]
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Futures 24hr ticker error {response.status}: {error_text[:100]}")
                        return self._mock_top_gainers(limit)
        except Exception as e:
            logger.error(f"❌ Error fetching FUTURES top gainers: {e}")
            return self._mock_top_gainers(limit)
    
    async def set_leverage(self, symbol: str, leverage: int) -> bool:
        """Set leverage for FUTURES symbol"""
        if not self.has_credentials:
            logger.info(f"SIMULATED LEVERAGE: {symbol} -> {leverage}x")
            return True
        
        url = f"{self.api_base_url}/fapi/v1/leverage"
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        
        params = {
            "symbol": symbol,
            "leverage": leverage,
            "timestamp": timestamp
        }
        
        signature = self._sign_request(params)
        params["signature"] = signature
        
        headers = {
            "X-MBX-APIKEY": self.api_key
        }
        
        proxy = self._get_next_proxy()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    data=params,
                    headers=headers,
                    proxy=proxy,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        logger.info(f"✅ Set FUTURES leverage: {symbol} -> {leverage}x")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Leverage error: {error_text[:100]}")
                        return False
        except Exception as e:
            logger.error(f"❌ Error setting leverage: {e}")
            return False
    
    async def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float
    ) -> Optional[Dict[str, Any]]:
        """Place FUTURES market order"""
        if not self.has_credentials:
            logger.info(f"SIMULATED FUTURES ORDER: {side} {quantity} {symbol}")
            return {
                "orderId": f"sim_order_{int(datetime.now(timezone.utc).timestamp())}",
                "symbol": symbol,
                "status": "FILLED",
                "executedQty": quantity,
                "side": side
            }
        
        url = f"{self.api_base_url}/fapi/v1/order"
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        
        params = {
            "symbol": symbol,
            "side": side,
            "type": "MARKET",
            "quantity": quantity,
            "timestamp": timestamp
        }
        
        signature = self._sign_request(params)
        params["signature"] = signature
        
        headers = {
            "X-MBX-APIKEY": self.api_key
        }
        
        proxy = self._get_next_proxy()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    data=params,
                    headers=headers,
                    proxy=proxy,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"✅ FUTURES order placed: {side} {quantity} {symbol}")
                        return data
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Order error: {error_text[:100]}")
                        return None
        except Exception as e:
            logger.error(f"❌ Error placing order: {e}")
            return None
    
    async def place_stop_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float
    ) -> Optional[Dict[str, Any]]:
        """Place FUTURES stop-loss order"""
        if not self.has_credentials:
            logger.info(f"SIMULATED SL: {side} {quantity} {symbol} @ {stop_price}")
            return {"orderId": f"sim_sl_{int(datetime.now(timezone.utc).timestamp())}"}
        
        url = f"{self.api_base_url}/fapi/v1/order"
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        
        params = {
            "symbol": symbol,
            "side": side,
            "type": "STOP_MARKET",
            "quantity": quantity,
            "stopPrice": stop_price,
            "timestamp": timestamp
        }
        
        signature = self._sign_request(params)
        params["signature"] = signature
        
        headers = {
            "X-MBX-APIKEY": self.api_key
        }
        
        proxy = self._get_next_proxy()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    data=params,
                    headers=headers,
                    proxy=proxy,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"✅ FUTURES SL placed: {symbol} @ {stop_price}")
                        return data
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ SL order error: {error_text[:100]}")
                        return None
        except Exception as e:
            logger.error(f"❌ Error placing SL: {e}")
            return None
    
    async def place_take_profit_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float
    ) -> Optional[Dict[str, Any]]:
        """Place FUTURES take-profit order"""
        if not self.has_credentials:
            logger.info(f"SIMULATED TP: {side} {quantity} {symbol} @ {stop_price}")
            return {"orderId": f"sim_tp_{int(datetime.now(timezone.utc).timestamp())}"}
        
        url = f"{self.api_base_url}/fapi/v1/order"
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        
        params = {
            "symbol": symbol,
            "side": side,
            "type": "TAKE_PROFIT_MARKET",
            "quantity": quantity,
            "stopPrice": stop_price,
            "timestamp": timestamp
        }
        
        signature = self._sign_request(params)
        params["signature"] = signature
        
        headers = {
            "X-MBX-APIKEY": self.api_key
        }
        
        proxy = self._get_next_proxy()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    data=params,
                    headers=headers,
                    proxy=proxy,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"✅ FUTURES TP placed: {symbol} @ {stop_price}")
                        return data
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ TP order error: {error_text[:100]}")
                        return None
        except Exception as e:
            logger.error(f"❌ Error placing TP: {e}")
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