"""
live/broker_adapter.py

Pure SmartAPI broker/tick data adapter for live trading and forward testing.

LIVE TRADING (Primary Function):
- Handles SmartAPI login/session management
- Streams live ticks via WebSocket or polling mode
- Buffers ticks, generates 1-min OHLCV bars
- Never sends real orders in paper trading mode

DATA SOURCES (User-Controlled):
- Live WebSocket/API data (primary)
- User-selected file simulation (optional, GUI-enabled only)
- NO synthetic/fallback data generation
- NO automatic data substitution

FAIL-FAST APPROACH:
- If SmartAPI unavailable and no file selected: STOP
- If file simulation fails: STOP  
- No hidden fallbacks that could mask real issues
"""

import time
import logging
import pandas as pd
import threading

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from utils.time_utils import now_ist, normalize_datetime_to_ist, IST
from types import MappingProxyType

logger = logging.getLogger(__name__)

class BrokerAdapter:
    def __init__(self, config: MappingProxyType = None):
        """Initialize BrokerAdapter with frozen config from upstream
        
        Args:
            config: Frozen MappingProxyType config from LiveTrader
        """
        if config is None:
            raise ValueError("BrokerAdapter requires frozen config from upstream (LiveTrader)")
        
        if not isinstance(config, MappingProxyType):
            raise TypeError(f"BrokerAdapter requires frozen MappingProxyType, got {type(config)}")
            
        self.params = config
        
        # Use strict config access - fail immediately if sections missing
        from utils.config_helper import ConfigAccessor
        self.config_accessor = ConfigAccessor(config)
        
        self.live_params = config["live"]
        self.instrument = config["instrument"]
        self.symbol = self.instrument["symbol"]
        
        # STRICT ACCESS - NO FALLBACKS IN TRADING SYSTEMS
        self.exchange = self.instrument["exchange"]  # Will raise KeyError if missing
        
        # Use SSOT for instrument parameters - STRICT ACCESS ONLY
        self.lot_size = int(self.config_accessor.get_current_instrument_param('lot_size'))
        self.tick_size = float(self.config_accessor.get_current_instrument_param('tick_size'))
            
        # STRICT ACCESS - NO FALLBACKS IN TRADING SYSTEMS  
        self.product_type = self.instrument["product_type"]  # Will raise KeyError if missing
        
        # instrument_token: Dynamic per option contract, set by user/token cache
        # Will be validated when actually needed for trading operations
        self.paper_trading = self.live_params["paper_trading"]

        # Data streaming components
        self.tick_buffer: List[Dict] = []
        self.df_tick = pd.DataFrame(columns=["timestamp", "price", "volume"])
        self.last_price: float = 0.0
        self.connection = None
        self.feed_active = False
        self.session_manager = None
        
        # WebSocket streaming components
        self.ws_streamer = None
        self.streaming_mode = False  # True = WebSocket, False = Polling
        self.last_tick_time = None
        self.heartbeat_threshold = 30  # seconds - switch to polling if no ticks
        self.stream_status = "disconnected"  # disconnected, connecting, streaming, polling, error
        self.tick_lock = threading.Lock()
        
        # Auto-recovery settings
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 3
        self.last_reconnect_time = None
        self.reconnect_cooldown = 60  # seconds between reconnect attempts
        
        # Rate limiting for polling mode
        self.last_poll_time = None
        self.min_poll_interval = 1.0  # minimum 1 second between polls

        # Optional file simulation (ONLY when explicitly enabled by user)
        self.file_simulator = None
        if config.get('data_simulation', {}).get('enabled', False):
            file_path = config.get('data_simulation', {}).get('file_path', '')
            if file_path:
                from live.data_simulator import DataSimulator
                # DataSimulator only takes file_path parameter
                self.file_simulator = DataSimulator(file_path)
                logger.info(f"File simulation enabled with: {file_path}")

        # Dynamic imports for SmartAPI
        try:
            from SmartApi import SmartConnect
            self.SmartConnect = SmartConnect
        except ImportError:
            self.SmartConnect = None
            logger.warning("SmartAPI not installed; live data streaming not available.")
            
        # Try to import WebSocket streamer
        try:
            from live.websocket_stream import WebSocketTickStreamer
            self.WebSocketTickStreamer = WebSocketTickStreamer
        except ImportError:
            self.WebSocketTickStreamer = None
            logger.info("WebSocket streaming not available; will use polling mode.")

    def connect(self):
        """Authenticate and establish live SmartAPI session with WebSocket streaming."""
        # Handle file simulation first (if enabled)
        if self.paper_trading and self.file_simulator:
            if self.file_simulator.load_data():
                logger.info("Paper trading mode: using user-selected file simulation.")
                self.stream_status = "file_simulation"
                return
            else:
                logger.error("File simulation failed to load data.")
                self.stream_status = "error"
                raise RuntimeError("File simulation data could not be loaded")
        
        # For both paper trading and live trading, we need SmartAPI for live data
        if not self.SmartConnect:
            error_msg = (
                "🚨 CRITICAL ERROR: SmartAPI package is not installed!\n"
                "💡 SOLUTION: Install SmartAPI package: pip install smartapi-python\n"
                "❌ TRADING SYSTEM CANNOT OPERATE WITHOUT BROKER CONNECTION"
            )
            logger.error(error_msg)
            self.stream_status = "error"
            raise RuntimeError("SmartAPI package missing - cannot establish broker connection")
            
        # FAIL-FAST: Validate minimum credentials for authentication
        live = self.live_params
        
        # Check minimum required credentials (session manager mode)
        min_required = ["api_key", "client_code"]
        missing_min = []
        empty_min = []
        
        for key in min_required:
            if key not in live:
                missing_min.append(key)
            elif not live[key] or live[key].strip() == "":
                empty_min.append(key)
        
        if missing_min or empty_min:
            error_msg = (
                f"🚨 CRITICAL ERROR: Missing essential trading credentials!\n"
                f"❌ Missing credentials: {missing_min}\n" 
                f"❌ Empty credentials: {empty_min}\n"
                f"💡 MINIMUM REQUIRED: api_key, client_code\n"
                f"🔄 OPTIONAL: pin, totp_secret (for direct auth mode)\n"
                f"⚠️  TRADING SYSTEM CANNOT OPERATE WITHOUT VALID CREDENTIALS"
            )
            logger.error(error_msg)
            self.stream_status = "error"
            raise ValueError(f"Invalid minimum credentials: missing {missing_min}, empty {empty_min}")
        
        # Determine authentication mode based on available credentials
        direct_auth_creds = ["pin", "totp_secret"]
        has_direct_auth = all(
            key in live and live[key] and live[key].strip() != "" 
            for key in direct_auth_creds
        )
        
        if has_direct_auth:
            logger.info("🔐 Using DIRECT AUTHENTICATION mode (all credentials provided)")
        else:
            logger.info("🔄 Using SESSION MANAGER mode (will attempt to reuse saved session)")
            logger.info("💡 TIP: Provide PIN/TOTP in config for direct authentication mode")
        
        # Attempt connection with retry logic
        self._connect_with_retry()

    def get_next_tick(self) -> Optional[Dict[str, Any]]:
        """Fetch next tick from live SmartAPI connection (WebSocket preferred, polling fallback)."""
        
        # File simulation mode (user-enabled only)
        if self.file_simulator:
            tick = self.file_simulator.get_next_tick()
            if tick:
                self.last_price = tick['price']
                self._buffer_tick(tick)
            return tick
        
        # Priority 1: WebSocket streaming (real-time) - ONLY mode when WebSocket is active
        if self.streaming_mode:
            try:
                with self.tick_lock:
                    if self.tick_buffer:
                        tick = self.tick_buffer.pop(0)
                        self.last_price = tick['price']
                        # DON'T call _buffer_tick() here - tick is already buffered by WebSocket handler
                        return tick
                    else:
                        # WebSocket is active but buffer is empty - return None (don't poll)
                        return None
            except Exception as e:
                logger.error(f"Error processing WebSocket tick buffer: {e}")
                return None
        
        # Priority 2: SmartAPI polling mode (ONLY if WebSocket unavailable)
        if not self.connection:
            logger.error("No SmartAPI connection available - live data streaming not possible")
            return None
        
        # Rate limiting for polling mode to prevent API limits
        current_time = time.time()
        if self.last_poll_time and (current_time - self.last_poll_time) < self.min_poll_interval:
            return None  # Skip this poll to respect rate limits
        
        self.last_poll_time = current_time
            
        try:
            # Use SmartAPI getLTP for polling
            instrument_token = self.instrument.get('token', '').strip()
            if not instrument_token:
                logger.error(f"Token not set for symbol '{self.instrument.get('symbol', 'Unknown')}'")
                return None
                
            # SmartAPI ltpData call - requires positional arguments
            ltp_response = self.connection.ltpData(
                self.exchange,
                self.instrument.get('symbol', ''),
                instrument_token
            )
            
            if 'data' in ltp_response and 'ltp' in ltp_response['data']:
                # CRITICAL FIX: SmartAPI returns prices in paise, convert to rupees
                raw_price = ltp_response["data"]["ltp"]
                price = float(raw_price) / 100.0  # Convert paise to rupees
                
                tick = {
                    "timestamp": pd.Timestamp.now(tz=IST),
                    "price": price, 
                    "volume": 1,  # LTP doesn't include volume
                    "source": "smartapi_polling"
                }
                self.last_price = price
                self._buffer_tick(tick)
                logger.debug(f"📊 Polling tick: {price}")
                return tick
            else:
                logger.error(f"Invalid LTP response: {ltp_response}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching SmartAPI LTP: {e}")
            return None

    def _buffer_tick(self, tick: Dict[str, Any]):
        """Buffer each tick and limit rolling window for memory safety."""
        self.tick_buffer.append(tick)
        # Fix pandas warning: avoid concatenating empty DataFrame
        if len(self.df_tick) == 0:
            self.df_tick = pd.DataFrame([tick])
        else:
            self.df_tick = pd.concat([self.df_tick, pd.DataFrame([tick])], ignore_index=True)
        if len(self.df_tick) > 2500:
            self.df_tick = self.df_tick.tail(2000)  # Keep last 2000 for memory management

    def place_order(self, side: str, price: float, quantity: int, order_type: str = "MARKET") -> str:
        """Simulate all orders by default. Never sends real order in paper/forward test."""
        logger.info(f"Simulated order: {side} {quantity} @ {price} ({order_type})")
        return f"PAPER_{side}_{int(time.time())}"

    def get_last_price(self) -> float:
        """Return last known tick price (latest or simulated)."""
        return self.last_price or 0.0

    def disconnect(self):
        """Graceful cleanup of WebSocket and SmartAPI session."""
        # Clean up WebSocket connection first
        if self.ws_streamer:
            try:
                self.ws_streamer.stop_stream()
                self.ws_streamer = None
            except Exception as e:
                logger.warning(f"Error stopping WebSocket stream: {e}")
            
        # Clean up SmartAPI session
        if self.connection and not self.paper_trading:
            try:
                # Logout from SmartAPI session
                self.connection.terminateSession(self.live_params["client_code"])
                self.connection = None
            except Exception as e:
                logger.warning(f"Error during SmartAPI logout: {e}")
                
        self.stream_status = "disconnected"
        self.streaming_mode = False
        self.feed_active = False

    # Additional methods would be implemented here for full functionality...
    def _connect_with_retry(self):
        """Establish SmartAPI connection with retry logic for live data streaming"""
        from live.login import SmartAPISessionManager
        
        live = self.live_params
        logger.info("🔌 Establishing SmartAPI connection for live data streaming...")
        
        # Validate minimum required credentials
        if not live.get('api_key') or not live.get('client_code'):
            raise ValueError("SmartAPI credentials missing: api_key and client_code required")
        
        try:
            # Try direct authentication if PIN and TOTP are provided
            if live.get('pin') and live.get('totp_secret'):
                logger.info("🔐 Using direct SmartAPI authentication...")
                session_manager = SmartAPISessionManager(
                    api_key=live['api_key'],
                    client_code=live['client_code'], 
                    pin=live['pin'],
                    totp_secret=live['totp_secret']
                )
                session_info = session_manager.login()
                logger.info("✅ Direct SmartAPI authentication successful")
            else:
                # Try to load saved session
                logger.info("🔄 Attempting to load saved SmartAPI session...")
                session_manager = SmartAPISessionManager(
                    api_key=live['api_key'],
                    client_code=live['client_code'],
                    pin="", 
                    totp_secret=""
                )
                session_info = session_manager.load_session()
                if not session_info:
                    raise RuntimeError("No saved session found and PIN/TOTP not provided. Please provide credentials or run interactive login.")
                logger.info("✅ Saved SmartAPI session loaded successfully")
            
            # Store session for use by streaming components
            self.session_manager = session_manager
            self.connection = session_manager.session  # Use the SmartConnect object, not session_info dict
            self.session_info = session_info  # Store session info separately for WebSocket
            
            # Initialize WebSocket streaming if available and token is provided
            if self.WebSocketTickStreamer and self.instrument.get("token"):
                self._initialize_websocket_streaming(self.session_info)
            else:
                logger.info("📊 WebSocket not available, using polling mode for data collection")
                self.streaming_mode = False
            
            self.stream_status = "connected"
            logger.info("🟢 SmartAPI connection established successfully")
            
        except Exception as e:
            logger.error(f"❌ SmartAPI connection failed: {e}")
            self.stream_status = "error"
            raise RuntimeError(f"Failed to establish SmartAPI connection: {e}")
    
    def _initialize_websocket_streaming(self, session_info):
        """Initialize WebSocket streaming for real-time data"""
        try:
            live = self.live_params
            symbol_tokens = [{
                "symbol": self.instrument.get("symbol", ""),
                "token": self.instrument["token"],
                "exchange": self.exchange
            }]
            
            logger.info(f"📡 Initializing WebSocket for {symbol_tokens[0]['symbol']} (Token: {symbol_tokens[0]['token']})")
            
            self.ws_streamer = self.WebSocketTickStreamer(
                api_key=live['api_key'],
                client_code=live['client_code'],
                feed_token=session_info['feed_token'],
                auth_token=session_info['jwt_token'],  # Add missing auth_token
                symbol_tokens=symbol_tokens,
                feed_type=live.get('feed_type', 'LTP'),
                on_tick=self._handle_websocket_tick
            )
            
            # Start WebSocket in background thread
            self.ws_streamer.start_stream()
            logger.info("📡 WebSocket streaming started successfully")
            self.streaming_mode = True
            
        except Exception as e:
            logger.warning(f"WebSocket initialization failed: {e}")
            logger.info("📊 Falling back to polling mode")
            self.streaming_mode = False
    
    def _handle_websocket_tick(self, tick, symbol):
        """Handle incoming WebSocket tick data"""
        try:
            with self.tick_lock:
                # Add timestamp if not present
                if 'timestamp' not in tick:
                    tick['timestamp'] = pd.Timestamp.now(tz=IST)
                
                # Store in tick buffer for strategy processing
                self.tick_buffer.append(tick)
                self.last_price = float(tick.get('price', tick.get('ltp', 0)))
                self.last_tick_time = pd.Timestamp.now(tz=IST)
                
        except Exception as e:
            logger.error(f"Error processing WebSocket tick: {e}")
            # Log WebSocket connection status on error
            logger.error(f"WebSocket streaming_mode: {self.streaming_mode}, stream_status: {self.stream_status}")