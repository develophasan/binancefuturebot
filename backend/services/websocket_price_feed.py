import asyncio
import json
import logging
from typing import Dict, Set, Callable
import websockets
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class BinanceWebSocketPriceFeed:
    """Real-time price feed using Binance WebSocket streams"""
    
    def __init__(self, testnet: bool = True):
        self.testnet = testnet
        if testnet:
            self.ws_base_url = "wss://stream.binancefuture.com"
        else:
            self.ws_base_url = "wss://fstream.binance.com"
        
        self.prices: Dict[str, float] = {}  # symbol -> current price
        self.subscribed_symbols: Set[str] = set()
        self.websocket = None
        self.is_running = False
        self.price_callbacks: list[Callable] = []
        
    def subscribe_symbol(self, symbol: str):
        """Subscribe to a symbol's price updates"""
        symbol_lower = symbol.lower()
        if symbol_lower not in self.subscribed_symbols:
            self.subscribed_symbols.add(symbol_lower)
            logger.info(f"📡 Subscribed to {symbol} price stream")
    
    def unsubscribe_symbol(self, symbol: str):
        """Unsubscribe from a symbol's price updates"""
        symbol_lower = symbol.lower()
        if symbol_lower in self.subscribed_symbols:
            self.subscribed_symbols.discard(symbol_lower)
            logger.info(f"🔇 Unsubscribed from {symbol} price stream")
    
    def get_price(self, symbol: str) -> float:
        """Get current price for a symbol"""
        return self.prices.get(symbol.upper(), 0.0)
    
    def add_price_callback(self, callback: Callable):
        """Add callback to be called on every price update"""
        self.price_callbacks.append(callback)
    
    async def start(self):
        """Start WebSocket connection and price streaming"""
        if self.is_running:
            logger.warning("WebSocket already running")
            return
        
        self.is_running = True
        logger.info("🚀 Starting Binance WebSocket price feed...")
        
        asyncio.create_task(self._connect_and_stream())
    
    async def stop(self):
        """Stop WebSocket connection"""
        self.is_running = False
        if self.websocket:
            await self.websocket.close()
        logger.info("🛑 WebSocket price feed stopped")
    
    async def _connect_and_stream(self):
        """Main WebSocket connection loop with auto-reconnect"""
        while self.is_running:
            try:
                await self._stream_prices()
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                if self.is_running:
                    logger.info("🔄 Reconnecting in 2 seconds...")
                    await asyncio.sleep(2)
    
    async def _stream_prices(self):
        """Connect to WebSocket and stream prices"""
        if not self.subscribed_symbols:
            logger.warning("No symbols subscribed, waiting...")
            await asyncio.sleep(3)
            return
        
        # Create stream URL for all subscribed symbols
        # Use miniTicker for real-time price (updates every second)
        streams = [f"{symbol}@miniTicker" for symbol in self.subscribed_symbols]
        stream_url = f"{self.ws_base_url}/stream?streams={'/'.join(streams)}"
        
        logger.info(f"📡 Connecting to WebSocket: {len(self.subscribed_symbols)} symbols: {list(self.subscribed_symbols)}")
        
        try:
            async with websockets.connect(stream_url, ping_interval=20) as websocket:
                self.websocket = websocket
                logger.info("✅ WebSocket connected! Streaming real-time prices...")
                
                async for message in websocket:
                    if not self.is_running:
                        break
                    
                    try:
                        data = json.loads(message)
                        
                        # Handle stream data
                        if 'data' in data:
                            ticker_data = data['data']
                            symbol = ticker_data.get('s')  # Symbol (e.g., BTCUSDT)
                            price = float(ticker_data.get('c', 0))  # Close price
                            
                            if symbol and price > 0:
                                old_price = self.prices.get(symbol)
                                self.prices[symbol] = price
                                
                                # Log only if price changed
                                if old_price != price:
                                    logger.debug(f"💰 {symbol}: ${price:.8f}")
                                    
                                    # Call callbacks
                                    for callback in self.price_callbacks:
                                        try:
                                            callback(symbol, price)
                                        except Exception as e:
                                            logger.error(f"Error in price callback: {e}")
                    
                    except json.JSONDecodeError:
                        logger.warning("Failed to decode WebSocket message")
                    except Exception as e:
                        logger.error(f"Error processing WebSocket message: {e}")
        
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed")
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
        finally:
            self.websocket = None


# Global singleton instance
_price_feed_instance = None


def get_price_feed(testnet: bool = True) -> BinanceWebSocketPriceFeed:
    """Get or create global price feed instance"""
    global _price_feed_instance
    if _price_feed_instance is None:
        _price_feed_instance = BinanceWebSocketPriceFeed(testnet=testnet)
    return _price_feed_instance
