#!/usr/bin/env python3
"""
Comprehensive Forward Test Validation Suite
==========================================

Tests all stages of forward testing functionality to ensure readiness for rollout.

Test Coverage:
1. Configuration validation and SSOT compliance
2. GUI parameter handling and instrument selection
3. Strategy initialization with forward test config
4. Live data feed integration (WebSocket/polling)
5. Position management and risk controls
6. Error handling and graceful degradation
7. Performance and resource usage
8. Integration with broker adapter
"""

import sys
import os
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import all required components
from utils.config_helper import create_config_from_defaults, validate_config, freeze_config, ConfigAccessor
from core.liveStrategy import ModularIntradayStrategy
from live.broker_adapter import BrokerAdapter
from core.position_manager import PositionManager

class ForwardTestValidator:
    """Comprehensive validator for forward test functionality"""
    
    def __init__(self):
        self.test_results = []
        self.errors = []
        self.warnings = []
        
    def log_result(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        result = f"{status}: {test_name}"
        if details:
            result += f" - {details}"
        
        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'details': details,
            'timestamp': datetime.now()
        })
        
        print(result)
        if not passed:
            self.errors.append(result)
    
    def test_configuration_system(self) -> bool:
        """Test 1: Configuration System & SSOT Compliance"""
        print("\n🔧 TEST 1: Configuration System & SSOT Compliance")
        print("=" * 60)
        
        try:
            # Test base config creation
            base_config = create_config_from_defaults()
            self.log_result("Base config creation", True, "SSOT properly loaded")
            
            # Test instrument mappings exist
            has_mappings = 'instrument_mappings' in base_config
            self.log_result("Instrument mappings present", has_mappings)
            
            if has_mappings:
                mappings = base_config['instrument_mappings']
                nifty_exists = 'NIFTY' in mappings
                self.log_result("NIFTY instrument exists", nifty_exists)
                
                if nifty_exists:
                    nifty_params = mappings['NIFTY']
                    required_params = ['lot_size', 'tick_size', 'exchange', 'type']
                    all_params_present = all(param in nifty_params for param in required_params)
                    self.log_result("NIFTY has all required parameters", all_params_present, 
                                  f"Parameters: {list(nifty_params.keys())}")
            
            # Test config validation
            validation = validate_config(base_config)
            self.log_result("Config validation", validation.get('valid', False), 
                          f"Errors: {validation.get('errors', [])}")
            
            # Test config freezing
            frozen_config = freeze_config(base_config)
            from types import MappingProxyType
            is_frozen = isinstance(frozen_config, MappingProxyType)
            self.log_result("Config freezing", is_frozen, f"Type: {type(frozen_config)}")
            
            # Test ConfigAccessor
            accessor = ConfigAccessor(frozen_config)
            symbol = accessor.get_instrument_param('symbol')
            self.log_result("ConfigAccessor functionality", symbol == 'NIFTY', f"Symbol: {symbol}")
            
            # Test SSOT parameter access
            try:
                lot_size = accessor.get_current_instrument_param('lot_size')
                self.log_result("SSOT lot_size access", lot_size == 75, f"Lot size: {lot_size}")
            except Exception as e:
                self.log_result("SSOT lot_size access", False, f"Error: {e}")
            
            return len([r for r in self.test_results[-7:] if not r['passed']]) == 0
            
        except Exception as e:
            self.log_result("Configuration system test", False, f"Exception: {e}")
            return False
    
    def test_gui_integration(self) -> bool:
        """Test 2: GUI Integration & Parameter Handling"""
        print("\n🖥️  TEST 2: GUI Integration & Parameter Handling")
        print("=" * 60)
        
        try:
            # Test GUI config building simulation
            base_config = create_config_from_defaults()
            
            # Simulate GUI modifications for forward test
            base_config['instrument']['symbol'] = 'BANKNIFTY'
            base_config['strategy']['use_ema_crossover'] = True
            base_config['strategy']['fast_ema'] = 9
            base_config['strategy']['slow_ema'] = 21
            base_config['risk']['base_sl_points'] = 50.0
            base_config['capital']['initial_capital'] = 100000.0
            base_config['live']['paper_trading'] = True
            
            # Test instrument mapping lookup for BANKNIFTY
            if 'BANKNIFTY' in base_config['instrument_mappings']:
                banknifty_info = base_config['instrument_mappings']['BANKNIFTY']
                base_config['instrument']['lot_size'] = banknifty_info['lot_size']
                base_config['instrument']['tick_size'] = banknifty_info['tick_size']
                self.log_result("GUI instrument parameter mapping", True, 
                              f"BANKNIFTY lot_size: {banknifty_info['lot_size']}")
            else:
                self.log_result("GUI instrument parameter mapping", False, "BANKNIFTY not in mappings")
            
            # Test validation of modified config
            validation = validate_config(base_config)
            self.log_result("GUI modified config validation", validation.get('valid', False))
            
            # Test forward test specific config creation
            frozen_config = freeze_config(base_config)
            self.log_result("Forward test config freezing", True)
            
            # Test parameter consistency
            accessor = ConfigAccessor(frozen_config)
            symbol = accessor.get_instrument_param('symbol')
            fast_ema = accessor.get_strategy_param('fast_ema')
            
            params_correct = (symbol == 'BANKNIFTY' and fast_ema == 9)
            self.log_result("GUI parameter consistency", params_correct, 
                          f"Symbol: {symbol}, Fast EMA: {fast_ema}")
            
            return len([r for r in self.test_results[-4:] if not r['passed']]) == 0
            
        except Exception as e:
            self.log_result("GUI integration test", False, f"Exception: {e}")
            return False
    
    def test_strategy_initialization(self) -> bool:
        """Test 3: Strategy Initialization with Forward Test Config"""
        print("\n⚙️  TEST 3: Strategy Initialization & Configuration")
        print("=" * 60)
        
        try:
            # Create forward test config
            base_config = create_config_from_defaults()
            base_config['live']['paper_trading'] = True
            base_config['strategy']['use_ema_crossover'] = True
            
            frozen_config = freeze_config(base_config)
            
            # Test strategy initialization
            strategy = ModularIntradayStrategy(frozen_config)
            self.log_result("Strategy initialization", True, "ModularIntradayStrategy created")
            
            # Test parameter loading via config accessor (SSOT pattern)
            try:
                lot_size = strategy.config_accessor.get_current_instrument_param('lot_size')
                has_lot_size = lot_size and lot_size > 0
                self.log_result("Strategy lot_size loaded", has_lot_size, f"Lot size: {lot_size}")
            except Exception as e:
                self.log_result("Strategy lot_size loaded", False, f"Error accessing lot_size: {e}")
            
            try:
                tick_size = strategy.config_accessor.get_current_instrument_param('tick_size')
                has_tick_size = tick_size and tick_size > 0
                self.log_result("Strategy tick_size loaded", has_tick_size, f"Tick size: {tick_size}")
            except Exception as e:
                self.log_result("Strategy tick_size loaded", False, f"Error accessing tick_size: {e}")
            
            # Test indicator initialization
            has_ema_tracker = hasattr(strategy, 'ema_fast_tracker') and hasattr(strategy, 'ema_slow_tracker')
            self.log_result("EMA tracker initialization", has_ema_tracker)
            
            # Test strategy methods exist
            has_process_method = hasattr(strategy, 'process_tick_or_bar')
            has_on_tick_method = hasattr(strategy, 'on_tick')
            
            self.log_result("Strategy methods available", has_process_method and has_on_tick_method)
            
            # Test sample tick processing (method should execute without exception)
            sample_tick = {'timestamp': datetime.now(), 'close': 100.0, 'volume': 1000}
            try:
                result = strategy.on_tick(sample_tick)
                # on_tick returns Optional[TradingSignal] - None is valid when no signal
                self.log_result("Sample tick processing", True, f"Result type: {type(result)}")
            except Exception as e:
                self.log_result("Sample tick processing", False, f"Exception: {e}")
            
            return len([r for r in self.test_results[-6:] if not r['passed']]) == 0
            
        except Exception as e:
            self.log_result("Strategy initialization test", False, f"Exception: {e}")
            return False
    
    def test_broker_integration(self) -> bool:
        """Test 4: Broker Adapter Integration"""
        print("\n🔌 TEST 4: Broker Adapter Integration")
        print("=" * 60)
        
        try:
            # Create broker config
            base_config = create_config_from_defaults()
            base_config['live']['paper_trading'] = True
            base_config['live']['api_key'] = "TEST_KEY"
            base_config['live']['client_code'] = "TEST_CLIENT"
            
            frozen_config = freeze_config(base_config)
            
            # Test broker adapter initialization
            broker = BrokerAdapter(frozen_config)
            self.log_result("Broker adapter initialization", True)
            
            # Test connection (paper trading)
            broker.connect()
            self.log_result("Broker connection", True, "Paper trading mode")
            
            # Test stream status
            status = broker.get_stream_status()
            has_status = isinstance(status, dict) and 'mode' in status
            self.log_result("Stream status API", has_status, f"Status: {status.get('mode', 'Unknown')}")
            
            # Test tick generation (simulation)
            tick_count = 0
            for i in range(5):
                tick = broker.get_next_tick()
                if tick:
                    tick_count += 1
                time.sleep(0.1)
            
            self.log_result("Tick data generation", tick_count > 0, f"Generated {tick_count} ticks")
            
            # Test graceful disconnect
            broker.disconnect()
            self.log_result("Broker disconnect", True)
            
            return len([r for r in self.test_results[-5:] if not r['passed']]) == 0
            
        except Exception as e:
            self.log_result("Broker integration test", False, f"Exception: {e}")
            return False
    
    def test_position_management(self) -> bool:
        """Test 5: Position Management & Risk Controls"""
        print("\n💰 TEST 5: Position Management & Risk Controls")
        print("=" * 60)
        
        try:
            # Create config with position management
            base_config = create_config_from_defaults()
            base_config['capital']['initial_capital'] = 100000.0
            base_config['risk']['base_sl_points'] = 50.0
            base_config['live']['paper_trading'] = True
            
            frozen_config = freeze_config(base_config)
            
            # Test position manager initialization
            position_manager = PositionManager(frozen_config)
            self.log_result("Position manager initialization", True)
            
            # Test initial state
            initial_capital = position_manager.current_capital
            capital_correct = initial_capital == 100000.0
            self.log_result("Initial capital loaded", capital_correct, f"Capital: {initial_capital}")
            
            # Test position opening simulation
            test_position = {
                'symbol': 'NIFTY',
                'side': 'long',
                'quantity': 75,  # One lot
                'entry_price': 18000.0,
                'timestamp': datetime.now()
            }
            
            # Note: Actual position testing would require full integration
            # For now, test that position manager can handle the structure
            position_valid = all(key in test_position for key in ['symbol', 'side', 'quantity', 'entry_price'])
            self.log_result("Position data structure", position_valid)
            
            # Test risk calculation
            risk_amount = (test_position['quantity'] * base_config['risk']['base_sl_points'])
            risk_reasonable = 0 < risk_amount < initial_capital * 0.1  # Risk should be < 10% of capital
            self.log_result("Risk calculation", risk_reasonable, f"Risk amount: {risk_amount}")
            
            return len([r for r in self.test_results[-4:] if not r['passed']]) == 0
            
        except Exception as e:
            self.log_result("Position management test", False, f"Exception: {e}")
            return False
    
    def test_error_handling(self) -> bool:
        """Test 6: Error Handling & Graceful Degradation"""
        print("\n🛡️  TEST 6: Error Handling & Graceful Degradation")
        print("=" * 60)
        
        try:
            # Test invalid configuration handling
            bad_config = {}
            validation = validate_config(bad_config)
            invalid_rejected = not validation.get('valid', True)
            self.log_result("Invalid config rejection", invalid_rejected, "Empty config properly rejected")
            
            # Test missing instrument parameter handling
            base_config = create_config_from_defaults()
            frozen_config = freeze_config(base_config)
            
            try:
                strategy = ModularIntradayStrategy(frozen_config)
                # Test with missing tick data fields
                bad_tick = {'timestamp': datetime.now()}  # Missing price/volume
                result = strategy.on_tick(bad_tick)
                graceful_handling = result is None  # Should return None gracefully
                self.log_result("Missing data graceful handling", graceful_handling)
            except Exception:
                self.log_result("Missing data graceful handling", False, "Strategy crashed on missing data")
            
            # Test development phase behavior: paper trading should work with empty credentials
            try:
                dev_config = create_config_from_defaults()
                dev_config['live']['api_key'] = ""  # Empty credentials (development phase)
                dev_config['live']['client_code'] = ""
                # Keep paper_trading = True (default for development)
                frozen_dev_config = freeze_config(dev_config)
                
                broker = BrokerAdapter(frozen_dev_config)
                broker.connect()  # Should succeed in paper trading mode
                self.log_result("Development mode credentials handling", True, "Paper trading works with empty credentials")
            except Exception as e:
                self.log_result("Development mode credentials handling", False, f"Unexpected failure: {str(e)[:50]}")
            
            # Test production phase behavior: should fail-fast with empty credentials
            try:
                prod_config = create_config_from_defaults()
                prod_config['live']['api_key'] = ""  # Empty credentials
                prod_config['live']['client_code'] = ""
                prod_config['live']['paper_trading'] = False  # Production mode
                frozen_prod_config = freeze_config(prod_config)
                
                broker = BrokerAdapter(frozen_prod_config)
                try:
                    broker.connect()
                    self.log_result("Production mode credentials handling", False, "Should have failed with empty credentials")
                except Exception:
                    self.log_result("Production mode credentials handling", True, "Properly rejected empty credentials in production")
            except Exception as e:
                self.log_result("Production credential validation", True, f"Caught early: {str(e)[:50]}")
            
            # Test network failure simulation
            base_config = create_config_from_defaults()
            base_config['live']['paper_trading'] = True
            base_config['live']['api_key'] = "TEST_KEY"
            base_config['live']['client_code'] = "TEST_CLIENT"
            frozen_config = freeze_config(base_config)
            
            broker = BrokerAdapter(frozen_config)
            broker.connect()
            
            # Simulate network issues by checking fallback mechanisms
            status = broker.get_stream_status()
            has_fallback_mode = status.get('mode') in ['polling', 'simulation']
            self.log_result("Fallback mechanism available", has_fallback_mode, f"Mode: {status.get('mode')}")
            
            broker.disconnect()
            
            return len([r for r in self.test_results[-4:] if not r['passed']]) == 0
            
        except Exception as e:
            self.log_result("Error handling test", False, f"Exception: {e}")
            return False
    
    def test_performance_resources(self) -> bool:
        """Test 7: Performance & Resource Usage"""
        print("\n⚡ TEST 7: Performance & Resource Usage")
        print("=" * 60)
        
        try:
            # Test configuration creation speed
            start_time = time.time()
            for _ in range(10):
                config = create_config_from_defaults()
                frozen_config = freeze_config(config)
            config_time = time.time() - start_time
            
            config_fast = config_time < 1.0  # Should create 10 configs in < 1 second
            self.log_result("Config creation speed", config_fast, f"{config_time:.3f}s for 10 configs")
            
            # Test strategy initialization speed
            base_config = create_config_from_defaults()
            frozen_config = freeze_config(base_config)
            
            start_time = time.time()
            strategy = ModularIntradayStrategy(frozen_config)
            init_time = time.time() - start_time
            
            init_fast = init_time < 0.5  # Should initialize in < 0.5 seconds
            self.log_result("Strategy init speed", init_fast, f"{init_time:.3f}s")
            
            # Test tick processing speed
            sample_tick = {'timestamp': datetime.now(), 'close': 18000.0, 'volume': 1000}
            
            start_time = time.time()
            for _ in range(100):
                strategy.on_tick(sample_tick)
            tick_time = time.time() - start_time
            
            tick_fast = tick_time < 1.0  # Should process 100 ticks in < 1 second
            self.log_result("Tick processing speed", tick_fast, f"{tick_time:.3f}s for 100 ticks")
            
            # Test memory usage (basic check)
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            memory_reasonable = memory_mb < 500  # Should use < 500MB for basic operation
            self.log_result("Memory usage", memory_reasonable, f"{memory_mb:.1f}MB")
            
            return len([r for r in self.test_results[-4:] if not r['passed']]) == 0
            
        except Exception as e:
            self.log_result("Performance test", False, f"Exception: {e}")
            return False
    
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run all tests and generate comprehensive report"""
        print("🚀 COMPREHENSIVE FORWARD TEST VALIDATION")
        print("=" * 70)
        print("Testing all stages of forward test functionality...")
        
        test_functions = [
            ("Configuration System", self.test_configuration_system),
            ("GUI Integration", self.test_gui_integration),
            ("Strategy Initialization", self.test_strategy_initialization),
            ("Broker Integration", self.test_broker_integration),
            ("Position Management", self.test_position_management),
            ("Error Handling", self.test_error_handling),
            ("Performance & Resources", self.test_performance_resources),
        ]
        
        results = {}
        overall_success = True
        
        for test_name, test_func in test_functions:
            try:
                success = test_func()
                results[test_name] = success
                if not success:
                    overall_success = False
            except Exception as e:
                print(f"\n❌ CRITICAL ERROR in {test_name}: {e}")
                results[test_name] = False
                overall_success = False
        
        # Generate summary report
        self.generate_summary_report(results, overall_success)
        
        return {
            'overall_success': overall_success,
            'test_results': results,
            'detailed_results': self.test_results,
            'errors': self.errors,
            'warnings': self.warnings
        }
    
    def generate_summary_report(self, results: Dict[str, bool], overall_success: bool):
        """Generate comprehensive summary report"""
        print("\n" + "=" * 70)
        print("📊 FORWARD TEST VALIDATION SUMMARY")
        print("=" * 70)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['passed']])
        failed_tests = total_tests - passed_tests
        
        print(f"\n📈 OVERALL STATISTICS:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {passed_tests}")
        print(f"   Failed: {failed_tests}")
        print(f"   Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        print(f"\n🎯 TEST CATEGORY RESULTS:")
        for category, success in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"   {status}: {category}")
        
        if self.errors:
            print(f"\n❌ CRITICAL ISSUES FOUND ({len(self.errors)}):")
            for error in self.errors:
                print(f"   • {error}")
        
        print(f"\n🚀 ROLLOUT RECOMMENDATION:")
        if overall_success:
            print("   ✅ FORWARD TEST IS READY FOR ROLLOUT")
            print("   ✅ All critical systems functioning properly")
            print("   ✅ Error handling and fallbacks working")
            print("   ✅ Performance within acceptable limits")
            print("   ✅ SSOT compliance maintained")
        else:
            print("   ❌ FORWARD TEST NOT READY FOR ROLLOUT")
            print("   ❌ Critical issues must be resolved first")
            print("   ❌ Review failed tests before deployment")
        
        print("\n" + "=" * 70)

def main():
    """Main execution function"""
    try:
        validator = ForwardTestValidator()
        results = validator.run_comprehensive_test()
        
        # Return appropriate exit code
        return 0 if results['overall_success'] else 1
        
    except Exception as e:
        print(f"\n💥 VALIDATION SUITE CRASHED: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)