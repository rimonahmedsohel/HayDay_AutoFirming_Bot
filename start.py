import time
import keyboard
import threading
from planting import PlantingBot
from harvesting import HarvestingBot
from sellingCrops import SellingBot

is_running = True

def listen_for_stop():
    global is_running
    print("\n[!] Emergency Stop Activated: Press 'ESC' at any time to kill the bot.")
    keyboard.wait('esc')
    print("\n[!] ESC pressed. Stopping bot...")
    is_running = False

def run_master_loop():
    print("Bot online. Starting master sequence...")
    
    # Initialize the first bot, which loads the image templates from the disk
    print("Loading image templates into memory...")
    plant_bot = PlantingBot()
    
    # Share those already-loaded templates with the second bot to avoid loading them twice
    harvest_bot = HarvestingBot(shared_templates=plant_bot.templates)
    sell_bot = SellingBot(shared_templates=plant_bot.templates)
    
    cycle_count = 0

    while is_running:
        cycle_count += 1
        
        is_sell_cycle = (cycle_count % 2 == 0) # Every 2nd cycle is a selling cycle

        print("\n========================================")
        print(f"         STARTING NEW CYCLE #{cycle_count}")
        print("========================================")
        if is_sell_cycle:
            print("Cycle Type: Plant -> Sell (No Wait)")
        else:
            print("Cycle Type: Plant -> Wait -> Harvest")
        
        # Take ONE screenshot for the entire master cycle
        if not plant_bot.get_adb_screenshot():
            print("Failed to capture screenshot. Retrying in 2s...")
            time.sleep(2)
            continue
            
        shared_screen = plant_bot.screen
        
        # ---------------------------------------------------------
        # PHASE 1: PLANTING (Try up to 3 times)
        # ---------------------------------------------------------
        print("\n--- PHASE 1: PLANTING ---")
        
        did_plant = False
        planting_attempts = 0
        
        while planting_attempts < 3 and not did_plant and is_running:
            planting_attempts += 1
            print(f"Planting Attempt {planting_attempts} of 3...")
            
            # Use the shared screen for the first attempt, take new ones for retries
            if planting_attempts > 1:
                if not plant_bot.get_adb_screenshot():
                    print("Failed to capture screenshot for Planting. Retrying...")
                    time.sleep(2)
                    continue
                shared_screen = plant_bot.screen # Update shared screen

            did_plant = plant_bot.exact_planting_sequence()
            
            if did_plant:
                print("Planting phase complete.")
            else:
                print("There is no empty field to plant. Retrying...")
                if planting_attempts < 3:
                     time.sleep(2) # Short delay before retry
        
        if not is_running: break

        # branching based on cycle type 
        if not is_sell_cycle:
            # ---------------------------------------------------------
            # MANDATORY GROWTH DELAY (Only for harvest cycles)
            # ---------------------------------------------------------
            if did_plant:
                print("\n--- WAITING FOR CROPS TO GROW ---")
                print("Waiting 2 minutes 15 seconds (135 sec) for wheat to mature...")
                
                # Print a status update every 5 seconds so the terminal doesn't look frozen
                wait_time = 135
                while wait_time > 0 and is_running:
                    print(f"Time remaining: {wait_time} seconds...")
                    sleep_duration = min(5, wait_time)
                    time.sleep(sleep_duration)
                    wait_time -= sleep_duration
                    
            if not is_running: break
            
            # ---------------------------------------------------------
            # PHASE 2: HARVESTING (Try up to 3 times)
            # ---------------------------------------------------------
            print("\n--- PHASE 2: HARVESTING ---")
            print("Looking for harvest crops...")
            
            did_harvest = False
            harvesting_attempts = 0
            
            while harvesting_attempts < 3 and not did_harvest and is_running:
                harvesting_attempts += 1
                print(f"Harvesting Attempt {harvesting_attempts} of 3...")
                
                # Take a fresh screenshot for harvesting since we waited 2 mins
                # OR if it's a retry
                if not harvest_bot.get_adb_screenshot():
                    print("Failed to capture screenshot for Harvesting. Retrying...")
                    time.sleep(2)
                    continue
                
                did_harvest = harvest_bot.exact_harvesting_sequence()
                
                if did_harvest:
                    print("Harvesting phase complete.")
                else:
                    print("No crops to harvest. Retrying...")
                    if harvesting_attempts < 3:
                         time.sleep(2)
                
            if not is_running: break
            
        else:
            # ---------------------------------------------------------
            # PHASE 3: SELLING (Immediate, no wait)
            # ---------------------------------------------------------
            print("\n--- PHASE 3: SELLING ---")
            
            # Take a fresh screenshot for selling 
            if sell_bot.get_adb_screenshot():
                did_sell = sell_bot.exact_selling_sequence()
                
                if did_sell:
                    print("Selling phase triggered: Shop button clicked.")
                else:
                    print("No shop button found to click.")
            else:
                 print("Failed to capture screenshot for Selling.")
                 
            if not is_running: break
        
        # ---------------------------------------------------------
        # CYCLE COMPLETE - WAIT
        # ---------------------------------------------------------
        print("\n--- CYCLE COMPLETE. Waiting 3 seconds before restarting... ---")
        time.sleep(3.0)

def main():
    stop_thread = threading.Thread(target=listen_for_stop, daemon=True)
    stop_thread.start()
    
    run_master_loop()

if __name__ == "__main__":
    main()
