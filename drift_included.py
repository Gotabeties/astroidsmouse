import tkinter as tk
from PIL import Image, ImageTk
import pyautogui
import keyboard
import math
import time
import pygetwindow as gw  # Ensure this is imported properly
import win32gui
import win32con
import win32api

# Configuration variable to hide spaceship after drift
hide_after_drift = True  # NEW: Set this to True if you want the spaceship to disappear after drifting

# Load and resize the spaceship image
original_image = Image.open("spaceship.png").resize((50, 50), Image.Resampling.NEAREST)
angle = 0
speed = 0
max_speed = 15
acceleration = 1
friction = 0.95

# Screen dimensions
screen_width, screen_height = pyautogui.size()

# Get initial mouse position
x, y = pyautogui.position()

class AsteroidsMouseOverlay:
    def __init__(self, root):
        self.root = root
        self.root.attributes('-topmost', True)
        self.root.attributes('-transparentcolor', 'white')
        self.root.overrideredirect(True)
        self.canvas = tk.Canvas(root, width=50, height=50, bg='white', highlightthickness=0)
        self.canvas.pack()

        self.image = original_image
        self.tk_image = ImageTk.PhotoImage(self.image)
        self.image_id = self.canvas.create_image(25, 25, image=self.tk_image)

        self.hide_system_cursor()

        self.x, self.y = pyautogui.position()
        self.mouse_locked = False
        self.last_key_time = 0
        self.initial_angle = 0
        self.shrink_factor = 1.0
        self.rotation_angle = self.initial_angle

        self.is_drifting = False  # New flag to track drifting state
        self.is_hidden = False  # NEW: Flag to track visibility
        self.is_shrinking = False  # NEW: Flag to track shrinking state
        self.final_x, self.final_y = self.x, self.y  # NEW: Track the final position after drift

        self.root.title("Asteroids Cursor")
        self.root.after(10, self.update_position)
        self.root.after(100, self.make_click_through)

    def hide_system_cursor(self):
        try:
            win32api.ShowCursor(False)
        except Exception as e:
            print(f"Error hiding cursor: {e}")

    def restore_system_cursor(self):
        try:
            win32api.ShowCursor(True)
        except Exception as e:
            print(f"Error restoring cursor: {e}")

    def make_click_through(self):
        try:
            hwnd = gw.getWindowsWithTitle(self.root.title())[0]._hWnd
            win32gui.ShowWindow(hwnd, win32con.SW_SHOWNOACTIVATE)
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
                                   win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT)
        except IndexError:
            print("Error: Window not found. Retrying...")
            self.root.after(100, self.make_click_through)

    def update_position(self):
        global x, y, angle, speed

        mouse_x, mouse_y = pyautogui.position()
        key_pressed = False

        if keyboard.is_pressed('left') or keyboard.is_pressed('right') or keyboard.is_pressed('up'):
            key_pressed = True
            self.last_key_time = time.time()

        # Handle rotation
        if keyboard.is_pressed('left'):
            angle -= 5
        if keyboard.is_pressed('right'):
            angle += 5

        thrust_angle = angle - 90

        # Handle thrust
        if keyboard.is_pressed('up'):
            speed += acceleration
            speed = min(speed, max_speed)
            self.is_drifting = True
        else:
            speed *= friction
            if speed < 0.1:
                speed = 0
                self.is_drifting = False

        # Update position based on thrust angle
        if key_pressed or self.is_drifting:
            self.x += speed * math.cos(math.radians(thrust_angle))
            self.y += speed * math.sin(math.radians(thrust_angle))

        # Only follow the mouse if not drifting
        if not self.is_drifting:
            self.x, self.y = mouse_x, mouse_y

        # Check if spaceship should disappear after drift
        if hide_after_drift and not self.is_drifting and not key_pressed:
            self.hide_spaceship()
        else:
            self.show_spaceship()

        # Gradual shrinking and resetting rotation after drift
        if not self.is_drifting and not key_pressed:
            if self.shrink_factor > 0.5:  # If not already at 50% size
                self.shrink_factor -= 0.05  # Shrink by 5% each frame
                self.rotation_angle += (self.initial_angle - self.rotation_angle) * 0.1  # Gradually reset rotation
            else:
                self.rotation_angle = self.initial_angle  # Ensure the rotation is reset to 0 degrees when fully shrunk
                self.shrink_factor = 0.5  # Ensure it doesn't go below 50%

        # Return to original size and apply rotation based on current angle
        if key_pressed:
            self.shrink_factor = min(1.0, self.shrink_factor + 0.05)  # Enlarge the spaceship size back to 100%
            self.rotation_angle = angle  # Apply the rotation based on arrow keys

        current_size = (int(original_image.width * self.shrink_factor), int(original_image.height * self.shrink_factor))
        resized_image = self.image.resize(current_size, Image.Resampling.NEAREST)
        rotated_image = resized_image.rotate(-self.rotation_angle, resample=Image.Resampling.NEAREST, expand=True, fillcolor=(0, 0, 0, 0))

        self.x %= screen_width
        self.y %= screen_height

        # Lock the mouse while arrow keys are pressed
        if keyboard.is_pressed('up') or keyboard.is_pressed('left') or keyboard.is_pressed('right'):
            self.mouse_locked = True
        else:
            if self.mouse_locked and not self.is_drifting:
                # Teleport the mouse only after the spaceship has stopped drifting
                pyautogui.moveTo(self.x, self.y)
                self.final_x, self.final_y = self.x, self.y  # Update final position after drift
                self.mouse_locked = False

        rotated_image = rotated_image.convert("RGBA")
        data = rotated_image.getdata()

        new_data = [(0, 0, 0, 0) if item[3] == 0 else item for item in data]
        rotated_image.putdata(new_data)

        self.tk_image = ImageTk.PhotoImage(rotated_image)
        self.root.geometry(f"+{int(self.x - rotated_image.width // 2)}+{int(self.y - rotated_image.height // 2)}")
        self.canvas.config(width=rotated_image.width, height=rotated_image.height)
        self.canvas.itemconfig(self.image_id, image=self.tk_image)
        self.canvas.coords(self.image_id, rotated_image.width // 2, rotated_image.height // 2)

        if keyboard.is_pressed('esc'):
            print("Exiting...")
            self.restore_system_cursor()
            self.root.destroy()
            return

        self.root.after(10, self.update_position)

    def hide_spaceship(self):
        if not self.is_hidden:
            self.canvas.itemconfig(self.image_id, state='hidden')
            self.is_hidden = True

    def show_spaceship(self):
        if self.is_hidden:
            self.canvas.itemconfig(self.image_id, state='normal')
            self.is_hidden = False


if __name__ == "__main__":
    root = tk.Tk()
    app = AsteroidsMouseOverlay(root)
    print("Overlay active. Use arrow keys to control, Esc to exit.")
    root.mainloop()
