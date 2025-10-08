"""
live/data_simulator.py

COMPLETELY OPTIONAL file-based data simulation for forward testing.

CRITICAL PRINCIPLES:
- This module is ONLY activated when user explicitly enables file simulation in GUI
- Does NOT interfere with live trading functionality in any way
- Does NOT provide fallback data when live streams fail
- Completely user-driven and user-controlled
- If file simulation is not working, the system fails fast with clear error messages

USAGE:
- User enables "File Simulation" checkbox in GUI
- User selects data file via Browse button  
- System uses ONLY this file data, no other sources
- If file is invalid/missing: clear error, no trading
"""

import pandas as pd
import os
import time
import logging
from datetime import datetime
from typing import Dict, Optional
from utils.time_utils import now_ist

logger = logging.getLogger(__name__)

class DataSimulator:
    """Optional file-based data simulator. Does not affect live trading."""
    
    # Speed mode presets (user-configurable)
    SPEED_MODES = {
        'REALTIME': 0.05,     # 20 tps - realistic market speed
        'FAST': 0.01,         # 100 tps - quick testing  
        'TURBO': 0.002,       # 500 tps - rapid validation
        'MAX': 0.0001,        # ~10000 tps - instant results
        'INSTANT': 0          # No delay - maximum speed
    }
    
    def __init__(self, file_path: str = None, speed_mode: str = 'FAST'):
        self.file_path = file_path
        self.data = None
        self.index = 0
        # Default to FAST mode for better testing experience
        self.tick_delay = self.SPEED_MODES.get(speed_mode, self.SPEED_MODES['FAST'])
        self.speed_mode = speed_mode
        self.loaded = False
        self.completed = False  # Flag to prevent repeated completion messages
        
    def load_data(self) -> bool:
        """Load data from file. Returns True if successful."""
        if not self.file_path or not os.path.exists(self.file_path):
            logger.warning(f"Data file not found: {self.file_path}")
            return False
            
        try:
            logger.info(f"Loading simulation data from: {self.file_path}")
            
            # Read CSV file
            self.data = pd.read_csv(self.file_path)
            
            # Standardize columns
            if 'close' in self.data.columns:
                self.data['price'] = self.data['close']
            elif 'Close' in self.data.columns:
                self.data['price'] = self.data['Close']
            elif 'ltp' in self.data.columns:
                self.data['price'] = self.data['ltp']
            elif 'LTP' in self.data.columns:
                self.data['price'] = self.data['LTP']
            
            # Ensure we have a price column
            if 'price' not in self.data.columns:
                # Use first numeric column as price
                numeric_cols = self.data.select_dtypes(include=['number']).columns
                if len(numeric_cols) > 0:
                    self.data['price'] = self.data[numeric_cols[0]]
                else:
                    raise ValueError("No numeric price column found")
            
            # Add default volume if not present
            if 'volume' not in self.data.columns:
                self.data['volume'] = 1000
                
            self.index = 0
            self.loaded = True
            
            # Provide user with time estimates
            total_ticks = len(self.data)
            estimated_time = total_ticks * self.tick_delay
            
            if estimated_time < 60:
                time_str = f"{estimated_time:.0f} seconds"
            elif estimated_time < 3600:
                time_str = f"{estimated_time/60:.1f} minutes"  
            else:
                time_str = f"{estimated_time/3600:.1f} hours"
                
            logger.info(f"📁 Loaded {total_ticks:,} data points for simulation")
            logger.info(f"🚀 Speed mode: {self.speed_mode} ({self.tick_delay}s per tick)")
            logger.info(f"⏱️  Estimated completion time: ~{time_str}")
            
            if estimated_time > 300:  # > 5 minutes
                logger.info("💡 TIP: Use 'TURBO' or 'MAX' speed mode for faster testing")
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to load simulation data: {e}")
            return False
    
    def get_next_tick(self) -> Optional[Dict]:
        """Get next tick from file data. Returns None if no data or end reached."""
        if not self.loaded or self.data is None:
            return None
            
        # Check if we've reached end
        if self.index >= len(self.data):
            if not self.completed:
                self.completed = True
                logger.info("📋 Simulation completed successfully - all data processed")
            return None  # Signal completion, don't restart
            
        # Progress reporting (every 5% for user feedback)
        if self.index % max(1, len(self.data) // 20) == 0:
            progress = (self.index / len(self.data)) * 100
            logger.info(f"📊 Simulation progress: {progress:.1f}% ({self.index}/{len(self.data)}) - Speed: {self.speed_mode}")
            
        # Get current data point
        row = self.data.iloc[self.index]
        self.index += 1
        
        # Create tick
        tick = {
            "timestamp": now_ist(),
            "price": float(row['price']),
            "volume": int(row.get('volume', 1000))
        }
        
        # Apply configurable delay (isolated from live trading)
        if self.tick_delay > 0:
            time.sleep(self.tick_delay)
        
        return tick
    
    def set_speed_mode(self, mode: str):
        """Change simulation speed during runtime (testing only)."""
        if mode in self.SPEED_MODES:
            self.tick_delay = self.SPEED_MODES[mode]
            self.speed_mode = mode
            logger.info(f"🚀 Simulation speed changed to: {mode} ({self.tick_delay}s delay)")
        else:
            available = ', '.join(self.SPEED_MODES.keys())
            logger.warning(f"Invalid speed mode '{mode}'. Available: {available}")
    
    def get_estimated_completion_time(self) -> str:
        """Estimate remaining time for user planning."""
        if not self.loaded or self.tick_delay == 0:
            return "Unknown"
        
        remaining_ticks = len(self.data) - self.index
        remaining_seconds = remaining_ticks * self.tick_delay
        
        if remaining_seconds < 60:
            return f"{remaining_seconds:.0f} seconds"
        elif remaining_seconds < 3600:
            return f"{remaining_seconds/60:.1f} minutes"
        else:
            return f"{remaining_seconds/3600:.1f} hours"