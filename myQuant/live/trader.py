"""
live/trader.py

Unified forward-test/live simulation runner.
- Loads configuration and strategy logic.
- Connects to SmartAPI for live tick data (or mock data if in simulation).
- Processes incoming bar/tick data with your core strategy and position manager.
- Simulates all trades: never sends real orders.
"""

import time
import logging
import importlib
import pandas as pd
from types import MappingProxyType
from core.position_manager import PositionManager
from live.broker_adapter import BrokerAdapter
from utils.time_utils import now_ist
from utils.config_helper import validate_config, freeze_config, create_config_from_defaults

def get_strategy(config):
    """Get strategy instance with frozen MappingProxyType config - strict validation"""
    if not isinstance(config, MappingProxyType):
        raise TypeError(f"get_strategy requires frozen MappingProxyType config, got {type(config)}")
    
    strat_module = importlib.import_module("core.liveStrategy")
    ind_mod = importlib.import_module("core.indicators")
    return strat_module.ModularIntradayStrategy(config, ind_mod)

class LiveTrader:
    def __init__(self, config_path: str = None, config_dict: dict = None, frozen_config: MappingProxyType = None):
        """Initialize LiveTrader with frozen config validation
        
        Args:
            config_path: Path to YAML config file (legacy)
            config_dict: Raw dict config (legacy) 
            frozen_config: MappingProxyType from GUI workflow (preferred)
        """
        # Accept frozen config directly from GUI (preferred path)
        if frozen_config is not None:
            if not isinstance(frozen_config, MappingProxyType):
                raise TypeError(f"frozen_config must be MappingProxyType, got {type(frozen_config)}")
            config = frozen_config
        elif config_dict is not None:
            # Legacy path - validate and freeze raw dict
            validation = validate_config(config_dict)
            if not validation.get('valid', False):
                errors = validation.get('errors', ['Unknown validation error'])
                raise ValueError(f"Invalid config: {errors}")
            config = freeze_config(config_dict)
        else:
            # File path - use defaults.py as SSOT (config_path parameter kept for legacy compatibility)
            raw_config = create_config_from_defaults()
            validation = validate_config(raw_config)
            if not validation.get('valid', False):
                errors = validation.get('errors', ['Unknown validation error'])
                raise ValueError(f"Invalid config from defaults: {errors}")
            config = freeze_config(raw_config)
        
        self.config = config
        
        # Pass complete frozen config to strategy (not partial params)
        self.strategy = get_strategy(config)
        
        # Pass frozen config directly to PositionManager (it expects MappingProxyType)
        self.position_manager = PositionManager(config)
        self.broker = BrokerAdapter(config)  # Pass frozen config downstream
        self.is_running = False
        self.active_position_id = None

    def stop(self):
        """Stop the forward test session gracefully"""
        logger = logging.getLogger(__name__)
        logger.info("🛑 Stop requested - ending forward test session")
        self.is_running = False
        
        # Close any open positions
        if self.active_position_id:
            self.close_position("Stop Requested")
        
        # Disconnect broker
        try:
            self.broker.disconnect()
        except Exception as e:
            logger.warning(f"Error disconnecting broker: {e}")
        
        logger.info("✅ Forward test session stopped successfully")

    def start(self, run_once=False, result_box=None):
        self.is_running = True
        logger = logging.getLogger(__name__)
        self.broker.connect()
        logger.info("🟢 Forward testing session started - TRUE TICK-BY-TICK PROCESSING")
        
        # Initialize NaN tracking from defaults - STRICT CONFIG ACCESS (fail fast if missing)
        nan_streak = 0
        nan_threshold = self.config['strategy']['nan_streak_threshold']
        nan_recovery_threshold = self.config['strategy']['nan_recovery_threshold']
        consecutive_valid_ticks = 0
        
        try:
            while self.is_running:
                # STEP 1: Get individual tick (no bar aggregation)
                tick = self.broker.get_next_tick()
                if not tick:
                    # Check if file simulation is complete
                    if hasattr(self.broker, 'file_simulator') and self.broker.file_simulator:
                        if hasattr(self.broker.file_simulator, 'completed') and self.broker.file_simulator.completed:
                            logger.info("File simulation completed - ending trading session")
                            break
                    time.sleep(0.1)
                    continue
                

                
                now = tick['timestamp'] if 'timestamp' in tick else now_ist()
                
                # STEP 2: Session end enforcement (before processing)
                if hasattr(self.strategy, "should_exit_for_session"):
                    if self.strategy.should_exit_for_session(now):
                        self.close_position("Session End")
                        logger.info("Session end: all positions flattened.")
                        break
                
                # STEP 3: TRUE TICK-BY-TICK PROCESSING - Use on_tick() directly
                try:
                    signal = self.strategy.on_tick(tick)
                    
                    # Reset NaN streak on successful processing
                    nan_streak = 0
                    consecutive_valid_ticks += 1
                    
                except Exception as e:
                    # NaN threshold implementation
                    nan_streak += 1
                    consecutive_valid_ticks = 0
                    logger.warning(f"Tick processing failed (streak: {nan_streak}/{nan_threshold}): {e}")
                    
                    if nan_streak >= nan_threshold:
                        logger.error(f"NaN streak threshold ({nan_threshold}) exceeded. Stopping trading.")
                        self.close_position("NaN Threshold Exceeded")
                        break
                    continue
                
                # STEP 4: Process signal immediately if generated
                if signal:
                    current_price = tick.get('price', tick.get('ltp', 0))
                    
                    if signal.action == 'BUY' and not self.active_position_id:
                        # Check if we can enter new position
                        if getattr(self.strategy, "can_enter_new_position", lambda t: True)(now):
                            # Create optimized tick row for position manager
                            tick_row = self._create_tick_row(tick, signal.price, now)
                            
                            self.active_position_id = self.strategy.open_long(tick_row, now, self.position_manager)
                            if self.active_position_id:
                                qty = self.position_manager.positions[self.active_position_id].current_quantity
                                logger.info(f"[TICK] ENTERED LONG at ₹{signal.price:.2f} ({qty} contracts) - {signal.reason}")
                                self._update_result_box(result_box, f"Tick BUY: {qty} @ {signal.price:.2f} ({signal.reason})")
                    
                    elif signal.action == 'CLOSE' and self.active_position_id:
                        self.close_position(f"Strategy Signal: {signal.reason}")
                        self._update_result_box(result_box, f"Tick CLOSE: @ {signal.price:.2f} ({signal.reason})")
                
                # STEP 5: Position manager processes TP/SL/trail exits (if position exists)
                if self.active_position_id:
                    current_price = tick.get('price', tick.get('ltp', 0))
                    current_tick_row = self._create_tick_row(tick, current_price, now)
                    
                    self.position_manager.process_positions(current_tick_row, now)
                    
                    # Check if position was closed by risk management
                    if self.active_position_id not in self.position_manager.positions:
                        logger.info("Position closed by risk management (TP/SL/trailing).")
                        self._update_result_box(result_box, f"Risk CLOSE: @ {current_price:.2f}")
                        # CRITICAL FIX: Notify strategy of position closure to reset state
                        try:
                            self.strategy.on_position_closed(self.active_position_id, "Risk Management")
                        except Exception as e:
                            # Log notification failed, but continue trading
                            logger.warning(f"Strategy notification failed: {e}")
                        self.active_position_id = None
                
                # STEP 6: Check for single-run mode
                if run_once:
                    self.is_running = False
        except KeyboardInterrupt:
            logger.info("Forward test interrupted by user.")
            self.close_position("Keyboard Interrupt")
        except Exception as e:
            logger.exception(f"Error in trading loop: {e}")
            self.close_position("Error Occurred")
        finally:
            self.broker.disconnect()
            logger.info("Session ended, data connection closed.")

    def close_position(self, reason: str = "Manual"):
        if self.active_position_id and self.active_position_id in self.position_manager.positions:
            last_price = self.broker.get_last_price()
            now = now_ist()
            self.position_manager.close_position_full(self.active_position_id, last_price, now, reason)
            logger = logging.getLogger(__name__)
            logger.info(f"[SIM] Position closed at {last_price} for reason: {reason}")
            # CRITICAL FIX: Notify strategy of position closure to reset state
            self.strategy.on_position_closed(self.active_position_id, reason)
            self.active_position_id = None

    def _create_tick_row(self, tick: dict, price: float, timestamp) -> pd.Series:
        """Create standardized tick row for position manager compatibility."""
        return pd.Series({
            'close': price,
            'high': price,
            'low': price,
            'open': price,
            'volume': tick.get('volume', 1000),
            'timestamp': timestamp
        })
    
    def _update_result_box(self, result_box, message: str):
        """Update result box with thread-safe GUI operations."""
        if result_box:
            try:
                result_box.config(state="normal")
                result_box.insert("end", f"{message}\n")
                result_box.see("end")
                result_box.config(state="disabled")
            except Exception as e:
                # GUI updates can fail in threading context
                logging.getLogger(__name__).warning(f"Result box update failed: {e}")

if __name__ == "__main__":
    import argparse
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Unified Forward Test Runner (Paper Trading)")
    parser.add_argument("--config", default="config/strategy_config.yaml", help="Config YAML path")
    args = parser.parse_args()

    bot = LiveTrader(args.config)
    bot.start()
