import tkinter as tk
from PIL import Image, ImageTk
import pyautogui
import keyboard
import math
import time
import pygetwindow as gw  # To handle window manipulation (click-through)
import win32gui
import win32con
import win32api  # Import win32api for cursor management

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
        self.root.overrideredirect(True)  # Remove window border
        self.canvas = tk.Canvas(root, width=50, height=50, bg='white', highlightthickness=0)
        self.canvas.pack()

        # Load image and display on canvas
        self.image = original_image
        self.tk_image = ImageTk.PhotoImage(self.image)
        self.image_id = self.canvas.create_image(25, 25, image=self.tk_image)

        # Hide system cursor using win32api
        self.hide_system_cursor()

        # Initialize the position based on the system mouse (initial placement)
        self.x, self.y = pyautogui.position()
        self.mouse_locked = False
        self.last_key_time = 0  # Timestamp for last key press
        self.initial_angle = 0  # Set the initial angle to 0 degrees
        self.shrink_factor = 1.0  # Initial size (100% size)
        self.rotation_angle = self.initial_angle  # Start at 0 degrees

        self.root.title("Asteroids Cursor")  # Set the window title

        self.root.after(10, self.update_position)

        # Make the window click-through
        self.root.after(100, self.make_click_through)

    def hide_system_cursor(self):
        try:
            # Hide the system cursor while the overlay is active
            win32api.ShowCursor(False)
        except Exception as e:
            print(f"Error hiding cursor: {e}")

    def restore_system_cursor(self):
        try:
            # Restore the system cursor when the program exits
            win32api.ShowCursor(True)
        except Exception as e:
            print(f"Error restoring cursor: {e}")

    def make_click_through(self):
        try:
            hwnd = gw.getWindowsWithTitle(self.root.title())[0]._hWnd
            win32gui.ShowWindow(hwnd, win32con.SW_SHOWNOACTIVATE)  # Make the window click-through
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
                                   win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT)  # Set layered and transparent style
        except IndexError:
            print("Error: Window not found. Retrying...")
            self.root.after(100, self.make_click_through)  # Retry after 100ms

    def update_position(self):
        global x, y, angle, speed

        # Get the current system mouse position
        mouse_x, mouse_y = pyautogui.position()

        # Check for arrow key presses and update the timestamp
        key_pressed = False
        if keyboard.is_pressed('left') or keyboard.is_pressed('right') or keyboard.is_pressed('up'):
            key_pressed = True
            self.last_key_time = time.time()  # Update last key press time

        # Handle rotation
        if keyboard.is_pressed('left'):
            angle -= 5  # Rotate counterclockwise
        if keyboard.is_pressed('right'):
            angle += 5  # Rotate clockwise

        # Adjust for the 90-degree counterclockwise offset on thrust
        thrust_angle = angle - 90  # 90 degrees counterclockwise shift

        # Handle thrust (accelerating)
        if keyboard.is_pressed('up'):
            speed += acceleration
            speed = min(speed, max_speed)
        else:
            # Apply friction when no thrust is being applied
            speed *= friction

        # Calculate new position based on the adjusted thrust angle
        if keyboard.is_pressed('up'):
            self.x += speed * math.cos(math.radians(thrust_angle))  # Adjusted thrust direction
            self.y += speed * math.sin(math.radians(thrust_angle))  # Adjusted thrust direction

        # Prevent moving to the mouse if a key was pressed recently (within 0.5 seconds)
        if time.time() - self.last_key_time < 0.5:  # Last key press was within the last 0.5 seconds
            key_pressed = True

        # When no arrow keys are pressed or no recent key press, make the spaceship follow the mouse directly
        if not key_pressed:
            self.x, self.y = mouse_x, mouse_y  # Directly move to the mouse position

            # Gradual shrink transition and reset rotation over a short period (0.2 seconds)
            if self.shrink_factor > 0.5:  # If not already at 50% size
                self.shrink_factor -= 0.05  # Shrink by 5% each frame
                self.rotation_angle += (self.initial_angle - self.rotation_angle) * 0.1  # Gradually reset rotation
            else:
                self.rotation_angle = self.initial_angle  # Ensure the rotation is reset to 0 degrees when fully shrunk
        else:
            # Return to original size and apply rotation based on current angle
            self.shrink_factor = min(1.0, self.shrink_factor + 0.05)  # Enlarge the spaceship size back to 100%
            self.rotation_angle = angle  # Apply the rotation based on arrow keys

        # Create the resized spaceship image based on the current shrink factor
        current_size = (int(original_image.width * self.shrink_factor), int(original_image.height * self.shrink_factor))
        resized_image = self.image.resize(current_size, Image.Resampling.NEAREST)

        # Rotate the image smoothly
        rotated_image = resized_image.rotate(-self.rotation_angle, resample=Image.Resampling.NEAREST, expand=True, fillcolor=(0, 0, 0, 0))

        # Wrap around screen edges
        self.x %= screen_width
        self.y %= screen_height

        # Lock the mouse position while arrow keys are pressed
        if keyboard.is_pressed('up') or keyboard.is_pressed('left') or keyboard.is_pressed('right'):
            self.mouse_locked = True
        else:
            if self.mouse_locked:
                # After keys are released, move the mouse to the final spaceship position
                pyautogui.moveTo(self.x, self.y)
                self.mouse_locked = False

        # Optionally, replace the transparent background with black (or another color if needed)
        rotated_image = rotated_image.convert("RGBA")  # Ensure it's in RGBA mode to preserve transparency properly

        # Fix transparent edges to remove white pixels around the border
        data = rotated_image.getdata()

        new_data = []
        for item in data:
            # Replace fully transparent pixels with black (or another color if needed)
            if item[3] == 0:  # Fully transparent
                new_data.append((0, 0, 0, 0))  # Fully transparent pixel
            else:
                new_data.append(item)  # Keep the original pixel

        rotated_image.putdata(new_data)

        self.tk_image = ImageTk.PhotoImage(rotated_image)

        # Move window to the new position (adjusting for the center of the ship)
        self.root.geometry(f"+{int(self.x - rotated_image.width // 2)}+{int(self.y - rotated_image.height // 2)}")

        # Adjust canvas position to keep the rotated image centered
        self.canvas.config(width=rotated_image.width, height=rotated_image.height)
        self.canvas.itemconfig(self.image_id, image=self.tk_image)
        self.canvas.coords(self.image_id, rotated_image.width // 2, rotated_image.height // 2)

        # Exit on 'Esc' key
        if keyboard.is_pressed('esc'):
            print("Exiting...")
            self.restore_system_cursor()  # Restore the system cursor before closing
            self.root.destroy()
            return

        self.root.after(10, self.update_position)

if __name__ == "__main__":
    root = tk.Tk()
    app = AsteroidsMouseOverlay(root)
    print("Overlay active. Use arrow keys to control, Esc to exit.")
    root.mainloop()
