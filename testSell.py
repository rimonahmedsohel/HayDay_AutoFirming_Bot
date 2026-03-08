from sellingCrops import SellingBot
import time
import sys
import subprocess
from adb_path import get_adb_path, CREATE_NO_WINDOW

ADB = get_adb_path()

def connect_adb():
    """Connect ADB to the MuMu emulator."""
    print("Connecting ADB to emulator...")
    subprocess.run([ADB, 'start-server'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW)
    result = subprocess.run([ADB, 'connect', '127.0.0.1:7555'], capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)
    print(f"  ADB: {result.stdout.strip()}")
    time.sleep(1)

def test_sell():
    print("=" * 50)
    print("  SELLING TEST — Sell + Wait 70min + Collect")
    print("=" * 50)
    
    # Connect ADB first
    connect_adb()
    
    print("\nInitializing Selling Bot...")
    bot = SellingBot()
    
    # ---- STEP 1: Sell ----
    print("\n--- STEP 1: SELLING ---")
    if not bot.get_adb_screenshot():
        print("Failed to capture screenshot!")
        return
    
    did_sell = bot.exact_selling_sequence()
    if did_sell:
        print(f"\nSelling done! Remembered {len(bot.sold_slot_positions)} sold slot position(s):")
        for i, pos in enumerate(bot.sold_slot_positions):
            print(f"  Slot #{i+1}: ({pos[0]}, {pos[1]})")
    else:
        print("\nNo items were sold. Nothing to collect later.")
        print("Test complete (nothing to wait for).")
        return
    
    # ---- STEP 2: Wait 70 seconds ----
    wait_seconds = 70
    print(f"\n--- STEP 2: WAITING {wait_seconds} SECONDS ---")
    print("(Press Ctrl+C to skip the wait and collect immediately)\n")
    
    try:
        remaining = wait_seconds
        while remaining > 0:
            mins = remaining // 60
            secs = remaining % 60
            print(f"  Time remaining: {mins}m {secs}s ...", end='\r')
            time.sleep(5)
            remaining -= 5
        print()  # newline after countdown
    except KeyboardInterrupt:
        print("\n\nWait skipped by user! Proceeding to collect...\n")
    
    # ---- STEP 3: Collect Money ----
    print("\n--- STEP 3: COLLECTING MONEY ---")
    print("(Using visual detection — only clicks items that show as SOLD)\n")
    
    did_collect = bot.collect_money()
    if did_collect:
        print("\nCollection complete! Money collected successfully.")
    else:
        print("\nNo sold items detected. Nothing was collected.")
    
    print("\n" + "=" * 50)
    print("  TEST COMPLETE")
    print("=" * 50)

if __name__ == "__main__":
    try:
        test_sell()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
