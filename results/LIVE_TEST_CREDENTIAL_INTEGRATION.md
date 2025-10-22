# Live Performance Test - Credential Integration Fix

**Date**: 2025-01-22  
**Issue**: test_live_performance.py created parallel credential system instead of using existing GUI workflow  
**Status**: ✅ FIXED

---

## Problem Identified

The test script (`scripts/test_live_performance.py`) was:
1. Creating its own `SmartAPISessionManager` instance
2. Manually handling authentication and session management
3. Duplicating logic that already exists in `BrokerAdapter`

**User Feedback**:
> "Use existing credential workflow, don't create parallel system"

---

## Solution: Mirror GUI Pattern

### GUI Pattern (noCamel1.py lines 2431-2433)
```python
from config.defaults import load_live_trading_credentials
credentials = load_live_trading_credentials()
config_dict['live'].update(credentials)
```

### Credential Loading Function (CRED/defaults.py lines 14-44)
```python
def load_live_trading_credentials():
    """Load credentials for live trading authentication"""
    credentials = {}
    
    try:
        from dotenv import load_dotenv
        
        # Primary: Load from angelalgo .env.trading file
        angelalgo_env_path = r"C:\Users\user\projects\angelalgo\.env.trading"
        if os.path.exists(angelalgo_env_path):
            load_dotenv(angelalgo_env_path)
        else:
            # Fallback: Load from local .env file
            local_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
            if os.path.exists(local_env_path):
                load_dotenv(local_env_path)
    except ImportError:
        pass
    
    # Load actual credential values
    credentials["api_key"] = os.getenv("API_KEY", "")
    credentials["client_code"] = os.getenv("CLIENT_ID", "")
    credentials["pin"] = os.getenv("PASSWORD", "")
    credentials["totp_secret"] = os.getenv("SMARTAPI_TOTP_SECRET", "")
    
    return credentials
```

---

## Changes Made to test_live_performance.py

### 1. Import Changes (Lines 1-50)
**REMOVED**:
```python
from CRED.live.login import SmartAPISessionManager

def get_credentials_from_config():
    """Extract credentials from DEFAULT_CONFIG or environment."""
    # ... 15 lines of duplicate credential retrieval logic
```

**ADDED**:
```python
from CRED.defaults import DEFAULT_CONFIG, load_live_trading_credentials
```

**Reason**: Use existing single function instead of duplicating logic

---

### 2. Credential Loading (Lines ~93-110)
**REMOVED** (50+ lines):
```python
# Step 3: Get credentials
print("\nAuthenticating with SmartAPI...")
creds = get_credentials_from_config()

if not creds['api_key'] or not creds['client_code']:
    # Error handling...

# Step 4: Authenticate and get session
try:
    session_manager = SmartAPISessionManager(
        api_key=creds['api_key'],
        client_code=creds['client_code'],
        pin=creds['pin'],
        totp_secret=creds['totp_secret']
    )
    
    session_info = session_manager.load_session()
    
    if not session_info or not session_manager.is_session_valid():
        print("No valid session found, logging in...")
        session_info = session_manager.login()
    else:
        print("✓ Using existing valid session")
    
    print(f"✓ Authenticated as: {creds['client_code']}")
    
except Exception as e:
    print(f"\n❌ Authentication failed: {e}")
    return
```

**ADDED** (12 lines):
```python
# Step 3: Load credentials using existing workflow (mirrors GUI pattern)
print("\nLoading SmartAPI credentials...")
credentials = load_live_trading_credentials()

if not credentials.get('api_key') or not credentials.get('client_code'):
    print("\n❌ ERROR: Missing credentials!")
    print("   Please provide credentials via:")
    print("   1. .env.trading file at: C:\\Users\\user\\projects\\angelalgo\\.env.trading")
    print("   2. Environment variables: API_KEY, CLIENT_ID, PASSWORD, SMARTAPI_TOTP_SECRET")
    print("   3. Or configure in CRED/defaults.py")
    return

print(f"✓ Credentials loaded: api_key={'✅' if credentials.get('api_key') else '❌'}, "
      f"client_code={'✅' if credentials.get('client_code') else '❌'}")
```

**Reason**: 
- Simplified from 50+ lines to 12 lines
- Uses existing `load_live_trading_credentials()` function
- Matches GUI pattern exactly
- Delegates session management to BrokerAdapter (where it belongs)

---

### 3. Configuration Update (Lines ~110-125)
**REMOVED**:
```python
# Step 5: Prepare configuration
config = deepcopy(DEFAULT_CONFIG)

# Enable paper trading (safety)
config['live']['paper_trading'] = True
config['live']['api_key'] = creds['api_key']
config['live']['client_code'] = creds['client_code']
```

**ADDED**:
```python
# Step 4: Prepare configuration (mirrors GUI pattern)
config = deepcopy(DEFAULT_CONFIG)

# Update live config with credentials
config['live'].update(credentials)

# Enable paper trading (safety)
config['live']['paper_trading'] = True

# Configure target symbol
config['instrument']['symbol'] = symbol
```

