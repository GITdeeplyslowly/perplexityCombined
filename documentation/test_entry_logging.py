"""
Test to demonstrate the new entry evaluation logging.
Shows why the strategy is not taking trades.
"""

print("=" * 80)
print("ENTRY EVALUATION LOGGING - NEW FEATURES")
print("=" * 80)

print("\n📊 WHAT'S NEW:")
print("   1. Entry signal evaluation logs every 30 seconds")
print("   2. Shows which indicators are enabled")
print("   3. Shows which indicators failed and why")
print("   4. Shows actual values (price vs thresholds)")
print("   5. 'Entry blocked' logs show session/time/green tick restrictions")

print("\n🔍 EXAMPLE LOG OUTPUT:")
print("-" * 80)

print("""
11:29:13 [INFO] live.trader: [HEARTBEAT] Callback mode - 100 cycles, position: False, price: ₹174.05

11:29:43 [INFO] core.liveStrategy: 📊 ENTRY EVALUATION @ ₹170.55: Enabled checks: EMA Crossover, VWAP, MACD
11:29:43 [INFO] core.liveStrategy:    ❌ Entry REJECTED - Failed: EMA: fast(18.5) ≤ slow(19.2); MACD: not bullish

11:30:13 [INFO] live.trader: [HEARTBEAT] Callback mode - 700 cycles, position: False, price: ₹165.80

11:30:43 [INFO] core.liveStrategy: 📊 ENTRY EVALUATION @ ₹162.85: Enabled checks: EMA Crossover, VWAP, MACD
11:30:43 [INFO] core.liveStrategy:    ❌ Entry REJECTED - Failed: VWAP: price(162.85) ≤ vwap(165.30); MACD: histogram not positive

11:31:13 [INFO] live.trader: [HEARTBEAT] Callback mode - 1300 cycles, position: False, price: ₹162.50

11:31:43 [INFO] core.liveStrategy: 🚫 ENTRY BLOCKED (#300): Need 3 green ticks, have 1, NIFTY20OCT2525300CE @ ₹161.10

11:32:13 [INFO] live.trader: [HEARTBEAT] Callback mode - 1800 cycles, position: False, price: ₹161.75

11:32:43 [INFO] core.liveStrategy: ✅ ENTRY SIGNAL @ ₹160.70: All checks passed (EMA Crossover, VWAP, MACD)
11:32:43 [INFO] live.trader: 📈 BUY signal generated @ ₹160.70
11:32:43 [INFO] core.position_manager: Position opened: lot_size=75, entry=₹160.70
""")

print("-" * 80)

print("\n📋 LOGGING FREQUENCY:")
print("   • Entry evaluation: Every 300 ticks (~30 seconds at 10 ticks/sec)")
print("   • Entry blocked: First occurrence, then every 300 blocks")
print("   • Entry allowed: ALWAYS logged (rare event)")
print("   • Heartbeat: Every 100 cycles (~10 seconds)")

print("\n🎯 HOW TO USE:")
print("   1. Start live forward test from GUI")
print("   2. Watch the logs for entry evaluation messages")
print("   3. Look for '📊 ENTRY EVALUATION' to see indicator status")
print("   4. Look for '🚫 ENTRY BLOCKED' to see session/time restrictions")
print("   5. Look for '✅ ENTRY SIGNAL' when conditions align")

print("\n💡 TROUBLESHOOTING:")
print("   • If you see 'EMA: not calculated yet' → Need more ticks for warmup")
print("   • If you see 'Need X green ticks' → Waiting for consecutive green ticks")
print("   • If you see 'Not in trading session' → Outside 09:15-15:30")
print("   • If you see 'Before buffer start' → In start buffer period")
print("   • If you see 'After buffer end' → In end buffer period")
print("   • If you see 'Exceeded max trades' → Hit daily trade limit")

print("\n" + "=" * 80)
print("CHANGES APPLIED:")
print("=" * 80)
print("✅ liveStrategy.py: Added detailed entry_signal() logging")
print("✅ logger.py: Changed entry_blocked frequency (1000 → 300)")
print("✅ Shows indicator values and reasons for rejection")
print("✅ Logs coordinated with heartbeat (every ~30 seconds)")
print("=" * 80)
