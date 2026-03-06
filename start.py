import time
import keyboard
import threading
from planting import PlantingBot
from harvesting import HarvestingBot
from sellingCrops import SellingBot
from crash_handler import CrashHandler

is_running = True

def listen_for_stop():
    global is_running
    print("\n[!] Emergency Stop Activated: Press 'ESC' at any time to kill the bot.")
    keyboard.wait('f5')
    print("\n[!] ESC pressed. Stopping bot...")
    is_running = False

def do_planting(plant_bot):
    """Try planting up to 3 times. Returns True if planting succeeded."""
    print("\n--- PLANTING PHASE ---")
    for attempt in range(1, 4):
        if not is_running: return False
        print(f"Planting Attempt {attempt} of 3...")
        if attempt > 1:
            if not plant_bot.get_adb_screenshot():
                print("Failed to capture screenshot for Planting. Retrying...")
                time.sleep(2)
                continue
        did_plant = plant_bot.exact_planting_sequence()
        if did_plant:
            print("Planting phase complete.")
            return True
        else:
            print("There is no empty field to plant. Retrying...")
            if attempt < 3:
                time.sleep(2)
    return False

def do_harvesting(harvest_bot):
    """Try harvesting up to 3 times. Returns True if harvesting succeeded."""
    print("\n--- HARVESTING PHASE ---")
    for attempt in range(1, 4):
        if not is_running: return False
        print(f"Harvesting Attempt {attempt} of 3...")
        if not harvest_bot.get_adb_screenshot():
            print("Failed to capture screenshot for Harvesting. Retrying...")
            time.sleep(2)
            continue
        did_harvest = harvest_bot.exact_harvesting_sequence()
        if did_harvest:
            print("Harvesting phase complete.")
            return True
        else:
            print("No crops to harvest. Retrying...")
            if attempt < 3:
                time.sleep(2)
    return False

def do_selling(sell_bot):
    """Run the selling sequence."""
    print("\n--- SELLING PHASE ---")
    if sell_bot.get_adb_screenshot():
        did_sell = sell_bot.exact_selling_sequence()
        if did_sell:
            print("Selling phase complete.")
        else:
            print("No items sold.")
        return did_sell
    else:
        print("Failed to capture screenshot for Selling.")
        return False

def do_collect_money(sell_bot):
    """Collect money from sold products."""
    print("\n--- COLLECT MONEY PHASE ---")
    did_collect = sell_bot.collect_money()
    if did_collect:
        print("Money collected!")
    else:
        print("No money to collect.")
    return did_collect

def wait_for_growth(seconds, crash_handler=None):
    """Wait for crops to grow, printing status updates. Checks for crashes every 30s."""
    print(f"\n--- WAITING FOR CROPS TO GROW ({seconds}s) ---")
    remaining = seconds
    time_since_crash_check = 0
    while remaining > 0 and is_running:
        print(f"Time remaining: {remaining} seconds...")
        sleep_duration = min(5, remaining)
        time.sleep(sleep_duration)
        remaining -= sleep_duration
        time_since_crash_check += sleep_duration

        # Check for crash every ~30 seconds during the wait
        if crash_handler and time_since_crash_check >= 30:
            time_since_crash_check = 0
            if crash_handler.check_and_recover():
                print("[CRASH] Recovered during growth wait. Continuing wait...")

def run_master_loop():
    print("Bot online. Starting master sequence...")
    
    print("Loading image templates into memory...")
    plant_bot = PlantingBot()
    harvest_bot = HarvestingBot(shared_templates=plant_bot.templates)
    sell_bot = SellingBot(shared_templates=plant_bot.templates)
    crash_handler = CrashHandler(shared_templates=plant_bot.templates)
    
    cycle_count = 0
    consecutive_failures = 0

    while is_running:
        cycle_count += 1
        
        print("\n========================================")
        print(f"         CYCLE #{cycle_count}")
        print("========================================")
        
        cycle_success = False

        # Sequence: Plant → Wait → Harvest → Plant → Sell → Wait → Harvest → Collect Money
        
        # ---- STEP 1: Plant ----
        print("\n[STEP 1] Plant")
        planted1 = False
        if not plant_bot.get_adb_screenshot():
            print("Failed to capture screenshot. Retrying in 2s...")
            time.sleep(2)
            if crash_handler.check_and_recover(): continue
            continue
        
        planted1 = do_planting(plant_bot)
        if planted1:
            cycle_success = True
        else:
            if crash_handler.check_and_recover(): continue
        if not is_running: break
        
        # ---- STEP 2: Wait (if planted) ----
        if planted1:
            print("\n[STEP 2] Wait for crops to grow (135s)")
            wait_for_growth(135, crash_handler)
        else:
            print("\n[STEP 2] Skipping wait — nothing was planted.")
        if not is_running: break

        # ---- STEP 3: Harvest ----
        print("\n[STEP 3] Harvest")
        if not do_harvesting(harvest_bot):
            if crash_handler.check_and_recover(): continue
        else:
            cycle_success = True
        if not is_running: break

        # ---- STEP 4: Plant ----
        print("\n[STEP 4] Plant")
        planted2 = False
        if not plant_bot.get_adb_screenshot():
            print("Failed to capture screenshot. Retrying in 2s...")
            time.sleep(2)
            if crash_handler.check_and_recover(): continue
            continue

        planted2 = do_planting(plant_bot)
        if planted2:
            cycle_success = True
        else:
            if crash_handler.check_and_recover(): continue
        if not is_running: break

        # ---- STEP 5: Sell ----
        print("\n[STEP 5] Sell")
        if not do_selling(sell_bot):
            if crash_handler.check_and_recover(): continue
        else:
            cycle_success = True
        if not is_running: break

        # ---- STEP 6: Wait (if planted) ----
        if planted2:
            print("\n[STEP 6] Wait for crops to grow (135s)")
            wait_for_growth(135, crash_handler)
        else:
            print("\n[STEP 6] Skipping wait — nothing was planted.")
        if not is_running: break

        # ---- STEP 7: Harvest ----
        print("\n[STEP 7] Harvest")
        if not do_harvesting(harvest_bot):
            if crash_handler.check_and_recover(): continue
        else:
            cycle_success = True
        if not is_running: break

        # ---- STEP 8: Collect Money ----
        print("\n[STEP 8] Collect Money")
        if do_collect_money(sell_bot):
            cycle_success = True
        else:
            if crash_handler.check_and_recover(): continue
        if not is_running: break

        # Failure Handling
        if not cycle_success:
            consecutive_failures += 1
            print(f"\n[!] Entire cycle failed! ({consecutive_failures}/3 consecutive failures)")
            if consecutive_failures >= 3:
                print("\n[CRASH] Cycle failed 3 times in a row! Forcing recovery...")
                crash_handler.recover()
                consecutive_failures = 0
        else:
            consecutive_failures = 0
            
        print("\n--- CYCLE COMPLETE. ---")


def main():
    stop_thread = threading.Thread(target=listen_for_stop, daemon=True)
    stop_thread.start()
    
    run_master_loop()

if __name__ == "__main__":
    main()
