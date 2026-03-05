import pyautogui
import pygetwindow as gw
import time

def main():
    print("[TEST CTRL+SCROLL] Looking for MuMuPlayer window...")
    windows = gw.getWindowsWithTitle('MuMuPlayer')
    
    if not windows:
        print("[TEST CTRL+SCROLL] Could not find any MuMuPlayer window! Please open it.")
        return
        
    # Windows sends minimized windows to (-32000, -32000). We must restore them first to get their real size.
    for w in windows:
        if w.left < -30000:
            try:
                w.restore()
                time.sleep(0.5)
            except:
                pass

    # Now filter out the tiny launcher/toolbar windows (like 160x28)
    valid_windows = [w for w in windows if w.width > 300 and w.height > 300]
    
    if not valid_windows:
        print("[TEST CTRL+SCROLL] Could not find a visible emulator window! Please make sure the main MuMu Player is open.")
        return

    # Find the largest MuMuPlayer window (the actual emulator)
    best_win = max(valid_windows, key=lambda w: w.width * w.height)
    print(f"[TEST CTRL+SCROLL] Found emulator window: {best_win.title} ({best_win.width}x{best_win.height})")

    # Save original mouse position
    original_pos = pyautogui.position()

    try:
        # Give focus to the window
        print("[TEST CTRL+SCROLL] Activating window...")
        best_win.activate()
    except Exception as e:
        print(f"[TEST CTRL+SCROLL] Could not activate window (it might already be active): {e}")

    time.sleep(1.0) # Wait for window to come forward

    # Move mouse to the center of the emulator
    center_x = best_win.left + (best_win.width // 2)
    center_y = best_win.top + (best_win.height // 2)
    
    print(f"[TEST CTRL+SCROLL] Moving mouse to center ({center_x}, {center_y}) and clicking...")
    pyautogui.moveTo(center_x, center_y)
    
    # We must click once inside the emulator to ensure the Android OS inside it has focus!
    pyautogui.click()
    time.sleep(0.5)

    print("[TEST CTRL+SCROLL] Holding 'ctrl' and scrolling DOWN...")
    # The scroll amount varies by OS/driver. In pyautogui Windows, negative is down, positive is up.
    # Usually, a single "tick" is 100 or 120. We will do a few large scrolls.
    pyautogui.keyDown('ctrl')
    time.sleep(0.1)
    
    for _ in range(3):
        pyautogui.scroll(-500) # Scroll down
        time.sleep(0.2)
        
    pyautogui.keyUp('ctrl')

    print("[TEST CTRL+SCROLL] Done! Restoring mouse position...")
    time.sleep(0.5)
    pyautogui.moveTo(original_pos[0], original_pos[1])

if __name__ == "__main__":
    main()
