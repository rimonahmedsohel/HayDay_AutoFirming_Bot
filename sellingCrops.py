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
            stdout, _ = pipe.communicate()
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
        time.sleep(2.0)
        
        return True