**Reason**: 
- Uses `.update(credentials)` to add all credential fields (api_key, client_code, pin, totp_secret)
- Matches GUI pattern from noCamel1.py line 2433
- No manual field-by-field assignment

---

## Responsibility Delegation

### Before (❌ Wrong)
```
test_live_performance.py
  ↓
SmartAPISessionManager (direct instantiation)
  ↓
Manual session validation
  ↓
Manual login if needed
  ↓
Pass session to BrokerAdapter
```

### After (✅ Correct)
```
test_live_performance.py
  ↓
load_live_trading_credentials() (from defaults.py)
  ↓
Add credentials to config
  ↓
Pass config to LiveTrader
  ↓
LiveTrader → BrokerAdapter (handles session internally)
  ↓
BrokerAdapter → SmartAPISessionManager (when needed)
```

**Key Principle**: Session management is **internal responsibility** of BrokerAdapter, not test script

---

## Code Quality Improvements

### Lines Reduced
- **Before**: ~334 lines with duplicate credential/session logic
- **After**: ~280 lines (removed ~54 lines of duplication)
- **Net**: 16% reduction in code size

### Maintainability
- ✅ Single source of truth: `load_live_trading_credentials()`
- ✅ Consistent with GUI workflow
- ✅ No parallel authentication systems
- ✅ Clearer separation of concerns

### Fail-First Compliance
```python
# Clear error with actionable instructions
if not credentials.get('api_key') or not credentials.get('client_code'):
    print("\n❌ ERROR: Missing credentials!")
    print("   1. .env.trading file at: C:\\Users\\user\\projects\\angelalgo\\.env.trading")
    print("   2. Environment variables: API_KEY, CLIENT_ID, PASSWORD, SMARTAPI_TOTP_SECRET")
    print("   3. Or configure in CRED/defaults.py")
    return  # STOP immediately, don't proceed
```

**Pattern**: Fails immediately with WHAT went wrong AND HOW to fix it

---

## Testing Readiness

### Prerequisites
1. **Credentials configured** in one of:
   - `C:\Users\user\projects\angelalgo\.env.trading` (primary)
   - Local `.env` file (fallback)
   - Environment variables: `API_KEY`, `CLIENT_ID`, `PASSWORD`, `SMARTAPI_TOTP_SECRET`

2. **Instrumentation enabled** (already done):
   - ✅ `websocket_stream.py` - lines 38-43, 114-180
   - ✅ `broker_adapter.py` - lines 47-52, 451-528
   - ✅ `trader.py` - lines 26-31, 472-509

3. **Session file** (automatically managed):
   - `C:\Users\user\projects\angelalgo\auth_token.json`
   - Created/updated by SmartAPISessionManager (inside BrokerAdapter)

### Run Command
```powershell
cd C:\Users\user\projects\PerplexityCombinedTest
python scripts/test_live_performance.py --ticks 1000
```

### Expected Flow
1. Load credentials from .env.trading or environment
2. Create config with credentials
3. Initialize LiveTrader with frozen config
4. LiveTrader creates BrokerAdapter
5. BrokerAdapter manages SmartAPISessionManager internally
6. WebSocket connects and streams live ticks
7. Instrumentation measures latency at all layers
8. Generate reports after 1000 ticks

---

## Alignment with Core Principles

### 1. Single Source of Truth (SSOT) ✅
- Credentials: `load_live_trading_credentials()` in `defaults.py`
- No duplicate credential retrieval logic

### 2. Fail-First, Not Fail-Safe ✅
- Missing credentials → STOP immediately with clear instructions
- No silent fallbacks or assumptions

### 3. Modularity ✅
- Credential loading: `defaults.py`
- Session management: `BrokerAdapter` (internal)
- Testing orchestration: `test_live_performance.py`

### 4. Live WebStream is Paramount ✅
- Test script uses SAME credential workflow as production GUI
- No special testing paths that differ from live trading
- Session management delegated to production components

### 5. Evidence-Driven Development ✅
- Instrumentation installed: Ready to measure real latency
- Will measure actual WebSocket → Broker → Trader → Strategy path
- Decision on Phases 2-5 based on live measurements, not assumptions

---

## Summary

**Problem**: Parallel credential system created duplicate authentication logic  
**Solution**: Use existing `load_live_trading_credentials()` pattern from GUI  
**Result**: 
- ✅ 54 lines removed (16% reduction)
- ✅ Consistent with production workflow
- ✅ Session management delegated to BrokerAdapter
- ✅ Clear fail-first error handling
- ✅ Ready for live WebSocket testing

**Next Step**: Run `python scripts/test_live_performance.py --ticks 1000` to collect actual live performance data

---

**Validation Checklist**:
- [x] Imports use `load_live_trading_credentials` from `defaults.py`
- [x] No direct `SmartAPISessionManager` instantiation
- [x] Credentials added via `config['live'].update(credentials)`
- [x] Clear error messages with fix instructions
- [x] Session management delegated to BrokerAdapter
- [x] Mirrors GUI pattern from noCamel1.py
