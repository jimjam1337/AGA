import pyautogui

# Get the current mouse position
x, y = pyautogui.position()

# Print the pixel coordinates (x, y)
print(f"The current mouse position is: ({x}, {y})")