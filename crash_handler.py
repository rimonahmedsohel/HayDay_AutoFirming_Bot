import cv2
import numpy as np
import subprocess
import os
import time
from adb_path import get_adb_path, get_images_dir, CREATE_NO_WINDOW

# Configuration
ADB = get_adb_path()
IMAGES_DIR = get_images_dir()


class CrashHandler:
    def __init__(self, shared_templates=None):
        self.screen = None
        self.last_successful_scale = None

        if shared_templates is not None:
            self.templates = shared_templates
        else:
            self.templates = {}
            self.load_templates()

    def load_templates(self):
        for filename in os.listdir(IMAGES_DIR):
            if filename.endswith('.png'):
                path = os.path.join(IMAGES_DIR, filename)
                self.templates[filename] = cv2.imread(path, cv2.IMREAD_UNCHANGED)

    def get_adb_screenshot(self):
        try:
            pipe = subprocess.Popen(
                [ADB, '-s', '127.0.0.1:7555', 'shell', 'screencap', '-p'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                creationflags=CREATE_NO_WINDOW
            )
            stdout, _ = pipe.communicate()
            stdout = stdout.replace(b'\r\n', b'\n')

            if not stdout:
                print("[CRASH] Failed to get screenshot. Reconnecting ADB...")
                subprocess.run([ADB, 'kill-server'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW)
                subprocess.run([ADB, 'start-server'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW)
                subprocess.run([ADB, 'connect', '127.0.0.1:7555'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW)
                return False

            image_array = np.frombuffer(stdout, dtype=np.uint8)
            self.screen = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            return True
        except Exception as e:
            print(f"[CRASH] Screenshot error: {e}")
            return False

    def adb_click(self, x, y):
        x_rand = int(x + np.random.randint(-2, 3))
        y_rand = int(y + np.random.randint(-2, 3))
        subprocess.run([ADB, '-s', '127.0.0.1:7555', 'shell', 'input', 'tap', str(x_rand), str(y_rand)], creationflags=CREATE_NO_WINDOW)
        time.sleep(0.3)

    def non_max_suppression(self, boxes, overlapThresh=0.3):
        if len(boxes) == 0:
            return []

        if boxes.dtype.kind == "i":
            boxes = boxes.astype("float")

        pick = []
        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 2]
        y2 = boxes[:, 3]

        area = (x2 - x1 + 1) * (y2 - y1 + 1)

        if boxes.shape[1] > 4:
            idxs = np.argsort(boxes[:, 4])
        else:
            idxs = np.argsort(y2)

        while len(idxs) > 0:
            last = len(idxs) - 1
            i = idxs[last]
            pick.append(i)

            xx1 = np.maximum(x1[i], x1[idxs[:last]])
            yy1 = np.maximum(y1[i], y1[idxs[:last]])
            xx2 = np.minimum(x2[i], x2[idxs[:last]])
            yy2 = np.minimum(y2[i], y2[idxs[:last]])

            w = np.maximum(0, xx2 - xx1 + 1)
            h = np.maximum(0, yy2 - yy1 + 1)

            overlap = (w * h) / area[idxs[:last]]
            idxs = np.delete(idxs, np.concatenate(([last], np.where(overlap > overlapThresh)[0])))

        return pick

    def find_image(self, template_name, threshold=0.75, fast_mode=False, update_cache=True):
        if self.screen is None:
            return []

        template_img = self.templates.get(template_name)
        if template_img is None:
            return []

        # Use an alpha mask only if the template has 4 channels AND actually contains transparent pixels
        use_mask = False
        if len(template_img.shape) == 3 and template_img.shape[2] == 4:
            alpha_mask = template_img[:, :, 3]
            if np.any(alpha_mask < 255):
                bgr_template = template_img[:, :, :3]
                use_mask = True
            
        screen_gray = cv2.cvtColor(self.screen, cv2.COLOR_BGR2GRAY)

        if len(template_img.shape) == 3 and template_img.shape[2] == 4:
            template_img_no_alpha = cv2.cvtColor(template_img, cv2.COLOR_BGRA2BGR)
        else:
            template_img_no_alpha = template_img
        template_gray = cv2.cvtColor(template_img_no_alpha, cv2.COLOR_BGR2GRAY)

        screen_h, screen_w = screen_gray.shape[:2]
        all_boxes = []

        if fast_mode and self.last_successful_scale is not None:
            scales = [self.last_successful_scale]
        else:
            # Wide scale range to handle both small and large templates
            scales = np.linspace(0.2, 1.4, 25)

        for scale in scales:
            resized_w = int(template_gray.shape[1] * scale)
            resized_h = int(template_gray.shape[0] * scale)

            if resized_w > screen_w or resized_h > screen_h or resized_w < 5 or resized_h < 5:
                continue

            if use_mask:
                resized_bgr = cv2.resize(bgr_template, (resized_w, resized_h))
                resized_mask = cv2.resize(alpha_mask, (resized_w, resized_h))
                res = cv2.matchTemplate(self.screen, resized_bgr, cv2.TM_SQDIFF_NORMED, mask=resized_mask)
                
                # TM_SQDIFF_NORMED: 0 is perfect match. We look for min_val <= 0.15
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
                if min_val <= 0.15:
                    if update_cache:
                        self.last_successful_scale = scale
                    x1, y1 = min_loc
                    # Invert min_val to behave like a positive score for sorting boxes
                    score = 1.0 - min_val
                    all_boxes.append([x1, y1, x1 + resized_w, y1 + resized_h, score])
            else:
                resized_template = cv2.resize(template_gray, (resized_w, resized_h))
                res = cv2.matchTemplate(screen_gray, resized_template, cv2.TM_CCOEFF_NORMED)
                loc = np.where(res >= threshold)

                if len(loc[0]) > 0 and update_cache:
                    self.last_successful_scale = scale

                for pt in zip(*loc[::-1]):
                    score = res[pt[1]][pt[0]]
                    x1, y1 = int(pt[0]), int(pt[1])
                    all_boxes.append([x1, y1, x1 + resized_w, y1 + resized_h, score])

        if not all_boxes:
            return []

        boxes_np = np.array(all_boxes)
        picked_indices = self.non_max_suppression(boxes_np)

        final_boxes = []
        for i in picked_indices:
            final_boxes.append(boxes_np[i].tolist())
            
        final_boxes.sort(key=lambda x: x[4], reverse=True)

        return final_boxes

    def get_center(self, box):
        return int((box[0] + box[2]) // 2), int((box[1] + box[3]) // 2)

    # ----------------------------------------------------------------
    #  Core crash detection & recovery
    # ----------------------------------------------------------------

    def is_crashed(self):
        """
        Detect crash by checking if Hay Day is the foreground app.
        Uses ADB to query the current focused window.
        If Hay Day is NOT the focused app, it means the game crashed.
        """
        print("[CRASH] Checking for crash...")
        try:
            # Check the focused window using dumpsys window displays
            result = subprocess.run(
                [ADB, '-s', '127.0.0.1:7555', 'shell', 'dumpsys', 'window', 'displays'],
                capture_output=True, text=True, creationflags=CREATE_NO_WINDOW
            )
            for line in result.stdout.splitlines():
                if 'mCurrentFocus' in line:
                    if 'com.supercell.hayday' in line:
                        print("[CRASH] No crash detected. Hay Day is running.")
                        return False
            
            print("[CRASH] Crash detected! Hay Day is NOT the active foreground app.")
            return True
        except Exception as e:
            print(f"[CRASH] Error checking foreground app: {e}")
            return False

    def recover(self):
        """
        Reopen Hay Day using ADB package launch command.
        After launching, monitors for loading screen stuck.
        If stuck on loading screen for 20s, force-closes and retries.
        """
        max_retries = 3

        for retry in range(1, max_retries + 1):
            # Force-close any existing Hay Day instance first
            print(f"[CRASH] Recovery attempt {retry}/{max_retries} — force-closing Hay Day...")
            subprocess.run(
                [ADB, '-s', '127.0.0.1:7555', 'shell', 'am', 'force-stop', 'com.supercell.hayday'],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW
            )
            time.sleep(2)
            print(f"[CRASH] Launching Hay Day via ADB...")

            try:
                result = subprocess.run(
                    [ADB, '-s', '127.0.0.1:7555', 'shell', 'monkey', '-p', 'com.supercell.hayday', '-c', 'android.intent.category.LAUNCHER', '1'],
                    capture_output=True, text=True, creationflags=CREATE_NO_WINDOW
                )
                if 'Events injected: 1' not in result.stdout:
                    print(f"[CRASH] Launch command failed: {result.stdout.strip()}")
                    time.sleep(3)
                    continue
            except Exception as e:
                print(f"[CRASH] Error launching Hay Day: {e}")
                time.sleep(3)
                continue

            print("[CRASH] Hay Day launch command sent. Monitoring loading screen...")

            load_start_time = time.time()
            saw_loading_screen = False
            stuck = False

            while True:
                elapsed = time.time() - load_start_time
                if elapsed > 35:
                    if saw_loading_screen:
                        print("[CRASH] Stuck on loading screen for >35s! Force-closing...")
                    else:
                        print("[CRASH] Never saw loading screen, and game didn't load in 35s. Force-closing...")
                    stuck = True
                    break

                time.sleep(2)
                is_loading = self._is_on_loading_screen()

                if is_loading:
                    if not saw_loading_screen:
                        print(f"[CRASH] Loading screen detected at {elapsed:.1f}s. Waiting for it to clear...")
                        saw_loading_screen = True
                else:
                    if saw_loading_screen:
                        print(f"[CRASH] Loading screen cleared at {elapsed:.1f}s. Game loaded successfully!")
                        break
                    elif elapsed > 20:
                        print("[CRASH] Never saw loading screen, but 20s elapsed. Assuming game loaded quickly.")
                        break

            if stuck:
                subprocess.run(
                    [ADB, '-s', '127.0.0.1:7555', 'shell', 'am', 'force-stop', 'com.supercell.hayday'],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW
                )
                time.sleep(3)
                continue  # Retry the launch
                
            # VERIFY HAY DAY IS ACTUALLY RUNNING (didn't crash during load)
            print("[CRASH] Verifying Hay Day is the active app...")
            if self.is_crashed():
                print("[CRASH] Game crashed during load! Retrying launch...")
                time.sleep(2)
                continue

            # Wait up to 10 seconds for the crow popup after loading
            print("[CRASH] Waiting up to 10 seconds for crow popup...")
            crow_found = False
            for _ in range(10):
                if self.get_adb_screenshot():
                    # threshold=0.65 works for the large crow.png (best match ~0.67)
                    crow_matches = self.find_image("crow.png", threshold=0.65)
                    if crow_matches:
                        cx, cy = self.get_center(crow_matches[0])
                        print(f"[CRASH] Crow detected at ({cx}, {cy}). Waiting 3 seconds before clicking...")
                        time.sleep(3)
                        print("[CRASH] Clicking exact to dismiss crow...")
                        subprocess.run([ADB, '-s', '127.0.0.1:7555', 'shell', 'input', 'tap', str(cx), str(cy)], creationflags=CREATE_NO_WINDOW)
                        crow_found = True
                        time.sleep(2)
                        break
                time.sleep(1)
            
            if not crow_found:
                print("[CRASH] Crow popup skipped (not found within 10s).")

            # Wait 3 seconds after crow functionality
            print("[CRASH] Waiting 3 seconds...")
            time.sleep(3)

            # Always pan top-to-bottom by 200px
            print("[CRASH] Panning top-to-bottom by 200px...")
            subprocess.run([ADB, '-s', '127.0.0.1:7555', 'shell', 'input', 'swipe', '500', '300', '500', '500', '500'], creationflags=CREATE_NO_WINDOW)

            # Wait 3 seconds
            print("[CRASH] Waiting 3 seconds...")
            time.sleep(3)

            # Move screen left to right 300px
            print("[CRASH] Panning screen left to right by 300px...")
            subprocess.run([ADB, '-s', '127.0.0.1:7555', 'shell', 'input', 'swipe', '400', '250', '700', '250', '500'], creationflags=CREATE_NO_WINDOW)
            
            print("[CRASH] Waiting 2 seconds after panning...")
            time.sleep(2)

            # Zoom out
            print("[CRASH] Zooming out screen (using zoom.py)...")
            try:
                from zoom import zoom_out
                zoom_out(0.65)
                time.sleep(1)
            except Exception as e:
                print(f"[CRASH] Error during zoom out: {e}")

            print("[CRASH] Looking for an empty field to align the farm view...")
            # We must take a fresh screenshot since we just loaded the game and zoomed out
            if self.get_adb_screenshot():
                empty_boxes = []
                for template_name in self.templates.keys():
                    if "empty_field" in template_name or "empty_slot" in template_name:
                        empty_boxes.extend(self.find_image(template_name, threshold=0.85))
                
                if empty_boxes:
                    print(f"[CRASH] Found {len(empty_boxes)} empty fields.")
                    # Sort top-left to bottom-right to get the "last" field, just like planting phase
                    empty_boxes.sort(key=lambda b: (b[1], b[0]))
                    last_field = empty_boxes[-1]
                    
                    # Instead of getting the exact center of the field, we get the center 
                    # and then click further down (or click the exact center, since planting clicks the exact center)
                    # The user requested "click lower of the empty field like in planting phase doing".
                    # In planting.py: tapped_x, tapped_y = self.get_center(last_field) -> self.adb_click(tapped_x, tapped_y)
                    # Planting actually clicks exactly on the center of the field to trigger the popup, 
                    # which pans the camera automatically down to show the seed menu above the click.
                    tapped_x, tapped_y = self.get_center(last_field)
                    
                    print(f"[CRASH] Clicking the last empty field at ({tapped_x}, {tapped_y}) to align the view...")
                    self.adb_click(tapped_x, tapped_y)
                else:
                    print("[CRASH] No empty fields found to test click on! Trying fallback lower-center tap...")
                    self.adb_click(450, 600)
            else:
                self.adb_click(450, 600)

            time.sleep(1)

            print("[CRASH] Recovery complete. Resuming bot operations.")
            return True

        print(f"[CRASH] Recovery FAILED after {max_retries} attempts.")
        return False

    def _is_on_loading_screen(self):
        """Check if the game is currently showing the loading screen."""
        if not self.get_adb_screenshot():
            return False
        matches = self.find_image("loadScreen.png", threshold=0.70)
        return len(matches) > 0

    def check_and_recover(self):
        """
        Main public API.
        Checks if the game has crashed. If yes, attempts recovery.
        Returns True if a crash was detected and recovered.
        Returns False if no crash was detected (game is fine).
        """
        if self.is_crashed():
            return self.recover()
        return False
