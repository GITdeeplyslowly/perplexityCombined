"""
live/broker_adapter.py

Unified SmartAPI broker/tick data adapter for live trading and forward test simulation.
- Handles SmartAPI login/session (via login.py/session manager).
- Streams live ticks via websocket or falls back to polling mode.
- Buffers ticks, generates 1-min OHLCV bars.
- Simulates orders in paper trading; never sends real orders.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
import pandas as pd
import os
import threading

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

        # Dynamic imports for SmartAPI
        try:
            from SmartApi import SmartConnect
            self.SmartConnect = SmartConnect
        except ImportError:
            self.SmartConnect = None
            logger.warning("SmartAPI not installed; running in simulated mode.")
            
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
            logger.info("Paper trading mode: running in simulation with synthetic ticks.")
            self.stream_status = "simulation"
            return
            
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
    
    def _connect_with_retry(self):
        """Attempt broker connection with explicit retry logic and clear error messages."""
        max_attempts = 3
        retry_delay = 5  # seconds
        
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"🔄 CONNECTION ATTEMPT {attempt}/{max_attempts}: Connecting to SmartAPI...")
                
                live = self.live_params
                
                # Try session manager first (loads existing saved session)
                if attempt == 1:
                    try:
                        from live.login import SmartAPISessionManager
                        # Use empty strings for missing PIN/TOTP in session manager mode
                        pin = live.get("pin", "")
                        totp = live.get("totp_token", "")
                        
                        self.session_manager = SmartAPISessionManager(
                            live["api_key"], live["client_code"], pin, totp
                        )
                        session_info = self.session_manager.load_session_from_file()
                        if session_info and self.session_manager.is_session_valid():
                            self.connection = self.session_manager.get_smartconnect()
                            self.feed_active = True
                            logger.info("✅ CONNECTED: Reusing saved SmartAPI session (no re-authentication needed)")
                            self._initialize_streaming()
                            self.stream_status = "connected"
                            return
                        else:
                            logger.warning("⏰ EXPIRED SESSION DETECTED: Saved session is no longer valid")
                            logger.info("🔄 Attempting automatic session renewal...")
                    except Exception as e:
                        logger.warning(f"⚠️  Session manager failed: {e}. Trying direct authentication...")
                
                # Fresh login attempt - handle both auto-renewal and manual auth
                pin = live.get("pin", "")
                totp = live.get("totp_token", "")
                
                if not pin or not totp:
                    # Check if we have saved credentials from previous session
                    saved_session = getattr(self, 'session_manager', None)
                    if saved_session and hasattr(saved_session, 'pin') and saved_session.pin and saved_session.totp_token:
                        logger.info("🔄 Using saved credentials for session renewal")
                        pin = saved_session.pin
                        totp = saved_session.totp_token
                    else:
                        # Last resort: Interactive authentication
                        logger.error("🚨 CRITICAL: Session expired and no stored credentials available!")
                        error_msg = (
                            "⏰ SESSION EXPIRED: Cannot auto-renew authentication!\n"
                            "💡 SOLUTIONS:\n"
                            "   1. Add 'pin' and 'totp_token' to config for automatic renewal\n"
                            "   2. Or restart system to re-authenticate manually\n"
                            "   3. Use GUI login to save new session\n"
                            "⚠️  TRADING OPERATIONS SUSPENDED until re-authentication"
                        )
                        logger.error(error_msg)
                        
                        # Attempt to prompt for credentials if possible
                        if self._can_prompt_for_credentials():
                            pin, totp = self._prompt_for_credentials()
                        else:
                            raise ValueError(error_msg)
                
                self.connection = self.SmartConnect(api_key=live["api_key"])
                client_code = live["client_code"]
                
                logger.info(f"🔐 Fresh authentication with SmartAPI (client: {client_code[:4]}****)")
                session = self.connection.generateSession(client_code, pin, totp)
                self.auth_token = session["data"]["jwtToken"]
                self.feed_token = self.connection.getfeedToken()
                self.feed_active = True
                
                # Save session for future use
                try:
                    if self.session_manager:
                        self.session_manager.session = self.connection
                        self.session_manager.login()
                        logger.info("💾 Session saved for future use (no re-authentication needed next time)")
                except Exception as e:
                    logger.warning(f"Could not save session: {e}")
                
                logger.info(f"✅ CONNECTED: Fresh SmartAPI session established for {client_code}")
                self._initialize_streaming()
                self.stream_status = "connected"
                return
                
            except Exception as e:
                error_details = str(e)
                logger.error(f"❌ CONNECTION ATTEMPT {attempt}/{max_attempts} FAILED: {error_details}")
                
                if attempt < max_attempts:
                    logger.warning(f"⏳ RETRYING in {retry_delay} seconds... ({max_attempts - attempt} attempts remaining)")
                    import time
                    time.sleep(retry_delay)
                else:
                    # Final failure - no more attempts
                    final_error = (
                        f"🚨 CRITICAL FAILURE: Unable to establish broker connection after {max_attempts} attempts!\n"
                        f"💀 LAST ERROR: {error_details}\n"
                        f"⚠️  TRADING SYSTEM CANNOT OPERATE WITHOUT BROKER CONNECTION\n"
                        f"📞 CHECK: Network connectivity, API credentials, broker status\n"
                        f"🔧 VERIFY: API key, client code, PIN, TOTP token are correct\n"
                        f"❌ SYSTEM SHUTDOWN: Trading operations terminated"
                    )
                    logger.error(final_error)
                    self.stream_status = "failed"
                    raise ConnectionError(f"Broker connection failed after {max_attempts} attempts: {error_details}")
    
    def _can_prompt_for_credentials(self) -> bool:
        """Check if interactive credential prompting is possible."""
        # Only allow interactive prompts in development mode or when explicitly enabled
        return (
            hasattr(self, 'config') and 
            self.config.get('live', {}).get('allow_interactive_auth', False)
        )
    
    def _prompt_for_credentials(self):
        """Interactively prompt for PIN and TOTP when session expires."""
        logger.info("🔐 INTERACTIVE AUTHENTICATION: Session expired, prompting for credentials...")
        
        try:
            import getpass
            print("\n" + "="*60)
            print("🚨 TRADING SESSION EXPIRED - AUTHENTICATION REQUIRED")
            print("="*60)
            print("Your SmartAPI session has expired. Please provide credentials to continue:")
            
            pin = getpass.getpass("📱 Trading PIN: ").strip()
            totp = getpass.getpass("🔑 TOTP Token: ").strip()
            
            if not pin or not totp:
                raise ValueError("PIN and TOTP are required")
                
            print("✅ Credentials received. Attempting to renew session...")
            return pin, totp
            
        except Exception as e:
            logger.error(f"Interactive authentication failed: {e}")
            raise ValueError("Could not obtain credentials interactively")

    def _initialize_streaming(self):
        """Initialize WebSocket streaming with fail-fast behavior."""
        if not self.connection or not hasattr(self, 'feed_token'):
            error_msg = (
                "🚨 CRITICAL ERROR: Cannot initialize data streaming!\n"
                "❌ Missing broker connection or feed token\n"
                "⚠️  TRADING SYSTEM REQUIRES LIVE DATA FEED\n"
                "🔧 VERIFY: Broker connection established successfully"
            )
            logger.error(error_msg)
            raise RuntimeError("Data streaming initialization failed - no valid broker connection")
            
        if self.WebSocketTickStreamer and self.feed_token:
            try:
                self._start_websocket_stream()
            except Exception as e:
                logger.warning(f"WebSocket initialization failed: {e}")
                self._switch_to_polling()
        else:
            logger.info("WebSocket not available; using polling mode")
            self._switch_to_polling()

    def _start_websocket_stream(self):
        """Start WebSocket streaming for real-time ticks."""
        try:
            # Get instrument token for streaming - must be set by user for specific option contract
            instrument_token = self.instrument.get('instrument_token', '').strip()
            if not instrument_token:
                raise ValueError(f"instrument_token not set for symbol '{self.symbol}'. Please select a specific option contract and ensure token is populated from token cache.")
            
                
            symbol_tokens = [{
                "symbol": self.symbol,
                "token": instrument_token,
                "exchange": self.exchange
            }]
            
            self.stream_status = "connecting"
            self.ws_streamer = self.WebSocketTickStreamer(
                api_key=self.live_params["api_key"],  # STRICT ACCESS - fail-fast if missing
                client_code=self.live_params["client_code"],  # STRICT ACCESS - fail-fast if missing
                feed_token=self.feed_token,
                symbol_tokens=symbol_tokens,
                feed_type="LTP",  # Use LTP for fastest updates
                on_tick=self._on_websocket_tick
            )
            
            self.ws_streamer.start_stream()
            self.streaming_mode = True
            self.stream_status = "streaming"
            self.last_tick_time = now_ist()
            logger.info(f"WebSocket streaming started for {self.symbol}")
            
        except Exception as e:
            logger.error(f"Failed to start WebSocket stream: {e}")
            self._switch_to_polling()

    def _on_websocket_tick(self, tick, symbol):
        """Handle incoming WebSocket tick data."""
        try:
            with self.tick_lock:
                # Update last tick time for heartbeat monitoring
                self.last_tick_time = now_ist()
                
                # Convert WebSocket tick to standard format
                # STRICT ACCESS - NO FALLBACKS IN TRADING SYSTEMS
                # Invalid tick data should fail immediately, not corrupt algorithm
                if "price" not in tick or "volume" not in tick:
                    raise ValueError(f"Invalid tick data: missing required fields. Tick: {tick}")
                
                standardized_tick = {
                    "timestamp": tick.get("timestamp", now_ist()),  # timestamp can fallback to current time
                    "price": float(tick["price"]),  # STRICT - fail if missing
                    "volume": int(tick["volume"])   # STRICT - fail if missing
                }
                
                # Update last price and buffer the tick
                self.last_price = standardized_tick["price"]
                self._buffer_tick(standardized_tick)
                
        except Exception as e:
            logger.error(f"Error processing WebSocket tick: {e}")

    def _switch_to_polling(self):
        """Switch to polling mode as fallback."""
        if self.ws_streamer:
            try:
                self.ws_streamer.stop_stream()
            except Exception as e:
                logger.warning(f"Error stopping WebSocket: {e}")
            self.ws_streamer = None
            
        self.streaming_mode = False
        self.stream_status = "polling"
        logger.info("Switched to polling mode for tick data")

    def _check_stream_health(self):
        """Check if WebSocket stream is healthy and switch to polling if needed."""
        if not self.streaming_mode or not self.last_tick_time:
            return
            
        time_since_last_tick = (now_ist() - self.last_tick_time).total_seconds()
        
        if time_since_last_tick > self.heartbeat_threshold:
            logger.warning(f"No ticks received for {time_since_last_tick:.1f}s; switching to polling")
            self._switch_to_polling()
            
    def _attempt_reconnect(self):
        """Attempt to reconnect WebSocket stream with exponential backoff."""
        if self.streaming_mode or self.paper_trading:
            return
            
        current_time = now_ist()
        
        # Check cooldown period
        if (self.last_reconnect_time and 
            (current_time - self.last_reconnect_time).total_seconds() < self.reconnect_cooldown):
            return
            
        # Check max attempts
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            return
            
        try:
            logger.info(f"Attempting WebSocket reconnect (attempt {self.reconnect_attempts + 1})")
            self.reconnect_attempts += 1
            self.last_reconnect_time = current_time
            
            self._start_websocket_stream()
            
            if self.streaming_mode:
                logger.info("WebSocket reconnection successful")
                self.reconnect_attempts = 0  # Reset on success
                
        except Exception as e:
            logger.error(f"WebSocket reconnection failed: {e}")

    def get_stream_status(self) -> Dict[str, Any]:
        """Get current streaming status for GUI display."""
        status = {
            "mode": "streaming" if self.streaming_mode else "polling",
            "status": self.stream_status,
            "last_tick_age": None,
            "reconnect_attempts": self.reconnect_attempts,
            "connection_active": self.feed_active
        }
        
        if self.last_tick_time:
            status["last_tick_age"] = (now_ist() - self.last_tick_time).total_seconds()
            
        return status

    def get_next_tick(self) -> Optional[Dict[str, Any]]:
        """Fetch next tickâ€”using SmartAPI polling, or simulated if in paper mode."""
        if self.paper_trading or not self.connection:
            # Simulate tick by quick micro-oscillation
            last = self.last_price or 22000.0
            direction = 1 if int(time.time() * 10) % 2 == 0 else -1
            price = last + direction * self.tick_size
            tick = {"timestamp": now_ist(), "price": price, "volume": 1500}
            self.last_price = price
            self._buffer_tick(tick)
            return tick
        try:
            ltp = self.connection.ltpData(self.exchange, self.symbol, self.instrument["instrument_token"])
            price = float(ltp["data"]["ltp"])
            tick = {"timestamp": now_ist(), "price": price, "volume": 1000}
            self.last_price = price
            self._buffer_tick(tick)
            return tick
        except Exception as e:
            logger.error(f"Error fetching SmartAPI LTP: {e}")
            return None

    def get_next_tick_enhanced(self) -> Optional[Dict[str, Any]]:
        """Enhanced tick fetching with WebSocket streaming and health monitoring."""
        # Health monitoring and auto-recovery
        if not self.paper_trading:
            self._check_stream_health()
            self._attempt_reconnect()
        
        if self.paper_trading or not self.connection:
            # Simulate tick by quick micro-oscillation
            last = self.last_price or 22000.0
            direction = 1 if int(time.time() * 10) % 2 == 0 else -1
            price = last + direction * self.tick_size
            tick = {"timestamp": now_ist(), "price": price, "volume": 1500}
            self.last_price = price
            self._buffer_tick(tick)
            return tick
            
        if self.streaming_mode:
            # In WebSocket mode, ticks are buffered by _on_websocket_tick
            # Return None if no new ticks (non-blocking)
            return None
        else:
            # Polling mode - actively fetch LTP
            try:
                # instrument_token must be set by user for specific option contract
                instrument_token = self.instrument.get('instrument_token', '').strip()
                if not instrument_token:
                    raise ValueError(f"instrument_token not set for symbol '{self.symbol}'. Please select a specific option contract and ensure token is populated from token cache.")
                ltp = self.connection.ltpData(self.exchange, self.symbol, instrument_token)
                price = float(ltp["data"]["ltp"])
                tick = {"timestamp": now_ist(), "price": price, "volume": 1000}
                
                with self.tick_lock:
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
            self.df_tick = self.df_tick.iloc[-1000:]

    def get_recent_bars(self, last_n: int = 100) -> pd.DataFrame:
        """Aggregate tick buffer into most recent N 1-min OHLCV bars."""
        if self.df_tick.empty:
            now = now_ist()
            return pd.DataFrame({
                "open": [self.last_price],
                "high": [self.last_price],
                "low": [self.last_price],
                "close": [self.last_price],
                "volume": [0]
            }, index=[now])
        df = self.df_tick.copy()
        df.index = pd.to_datetime(df["timestamp"])
        df = df.sort_index()
        ohlc = df["price"].resample("1T").ohlc()
        volume = df["volume"].resample("1T").sum()
        bars = pd.concat([ohlc, volume], axis=1).dropna()
        bars.rename(columns={"sum": "volume"}, inplace=True)
        return bars.tail(last_n)

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
                logger.info("WebSocket stream stopped")
            except Exception as e:
                logger.warning(f"Error stopping WebSocket stream: {e}")
            self.ws_streamer = None
            
        # Clean up SmartAPI session
        if self.connection and not self.paper_trading:
            try:
                # STRICT ACCESS - NO FALLBACKS IN TRADING SYSTEMS
                client_code = self.live_params["client_code"]
                if client_code:
                    self.connection.terminateSession(client_code)
                logger.info("Broker session terminated.")
            except Exception as e:
                logger.warning(f"Error shutting down session: {e}")
                
        self.stream_status = "disconnected"
        self.streaming_mode = False
        self.feed_active = False
