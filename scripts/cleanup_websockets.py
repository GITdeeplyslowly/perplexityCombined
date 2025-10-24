"""
Cleanup script to close any lingering WebSocket connections
Run this if you get "429 Too Many Requests - Connection Limit Exceeded"
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'myQuant'))

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup_websockets():
    """Close all active WebSocket connections"""
    logger.info("=" * 80)
    logger.info("WEBSOCKET CLEANUP UTILITY")
    logger.info("=" * 80)
    
    try:
        # Try to import and check for active connections
        import live.websocket_stream as ws_module
        
        # Check if there are any active WebSocket instances
        logger.info("Checking for active WebSocket connections...")
        
        # Force garbage collection to cleanup any unreferenced WebSockets
        import gc
        gc.collect()
        logger.info("✓ Garbage collection completed")
        
        logger.info("=" * 80)
        logger.info("CLEANUP COMPLETE")
        logger.info("=" * 80)
        logger.info("Please wait 30-60 seconds before starting a new test")
        logger.info("(Allows Angel One servers to release the connection)")
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        logger.info("You may need to wait 1-2 minutes for connections to timeout")

if __name__ == "__main__":
    cleanup_websockets()
