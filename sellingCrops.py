import cv2
import numpy as np
import subprocess
import os
import time

# Configuration
IMAGES_DIR = "images"

class SellingBot:
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
        print(f"Successfully loaded {len(self.templates)} templates for Selling.")

    def get_adb_screenshot(self, shared_screen=None):
        if shared_screen is not None:
            self.screen = shared_screen
            return True
            
        try:
            pipe = subprocess.Popen(['adb', '-s', '127.0.0.1:7555', 'shell', 'screencap', '-p'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                stdout, _ = pipe.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                pipe.kill()
                print("--> [ADB] Screenshot timed out! Reconnecting...")
                subprocess.run(['adb', 'kill-server'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(['adb', 'start-server'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(['adb', 'connect', '127.0.0.1:7555'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return False
                
            stdout = stdout.replace(b'\r\n', b'\n')
            
            if not stdout:
                return False

            image_array = np.frombuffer(stdout, dtype=np.uint8)
            self.screen = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            return True
        except Exception:
            return False

    def adb_click(self, x, y):
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
            # Crop template to the bounding box of its opaque region (removes transparent edges)
            alpha_channel = template_img[:, :, 3]
            coords = cv2.findNonZero(alpha_channel)
            if coords is not None:
                x, y, w, h = cv2.boundingRect(coords)
                template_img = template_img[y:y+h, x:x+w, :3]
            else:
                template_img = template_img[:, :, :3]
            template_gray = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)
        else:
            template_gray = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)
        
        screen_h, screen_w = screen_gray.shape[:2]
        all_boxes = []
        
        if fast_mode and self.last_successful_scale is not None:
            scales = [self.last_successful_scale]
        else:
            scales = np.linspace(0.5, 2.0, 25)
            
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

    def click_cross(self):
        """Find and click cross_1.png to close a dialog."""
        if not self.get_adb_screenshot():
            return False
        cross_boxes = []
        for template_name in self.templates.keys():
            if template_name.startswith("cross_1"):
                cross_boxes.extend(self.find_image(template_name, threshold=0.70, fast_mode=False, update_cache=False))
        if cross_boxes:
            cross_box = cross_boxes[0]
            cx, cy = self.get_center(cross_box)
            print(f"--> [PHASE 3] Clicking cross button at ({cx}, {cy})...")
            self.adb_click(cx, cy)
            time.sleep(0.5)
            return True
        print("--> [PHASE 3] Cross button not found!")
        return False

    def exact_selling_sequence(self):
        print("--> [PHASE 3] Looking for shop button...")
        
        # Refresh the screen just before clicking the shop to ensure we have the latest UI state
        if not self.get_adb_screenshot():
            return False
        
        shop_boxes = []
        for template_name in self.templates.keys():
            if template_name.startswith("shop_button_1"):
                shop_boxes.extend(self.find_image(template_name, threshold=0.75, fast_mode=False, update_cache=False))
                
        if not shop_boxes:
            return False
            
        print(f"--> [PHASE 3] Found {len(shop_boxes)} shop buttons. Clicking the best match...")
        
        # Just click the first found shop button
        first_shop = shop_boxes[0]
        shop_x, shop_y = self.get_center(first_shop)
        
        print(f"--> [PHASE 3] Clicking shop button at ({shop_x}, {shop_y})...")
        self.adb_click(shop_x, shop_y)
        
        # Wait a bit for the shop UI to open
        time.sleep(0.5)
        # Loop: keep selling until no more empty slots
        slot_count = 0
        initial_empty_slots = 0
        while True:
            # Take a fresh screenshot of the shop interior
            if not self.get_adb_screenshot():
                print("--> [PHASE 3] Failed to take screenshot inside the shop.")
                break
                
            empty_slots = []
            for template_name in self.templates.keys():
                if template_name.startswith("empty_slot_1"):
                    empty_slots.extend(self.find_image(template_name, threshold=0.70, fast_mode=False, update_cache=False))
                    
            print(f"--> [PHASE 3] Found {len(empty_slots)} empty slot(s) in the shop.")
            
            if len(empty_slots) == 0:
                print("--> [PHASE 3] No more empty slots. Selling complete!")
                # Close the shop by clicking cross
                self.click_cross()
                break
            
            slot_count += 1
            if slot_count == 1:
                initial_empty_slots = len(empty_slots)
            print(f"--> [PHASE 3] === Selling slot #{slot_count} ===")
            
            # Sort slots top-left to bottom-right
            empty_slots.sort(key=lambda b: (b[1], b[0]))
            
            # Click the first empty slot
            first_slot = empty_slots[0]
            slot_x, slot_y = self.get_center(first_slot)
            print(f"--> [PHASE 3] Clicking first empty slot at ({slot_x}, {slot_y})...")
            self.adb_click(slot_x, slot_y)

            
            # Take a fresh screenshot to see the item selection screen
            if not self.get_adb_screenshot():
                break
            
            # Search for wheat icon
            wheat_boxes = []
            for template_name in self.templates.keys():
                if template_name.startswith("wheat_icon_1"):
                    wheat_boxes.extend(self.find_image(template_name, threshold=0.70, fast_mode=False, update_cache=False))
            
            if not wheat_boxes:
                print("--> [PHASE 3] Wheat icon not found! Closing dialogs...")
                # Click cross twice to close both dialogs
                self.click_cross()

                self.click_cross()
                break
            
            print(f"--> [PHASE 3] Found {len(wheat_boxes)} wheat icon(s).")
            wheat_box = wheat_boxes[0]
            wheat_x, wheat_y = self.get_center(wheat_box)
            
            # Click the wheat icon
            print(f"--> [PHASE 3] Clicking wheat icon at ({wheat_x}, {wheat_y})...")
            self.adb_click(wheat_x, wheat_y)

            
            # Take a fresh screenshot
            if not self.get_adb_screenshot():
                break
            
            # Check if we should NOT increase (dont_increase.png visible)
            dont_increase = []
            for template_name in self.templates.keys():
                if template_name.startswith("dont_increase"):
                    dont_increase.extend(self.find_image(template_name, threshold=0.70, fast_mode=False, update_cache=False))
            
            if dont_increase:
                print("--> [PHASE 3] dont_increase detected, skipping increase...")
            else:
                # Find the increase button
                increase_boxes = []
                for template_name in self.templates.keys():
                    if template_name.startswith("increase_wheat"):
                        increase_boxes.extend(self.find_image(template_name, threshold=0.70, fast_mode=False, update_cache=False))
                
                if not increase_boxes:
                    print("--> [PHASE 3] Increase wheat button not found!")
                    break
                
                increase_box = increase_boxes[0]
                # Click the right side of the increase button (not center)
                x1, y1, x2, y2 = increase_box
                inc_x = x2 + 20
                inc_y = y1 + (y2 - y1) // 2
                
                # Click increase button 5 times
                print(f"--> [PHASE 3] Clicking increase wheat button 5 times at ({inc_x}, {inc_y})...")
                for i in range(5):
                    self.adb_click(inc_x, inc_y)
                    time.sleep(0.05)
                print("--> [PHASE 3] Done increasing wheat quantity.")

            if not self.get_adb_screenshot():
                break
            
            # Find and click price up button
            price_boxes = []
            for template_name in self.templates.keys():
                if template_name.startswith("price_up_1"):
                    price_boxes.extend(self.find_image(template_name, threshold=0.70, fast_mode=False, update_cache=False))
            
            if not price_boxes:
                print("--> [PHASE 3] Price up button not found!")
                break
            
            price_box = price_boxes[0]
            price_x, price_y = self.get_center(price_box)
            print(f"--> [PHASE 3] Clicking price up button at ({price_x}, {price_y})...")
            self.adb_click(price_x, price_y)

            if not self.get_adb_screenshot():
                break
            
            # Find and click ad button (only on 3rd slot when started with 8)
            if slot_count >= 5 and initial_empty_slots == 8:
                ad_boxes = []
                for template_name in self.templates.keys():
                    if template_name.startswith("ad_button_1"):
                        ad_boxes.extend(self.find_image(template_name, threshold=0.70, fast_mode=False, update_cache=False))
                
                if not ad_boxes:
                    print("--> [PHASE 3] Ad button not found, skipping...")
                else:
                    ad_box = ad_boxes[0]
                    ad_x, ad_y = self.get_center(ad_box)
                    print(f"--> [PHASE 3] Clicking ad button at ({ad_x}, {ad_y})...")
                    self.adb_click(ad_x, ad_y)

            
            # Take a fresh screenshot
            if not self.get_adb_screenshot():
                break
            
            # Find and click "Put on Sale" button
            sell_boxes = []
            for template_name in self.templates.keys():
                if template_name.startswith("put_on_sell_1"):
                    sell_boxes.extend(self.find_image(template_name, threshold=0.70, fast_mode=False, update_cache=False))
            
            if not sell_boxes:
                print("--> [PHASE 3] Put on sale button not found!")
                break
            
            sell_box = sell_boxes[0]
            sell_x, sell_y = self.get_center(sell_box)
            print(f"--> [PHASE 3] Clicking put on sale button at ({sell_x}, {sell_y})...")
            self.adb_click(sell_x, sell_y)

        
        print(f"--> [PHASE 3] Sold {slot_count} item(s) total.")
        return slot_count > 0
