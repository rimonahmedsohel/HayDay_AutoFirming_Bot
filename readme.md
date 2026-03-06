# HayDay Auto-Farming Bot Logic & Flow

This bot is designed to automate the complete farming cycle (Planting -> Selling -> Harvesting) in Hay Day using Python, OpenCV, and ADB. It uses scale-invariant template matching to dynamically locate UI elements regardless of the screen's zoom level.

---

## 🔁 Master Sequence (The Normal Flow)

The core bot loop runs infinitely (until `ESC` is pressed). A single, flawless cycle looks exactly like this:

1. **[STEP 1] Plant**: The bot searches for grown wheat fields first to find the origin, then clicks the empty fields in a zigzag pattern to plant wheat.
2. **[STEP 2] Wait for Growth**: If seeds were successfully planted in Step 1, the bot waits for precisely 125 seconds for the wheat to grow.
3. **[STEP 3] Harvest 1**: The bot locates grown wheat, clicks it to summon the sickle menu, grabs the sickle, and drags it in a zigzag pattern across the fields.
4. **[STEP 4] Plant 2**: Immediately plants the newly harvested fields with wheat.
5. **[STEP 5] Sell**: Opens the shop to sell the newly harvested wheat.
    * *Pre-Collection:* Upon opening the shop, it first checks for previously sold items (`sold_product_1.png`). If found, it collects the money from those slots *before* trying to sell anything new.
    * *Selling Loop:* It finds empty shop slots, lists wheat at maximum price, occasionally watches ads (for specific slots), and puts them on sale.
6. **[STEP 6] Wait Remaining Growth**: Calculates how much time elapsed since Step 4 (Plant 2). It waits whatever time is left of the originally required 125 seconds.
7. **[STEP 7] Harvest 2**: Harvests the second batch of crops.
8. **[STEP 8] Collect Money**: Opens the roadside shop and clicks all the specific slots where it remembers placing items for sale during Step 5.

*After Step 8, the cycle completes and begins again from Step 1.*

---

## 🚦 Exceptional Flows

Sometimes things do not go perfectly. The bot constantly monitors the screen for edge cases and exceptions.

### 1. The "Silo Full" Exception
If the Silo is full, the bot cannot harvest crops, which breaks the normal loop. To prevent a deadlock, the bot actively checks for the `silo_full.png` popup immediately after dragging the sickle.

* **If detected during Harvest 1 (Step 3)**:
  * The bot clicks the "Cross" to dismiss the popup.
  * It immediately diverts to the **Sell Flow**:
    * Sells current inventory.
    * Waits 30 seconds for items to be purchased by other players.
    * Collects the money.
    * Plants new crops.
    * Waits 125 seconds for them to grow.
    * Harvests the crops (now that the silo has room).
  * The cycle ends and restarts from the top.

* **If detected during Harvest 2 (Step 7)**:
  * Over 125s have passed since it last sold items in Step 5, so it diverts.
  * The bot clicks the "Cross" to dismiss the popup.
  * Collects money from previously listed items to clear shop space.
  * Sells current inventory.
  * Waits 30 seconds for items to be purchased by other players.
  * Collects money again from the newly listed items.
  * The cycle ends and restarts from the top.

### 2. The 3-Strike Cycle Failure
If a cycle completely fails—meaning *nothing* was planted, *nothing* was harvested, and *nothing* was sold—it will be marked as a failed cycle.
* If **3 consecutive cycles** fail completely, the bot assumes there is a critical state error (e.g., UI glitch, stuck camera, network error).
* It instantly triggers the **Crash Handler recovery sequence** to force-close and reboot the game.

### 3. Application Crashes
Every single action (Planting, Harvesting, Selling, and Waiting) is wrapped in crash detection. If the ADB `dumpsys` command detects that `com.supercell.hayday` is no longer the active foreground application, the bot halts execution and begins recovery.

---

## 🛠 Crash Recovery Sequence
If the Crash Handler is triggered (via game crash OR 3-strike failure), the following happens:
1. **Force Stop**: Kills any lingering `com.supercell.hayday` background processes via ADB.
2. **Launch Game**: Sends an Android Intent via ADB shell to boot the app.
3. **Monitor Loading**: Watches for `loadScreen.png`. If the game gets stuck on the loading screen for more than 35 seconds, it kills it and tries again (max 3 retries).
4. **Post-Load Verification**:
   * Waits and clicks the crow dialog (`crow.png`) to dismiss the daily news popup.
   * Swipes the camera right by 400 pixels.
   * Executes `zoom.py` (via background `minitouch` binary injection) to pinch-to-zoom completely out, ensuring maximum visibility for OpenCV.
   * Locates the lowest available empty field on the farm and clicks it. This forces the Hay Day camera to pan downwards and perfectly align the farm into the bot's expected viewing angle.
5. **Resume**: The Crash Handler yields back to `start.py` and the main loop continues exactly where it left off.
