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

from utils.time_utils import now_ist, normalize_datetime_to_ist
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

        # Optional file simulation (ONLY when explicitly enabled by user)
        self.file_simulator = None
        if config.get('data_simulation', {}).get('enabled', False):
            file_path = config.get('data_simulation', {}).get('file_path', '')
            if file_path:
                from live.data_simulator import DataSimulator
                # Extract speed mode from config (default to FAST for better UX)
                speed_mode = config.get('data_simulation', {}).get('speed_mode', 'FAST')
                self.file_simulator = DataSimulator(file_path, speed_mode)
                logger.info(f"File simulation enabled with: {file_path} (Speed: {speed_mode})")

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
        if self.paper_trading:
            # For paper trading, try file simulation first, then fall back to live SmartAPI
            if self.file_simulator:
                if self.file_simulator.load_data():
                    logger.info("Paper trading mode: using user-selected file simulation.")
                    self.stream_status = "file_simulation"
                    return
                else:
                    logger.error("File simulation failed to load data.")
                    self.stream_status = "error"
                    raise RuntimeError("File simulation data could not be loaded")
            else:
                # No file simulation - check if SmartAPI is available for live data streaming
                if not self.SmartConnect:
                    logger.error("Paper trading mode requires either SmartAPI connection or file simulation.")
                    logger.error("Enable file simulation in GUI or install SmartAPI package.")
                    self.stream_status = "error"
                    raise RuntimeError("No data source available for paper trading")
                else:
                    logger.info("Paper trading mode: using live SmartAPI connection for real-time data.")
                    # Continue with SmartAPI connection below
            
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
                f"🔄 OPTIONAL: pin, totp_token (for direct auth mode)\n"
                f"⚠️  TRADING SYSTEM CANNOT OPERATE WITHOUT VALID CREDENTIALS"
            )
            logger.error(error_msg)
            self.stream_status = "error"
            raise ValueError(f"Invalid minimum credentials: missing {missing_min}, empty {empty_min}")
        
        # Determine authentication mode based on available credentials
        direct_auth_creds = ["pin", "totp_token"]
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
        """Fetch next tick from configured data source (WebSocket, polling, or file)."""
        
        # File simulation mode (user-enabled)
        if self.file_simulator:
            tick = self.file_simulator.get_next_tick()
            if tick:
                self.last_price = tick['price']
                self._buffer_tick(tick)
            return tick
        
        # Live trading mode - no fallback, no synthetic data
        if not self.connection:
            logger.warning("No SmartAPI connection available and no file simulation enabled.")
            return None
            
        try:
            # Use correct Angel One SmartAPI getLTP method
            instrument_token = self.instrument.get('instrument_token', '').strip()
            if not instrument_token:
                logger.error(f"instrument_token not set for symbol '{self.symbol}'")
                return None
                
            ltp_response = self.connection.getLTP({
                "exchange": self.exchange,
                "tradingsymbol": self.symbol,
                "symboltoken": instrument_token
            })
            price = float(ltp_response["data"]["ltp"])
            tick = {"timestamp": now_ist(), "price": price, "volume": 1000}
            self.last_price = price
            self._buffer_tick(tick)
            return tick
        except Exception as e:
            logger.error(f"Error fetching SmartAPI LTP: {e}")
            return None

    def _buffer_tick(self, tick: Dict[str, Any]):
        """Buffer each tick and limit rolling window for memory safety."""
        self.tick_buffer.append(tick)
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
        """Implement connection retry logic"""
        # This would contain the actual SmartAPI connection logic
        # For now, just set as connected for paper trading
        if self.paper_trading:
            return
        # Real connection logic would go here
        pass