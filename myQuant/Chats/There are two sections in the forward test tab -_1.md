<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# There are two sections in the forward test tab -

1. Instrument selection - which has fields -
a. Instrument  (More accurate name could index/stock)
b. Exchange (  (More accurate name Instrument) because the drawdown selection is about selecting f\&o or cash instrument.
The number of lots is mapped to these two field and not to the exact symbol.  Thus,  the lot size field  is not directly linked to the symbol.
The symbol selection can be validated against the index/stock and the instrument field, but can remain indipendent.

Perfect! Now I fully understand the architecture. The GUI has **two separate selection mechanisms** that work together:[^1][^2]

## Current Architecture Understanding

### 1. **Instrument Selection** (Primary - Determines lot_size)

**Field Name:** `ft_instrument_type` (GUI label: "Instrument")
**Values:** NIFTY, BANKNIFTY, FINNIFTY, RELIANCE, etc.
**Purpose:** Determines lot_size, tick_size, exchange from `instrument_mappings` SSOT[^2]

### 2. **Exchange/Instrument Type** (Secondary)

**Field Name:** `ft_exchange` (GUI label: "Exchange")
**Values:** NSE_FO, NSE_CM, BSE_FO, BSE_CM
**Purpose:** Specifies whether trading F\&O or Cash instruments[^1]

### 3. **Symbol Selection** (Independent - User Input Only)

**Field Name:** `ft_symbol` (GUI label: "Symbol")
**Values:** NIFTY07OCT2525100CE, BANKNIFTY07OCT2555000PE (dynamic, expires)
**Purpose:** Specific contract for trading, extracted from cache[^1]

## The Error Explanation

The validation code is incorrectly trying to validate the **user-selected symbol** (`NIFTY07OCT2525100CE`) against `instrument_mappings`, when it should be validating based on the **instrument dropdown** selection (`NIFTY`).[^1]

The lot_size comes from the **instrument dropdown**, not from parsing the symbol.[^2][^1]

## Solution: Remove Symbol-to-Mapping Validation

The symbol should be validated **independently** to ensure it's compatible with the selected instrument, but **not** used to look up lot_size/tick_size from SSOT.[^2][^1]

### Updated `ft_build_config_from_gui()` Logic

```python
def ft_build_config_from_gui(self):
    """Build forward test specific configuration from GUI state"""
    config_dict = deepcopy(self.runtime_config)
    
    # 1. INSTRUMENT SELECTION (Primary - determines lot_size from SSOT)
    selected_instrument = self.ft_instrument_type.get()  # e.g., "NIFTY"
    
    if selected_instrument not in self.instrument_mappings:
        raise KeyError(
            f"FATAL: Instrument '{selected_instrument}' not found in instrument_mappings SSOT. "
            f"Available: {list(self.instrument_mappings.keys())}"
        )
    
    instrument_info = self.instrument_mappings[selected_instrument]
    
    # Get metadata from SSOT - STRICT ACCESS
    required_params = ["lot_size", "tick_size", "exchange", "type"]
    for param in required_params:
        if param not in instrument_info:
            raise KeyError(
                f"FATAL: {param} not found for instrument '{selected_instrument}' "
                f"in instrument_mappings SSOT"
            )
    
    config_dict["instrument"]["lot_size"] = instrument_info["lot_size"]
    config_dict["instrument"]["tick_size"] = instrument_info["tick_size"]
    config_dict["instrument"]["instrument_type"] = instrument_info["type"]
    
    # 2. EXCHANGE/INSTRUMENT TYPE (Secondary - F&O vs Cash)
    config_dict["instrument"]["exchange"] = self.ft_exchange.get()
    
    # 3. SYMBOL SELECTION (Independent - user input from cache)
    user_symbol = self.ft_symbol.get().strip()
    user_token = self.ft_token.get().strip()
    
    if not user_symbol:
        raise ValueError("FATAL: Symbol must be selected from cache before starting forward test")
    
    if not user_token:
        raise ValueError("FATAL: Token must be available for selected symbol")
    
    # OPTIONAL: Validate symbol compatibility with selected instrument
    # This is a soft validation - just warn if mismatch detected
    if not user_symbol.startswith(selected_instrument):
        logger.warning(
            f"Symbol '{user_symbol}' may not match selected instrument '{selected_instrument}'. "
            f"Proceeding anyway - verify symbol selection is correct."
        )
    
    config_dict["instrument"]["symbol"] = user_symbol
    config_dict["instrument"]["token"] = user_token
    
    # Continue with rest of configuration...
    # (strategy, risk, capital, session parameters)
```


### Key Design Principles

**Separation of Concerns:**

- **Instrument dropdown** → lot_size, tick_size (from SSOT)
- **Exchange dropdown** → F\&O vs Cash classification
- **Symbol input** → Specific contract for trading (user-driven, dynamic)[^2][^1]

**Validation:**

- Instrument dropdown **must exist** in `instrument_mappings` (fail-fast)
- Symbol **must be non-empty** (fail-fast)
- Symbol compatibility with instrument is **optional warning** (not fail-fast)[^1]

**No Symbol Parsing for SSOT Lookup:**

- Never extract base instrument from symbol for lot_size lookup
- lot_size comes directly from instrument dropdown selection
- Symbol remains independent and dynamic (handles daily expirations)[^2][^1]

This design maintains strict SSOT validation while allowing flexible symbol selection as contracts expire and new ones are created.[^1][^2]

<div align="center">⁂</div>

[^1]: noCamel1.py

[^2]: defaults.py

