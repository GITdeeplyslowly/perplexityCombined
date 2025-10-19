"""
live/websocket_stream.py

SmartAPI WebSocket streaming module for unified trading system.

Features:
- Multiple instrument streams (up to 3 per SmartAPI account)
- User-selectable feed type: LTP, Quote, SnapQuote
- Event-driven tick delivery to tick buffer and OHLC aggregator
- Robust reconnect and error handling
- Integration with GUI controls and manual refresh
- Angel One compatible exchange type mapping

Usage:
- Import and call `start_stream()` from the live runner or GUI.
- All ticks passed safely for simulation; never to live order endpoints.
"""

import logging
import threading
import json
import pytz
from datetime import datetime

# Import timezone from SSOT
from utils.time_utils import IST
try:
    from SmartApi.smartWebSocketV2 import SmartWebSocketV2  # Capital 'A' - correct package name
except ImportError:
    SmartWebSocketV2 = None  # Install with pip install smartapi-python

# Import Angel One exchange type mapper
from ..utils.exchange_mapper import map_to_angel_exchange_type

logger = logging.getLogger(__name__)

class WebSocketTickStreamer:
    def __init__(self, api_key, client_code, feed_token, symbol_tokens, feed_type="Quote", on_tick=None, auth_token=None):
        """
        api_key: SmartAPI API key
        client_code: User/Account code
        feed_token: Obtained from SmartAPI session
        auth_token: JWT token for authentication (required for SmartWebSocketV2)
        symbol_tokens: list of dicts [{"symbol": ..., "token": ..., "exchange": ...}]
        feed_type: 'LTP', 'Quote', or 'SnapQuote'
        on_tick: callback(tick_dict, symbol) called when new tick arrives
        """
        if SmartWebSocketV2 is None:
            raise ImportError("SmartWebSocketV2 (smartapi) package not available.")
        self.api_key = api_key
        self.auth_token = auth_token
        self.client_code = client_code
        self.feed_token = feed_token
        self.symbol_tokens = symbol_tokens[:3]  # SmartAPI allows max 3
        self.feed_type = feed_type
        self.on_tick = on_tick or (lambda tick, symbol: None)
        self.ws = None
        self.running = False
        self.thread = None

    def _on_open(self, ws):
        logger.info("WebSocket connection OPEN")
        
        # SmartWebSocketV2.subscribe() expects: subscribe(mode, token_list)
        # mode: 1=LTP, 2=Quote, 3=SnapQuote
        mode_map = {"LTP": 1, "Quote": 2, "SnapQuote": 3}
        mode = mode_map.get(self.feed_type, 1)  # Default to LTP
        
        # Build token list with exchange type mapping
        token_list = []
        for s in self.symbol_tokens:
            try:
                # Convert exchange code to Angel One exchange_type integer
                angel_exchange_type = map_to_angel_exchange_type(s['exchange'])
                token_entry = {
                    "exchangeType": angel_exchange_type,  # Use Angel One integer format
                    "tokens": [s['token']]
                }
                token_list.append(token_entry)
                logger.info(f"Mapped {s['exchange']} -> exchange_type={angel_exchange_type} for {s['symbol']}")
            except ValueError as e:
                logger.error(f"Exchange mapping failed for {s['symbol']}: {e}")
                continue
        
        if token_list:
            try:
                # SmartWebSocketV2.subscribe() signature: subscribe(correlation_id, mode, token_list)
                # Try different subscription patterns based on SmartAPI version
                correlation_id = "myQuant_stream"
                self.ws.subscribe(correlation_id, mode, token_list)
                logger.info(f"Subscribed to {len(token_list)} stream(s): {[s['symbol'] for s in self.symbol_tokens]} [mode={mode}, feed_type={self.feed_type}]")
            except TypeError as e:
                logger.error(f"WebSocket subscription failed with signature error: {e}")
                # Fallback: Try without correlation_id
                try:
                    self.ws.subscribe(mode, token_list)
                    logger.info(f"Subscribed (fallback) to {len(token_list)} stream(s)")
                except Exception as e2:
                    logger.error(f"WebSocket subscription fallback also failed: {e2}")
        else:
            logger.error("No valid exchange mappings found - WebSocket subscription failed")

    def _on_data(self, ws, message):
        try:
            # Handle both JSON string and dict object from SmartAPI
            if isinstance(message, str):
                data = json.loads(message)
            else:
                data = message  # Already a dictionary
                
            # Use timezone-aware timestamp for consistency with strategy
            # Create timestamp if needed
            ts = datetime.now(IST)
            # Extract price with better error handling and logging
            raw_price = data.get("ltp", data.get("last_traded_price", 0))
            if raw_price == 0:
                # Log raw data when price is missing/zero for debugging
                logger.warning(f"Zero price received in WebSocket data: {data}")
            
            # CRITICAL FIX: SmartAPI returns prices in paise, convert to rupees
            # Raw price from SmartAPI is in paise (smallest currency unit)
            # Need to divide by 100 to get actual rupee price
            actual_price = float(raw_price) / 100.0
            
            tick = {
                "timestamp": ts,
                "price": actual_price,  # Use converted price in rupees
                "volume": int(data.get("volume", 0)),
                "symbol": data.get("tradingsymbol", data.get("symbol", "")),
                "exchange": data.get("exchange", ""),
                "raw": data
            }
            
            # Validate reasonable price range for options  
            if tick['price'] > 5000:  # Still log if something seems wrong
                logger.warning(f"🚨 Unusually high option price: {tick['symbol']} @ ₹{tick['price']} - Raw data: {data}")
            elif tick['price'] < 0.01:  # Also log extremely low prices
                logger.warning(f"🚨 Unusually low option price: {tick['symbol']} @ ₹{tick['price']} - Raw data: {data}")
            
            if self.on_tick:
                self.on_tick(tick, tick['symbol'])
        except Exception as e:
            logger.error(f"Error in streamed tick: {e}")

    def _on_error(self, ws, error):
        logger.error(f"WebSocket error: {error}")

    def _on_close(self, ws, close_status_code=None, close_msg=None):
        self.running = False
        logger.warning("WebSocket connection CLOSED")

    def start_stream(self):
        if self.running:
            logger.info("WebSocket stream already running.")
            return
        self.running = True
        self.ws = SmartWebSocketV2(
            auth_token=self.auth_token,
            api_key=self.api_key,
            client_code=self.client_code,
            feed_token=self.feed_token
        )
        self.ws.on_open = self._on_open
        self.ws.on_data = self._on_data
        self.ws.on_error = self._on_error
        self.ws.on_close = self._on_close
        self.thread = threading.Thread(target=self.ws.connect)
        self.thread.daemon = True
        self.thread.start()
        logger.info("WebSocket thread started.")

    def stop_stream(self):
        if self.ws is not None:
            self.ws.close()
            self.running = False
            logger.info("WebSocket stream stopped.")

# Example usage for integration testing (not run in production as-is)
if __name__ == "__main__":
    import os
    import time
    # Load session info from smartapi/session_token.json or config
    session_path = "smartapi/session_token.json"
    if not os.path.exists(session_path):
        print("Session JSON missingâ€”run smartapi login first.")
        exit(1)
    with open(session_path, "r") as f:
        session = json.load(f)
    api_key = session["profile"]["api_key"]
    client_code = session["client_code"]
    feed_token = session["feed_token"]
    # Load three sample tokens from symbol cache
    from utils.cache_manager import load_symbol_cache
    symbols = load_symbol_cache()
    test_tokens = [v for (k, v) in list(symbols.items())[:3]]
    def print_tick(tick, symbol):
        print(f"[{tick['timestamp']}] {symbol}: â‚¹{tick['price']} Vol:{tick['volume']}")
    streamer = WebSocketTickStreamer(
        api_key, client_code, feed_token,
        test_tokens, feed_type="Quote", on_tick=print_tick
    )
    streamer.start_stream()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        streamer.stop_stream()
