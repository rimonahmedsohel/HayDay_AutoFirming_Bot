import cv2
import numpy as np
import subprocess
import os
import time
import keyboard
import threading
import math

# Configuration
IMAGES_DIR = "images"
is_running = True

def listen_for_stop():
    global is_running
    print("\n[!] Emergency Stop Activated: Press 'ESC' at any time to kill the bot.")
    keyboard.wait('esc')
    print("\n[!] ESC pressed. Stopping bot...")
    is_running = False

class PlantingBot:
    def __init__(self, shared_templates=None):
        self.screen = None
        self.last_successful_scale = None
        
        if shared_templates is not None:
            self.templates = shared_templates
        else:
            self.templates = {}
            self.load_templates()

    def load_templates(self):
        if not os.path.exists(IMAGES_DIR):
            print(f"Error: Directory '{IMAGES_DIR}' not found!")
            return
        image_files = [f for f in os.listdir(IMAGES_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        for img_file in image_files:
            path = os.path.join(IMAGES_DIR, img_file)
            template = cv2.imread(path, cv2.IMREAD_UNCHANGED)
            if template is not None:
                self.templates[img_file] = template
        print(f"Successfully loaded {len(self.templates)} templates for Planting.")

    def get_adb_screenshot(self, shared_screen=None):
        if shared_screen is not None:
            self.screen = shared_screen
            return True
            
        try:
            pipe = subprocess.Popen(['adb', '-s', '127.0.0.1:7555', 'shell', 'screencap', '-p'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, _ = pipe.communicate()
            stdout = stdout.replace(b'\r\n', b'\n')
            
            if not stdout:
                print("Failed to get screenshot. Reconnecting ADB...")
                subprocess.run(['adb', 'kill-server'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(['adb', 'start-server'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(['adb', 'connect', '127.0.0.1:7555'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return False

            image_array = np.frombuffer(stdout, dtype=np.uint8)
            self.screen = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            return True
        except Exception as e:
            return False

    def adb_click(self, x, y):
        # Add slight variation to clicking
        x_rand = x + np.random.randint(-2, 3)
        y_rand = y + np.random.randint(-2, 3)
        subprocess.run(['adb', '-s', '127.0.0.1:7555', 'shell', 'input', 'tap', str(x_rand), str(y_rand)])
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
        scores = boxes[:, 4]

        area = (x2 - x1 + 1) * (y2 - y1 + 1)
        idxs = np.argsort(scores)[::-1]

        while len(idxs) > 0:
            last = len(idxs) - 1
            i = idxs[0]
            pick.append(i)

            xx1 = np.maximum(x1[i], x1[idxs[1:]])
            yy1 = np.maximum(y1[i], y1[idxs[1:]])
            xx2 = np.minimum(x2[i], x2[idxs[1:]])
            yy2 = np.minimum(y2[i], y2[idxs[1:]])

            w = np.maximum(0, xx2 - xx1 + 1)
            h = np.maximum(0, yy2 - yy1 + 1)

            overlap = (w * h) / area[idxs[1:]]
            idxs = np.delete(idxs, np.concatenate(([0], np.where(overlap > overlapThresh)[0] + 1)))

        return pick

    def find_image(self, template_name, threshold=0.75, fast_mode=False, update_cache=True):
        if self.screen is None:
            return []
            
        template_img = self.templates.get(template_name)
        if template_img is None:
            return []

        screen_gray = cv2.cvtColor(self.screen, cv2.COLOR_BGR2GRAY)
        
        if len(template_img.shape) == 3 and template_img.shape[2] == 4:
            template_img = cv2.cvtColor(template_img, cv2.COLOR_BGRA2BGR)
        template_gray = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)
        
        screen_h, screen_w = screen_gray.shape[:2]
        all_boxes = []
        
        if fast_mode and self.last_successful_scale is not None:
            scales = [self.last_successful_scale]
        else:
            scales = np.linspace(0.6, 1.4, 18)
            
        for scale in scales:
            resized_w = int(template_gray.shape[1] * scale)
            resized_h = int(template_gray.shape[0] * scale)
            
            if resized_w > screen_w or resized_h > screen_h or resized_w < 5 or resized_h < 5:
                continue
                
            resized_template = cv2.resize(template_gray, (resized_w, resized_h))
            res = cv2.matchTemplate(screen_gray, resized_template, cv2.TM_CCOEFF_NORMED)
            loc = np.where(res >= threshold)
            
            if len(loc[0]) > 0 and update_cache:
                self.last_successful_scale = scale
            
            for pt in zip(*loc[::-1]):
                score = res[pt[1]][pt[0]]
                x1, y1 = int(pt[0]), int(pt[1])
                x2, y2 = int(pt[0] + resized_w), int(pt[1] + resized_h)
                all_boxes.append([x1, y1, x2, y2, score])
                
        if not all_boxes:
            return []
            
        boxes_np = np.array(all_boxes)
        picked_indices = self.non_max_suppression(boxes_np)
        
        final_boxes = []
        for i in picked_indices:
            final_boxes.append([int(b) for b in boxes_np[i][:4]])
            
        return final_boxes

    def get_center(self, box):
        x1, y1, x2, y2 = box
        return (x1 + (x2 - x1)//2, y1 + (y2 - y1)//2)

    def adb_swipe(self, x1, y1, x2, y2, duration_ms=500):
        subprocess.run(['adb', '-s', '127.0.0.1:7555', 'shell', 'input', 'swipe', str(x1), str(y1), str(x2), str(y2), str(duration_ms)])
        time.sleep(0.3)

    def exact_planting_sequence(self):
        """
        1. Find empty field.
        2. Click the LAST empty field.
        3. Find wheat seed.
        4. Drag seed to the EXACT empty field clicked.
        5. Continue dragging through all other empty fields.
        """
        # Find all empty fields
        empty_boxes = []
        for template_name in self.templates.keys():
            if "empty_field" in template_name or "empty_slot" in template_name:
                empty_boxes.extend(self.find_image(template_name, threshold=0.85))

        if not empty_boxes:
            return False

        print(f"--> [1] Found {len(empty_boxes)} empty fields.")

        # Sort the boxes from top-left to bottom-right so the "last" is consistent
        empty_boxes.sort(key=lambda b: (b[1], b[0]))
        
        # Click the LAST empty field
        last_field = empty_boxes[-1]
        tapped_x, tapped_y = self.get_center(last_field)
        print(f"--> [2] Clicking the LAST empty field at coordinates: ({tapped_x}, {tapped_y})")
        self.adb_click(tapped_x, tapped_y)
        
        # Wait for the screen to finish panning down
        time.sleep(0.75)

        # 4. Take a FRESH screenshot because the camera panned, meaning all old coordinates are wrong!
        if not self.get_adb_screenshot():
            return False
            
        print("--> [4] Finding relocated empty fields after camera pan...")
        
        # Find the wheat seed FIRST so we have `seed_y`
        seed_boxes = []
        for template_name in self.templates.keys():
            if template_name.startswith("wheat_seed_"):
                seed_boxes.extend(self.find_image(template_name, threshold=0.74, update_cache=False))
                
        # Filter out false positives (e.g., UI elements in the bottom left corner)
        # The true seed menu pops up radially around the tapped dirt field!
        valid_seeds = []
        for box in seed_boxes:
            cx, cy = self.get_center(box)
            dist = math.sqrt((cx - tapped_x)**2 + (cy - tapped_y)**2)
            if dist < 400:  # Seed menu is always close to the tapped field
                valid_seeds.append(box)
                
        if not valid_seeds:
            print("--> [!] Wheat Seed not found near tapped field. Proceeding anyway (user bypass).")
            # Fallback to a hardcoded coordinate if the vision threshold missed it completely to prevent crashing
            seed_x, seed_y = 660, 400
            valid_seeds.append([seed_x, seed_y, seed_x+10, seed_y+10])
            
        # The seed menu pops up horizontally. Wheat is almost always the first (left-most) crop if we are wheating.
        valid_seeds.sort(key=lambda b: b[0])
        seed_x, seed_y = self.get_center(valid_seeds[0])
        print(f"--> [3] Wheat Seed found at ({seed_x}, {seed_y})!")
        
        # Now find the relocated empty fields
        new_empty_boxes = []
        for template_name in self.templates.keys():
            if "empty_field" in template_name or "empty_slot" in template_name:
                new_empty_boxes.extend(self.find_image(template_name, threshold=0.85, fast_mode=True))
                
        if not new_empty_boxes:
            return False
            
        # 5. Drag the seed to the exact screen coordinates where we originally clicked.
        # The user requested the zigzag circle be centered on the absolute `(tapped_x, tapped_y)` coordinates from Step 2.
        new_centers = [self.get_center(b) for b in new_empty_boxes]
        
        print(f"--> [5] Dragging seed DOWN to the EXACT originally tapped screen coordinates at ({tapped_x}, {tapped_y}) to trigger scroll...")
        
        # We must use `motionevent` instead of `swipe`. 
        # `input swipe` lifts the finger at the end, dropping the seed!
        # And chaining 95 swipes crashes the Android system.
        
        # We build a path that perfectly matches the user's logic:
        # 1. Start at the Seed.
        # 2. Go to the originally tapped raw screen coordinate `(tapped_x, tapped_y)`
        # 3. Do a fast, dense circular zig-zag around this coordinate to trigger the scroll and plant the local area.
        # 4. Stop holding and finish.
        
        lx, ly = tapped_x, tapped_y
        sweep_points = [(lx, ly)]
        
        # Add a dense zig-zag movement INSIDE a 400px circle around the tapped coordinate
        radius = 400
        horizontal_step = 60 # Keep the side-to-side sweeping fast
        vertical_step = 20   # But draw lines much closer together vertically so we don't skip pixels
        
        # We will sweep horizontally, moving line by line from the BOTTOM of the circle to the TOP
        # Step up by `vertical_step` instead of the massive `horizontal_step`
        # Because 400px goes too far down, start the sweep at 100px below the center.
        for dy in range(100, -radius - 1, -vertical_step):
            # Calculate the max horizontal width of the circle at this specific Y height (using Pythagoras)
            dx_max = int(math.sqrt(radius**2 - dy**2))
            
            # The line sweeps from left to right, or right to left
            y_coord = ly + dy
            if (dy // vertical_step) % 2 == 0:
                # Sweep Left to Right
                for dx in range(-dx_max, dx_max + 1, horizontal_step):
                    sweep_points.append((lx + dx, y_coord))
            else:
                # Sweep Right to Left
                for dx in range(dx_max, -dx_max - 1, -horizontal_step):
                    sweep_points.append((lx + dx, y_coord))
                    
        sweep_points.append((lx, ly)) # Return to exact center of the tapped field
            
        # Build the exact `motionevent` shell script
        # 1. Press Down on the Seed
        commands = [f"input motionevent DOWN {seed_x} {seed_y}"]
        # 2. Hold to lift the seed from the menu
        commands.append("sleep 0.4")
        
        # 3. Drag through our real exact field coordinates
        for px, py in sweep_points:
            commands.append(f"input motionevent MOVE {px} {py}")
            # Add a microscopic sleep to let the game engine render the touch move
            commands.append("sleep 0.05")
            
        # 4. Lift finger
        commands.append(f"input motionevent UP {sweep_points[-1][0]} {sweep_points[-1][1]}")
        
        # Execute the sequence as one shell command
        full_command = " ; ".join(commands)
        subprocess.run(['adb', '-s', '127.0.0.1:7555', 'shell', full_command])
                
        print("--> Planting batch complete!\n")
        time.sleep(1.0)
        return True

    def run_loop(self):
        print("Bot online. Starting planting sequence monitor...")
        
        while is_running:
            if not self.get_adb_screenshot():
                time.sleep(2)
                continue
                
            if not self.exact_planting_sequence():
                print("--> [IDLE] No empty fields found. Waiting...")
                time.sleep(2)

def main():
    stop_thread = threading.Thread(target=listen_for_stop, daemon=True)
    stop_thread.start()
    
    bot = PlantingBot()
    bot.run_loop()

if __name__ == "__main__":
    main()
