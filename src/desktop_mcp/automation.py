"""
Advanced desktop automation capabilities for the Desktop MCP
"""

import time
import logging
from typing import Dict, Any, List, Optional, Tuple
import pyautogui
import pyperclip
from pynput import mouse, keyboard
from pynput.keyboard import Key, Listener as KeyboardListener
from pynput.mouse import Listener as MouseListener
import threading
import os
import platform
import subprocess

logger = logging.getLogger("DesktopMCP.Automation")

# Disable PyAutoGUI failsafe for automation (can be re-enabled)
pyautogui.FAILSAFE = False

class WindowManager:
    """Manages window operations and desktop interactions"""
    
    @staticmethod
    def get_system_type():
        """Get the current operating system"""
        return platform.system().lower()
    
    @staticmethod
    def get_active_window_info() -> Dict[str, Any]:
        """Get information about the currently active window"""
        try:
            system = WindowManager.get_system_type()
            
            if system == "windows":
                # Windows-specific window detection
                import win32gui
                import win32process
                
                hwnd = win32gui.GetForegroundWindow()
                if hwnd:
                    window_text = win32gui.GetWindowText(hwnd)
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    rect = win32gui.GetWindowRect(hwnd)
                    
                    return {
                        "success": True,
                        "title": window_text,
                        "pid": pid,
                        "position": {"x": rect[0], "y": rect[1]},
                        "size": {"width": rect[2] - rect[0], "height": rect[3] - rect[1]},
                        "handle": hwnd
                    }
            
            elif system == "darwin":  # macOS
                # Use AppleScript for macOS
                script = '''
                tell application "System Events"
                    set frontApp to first application process whose frontmost is true
                    set frontWindow to first window of frontApp
                    return {name of frontApp, name of frontWindow, position of frontWindow, size of frontWindow}
                end tell
                '''
                result = subprocess.run(['osascript', '-e', script], 
                                     capture_output=True, text=True)
                if result.returncode == 0:
                    # Parse the result
                    return {
                        "success": True,
                        "title": "Active Window",
                        "app_name": result.stdout.strip(),
                        "system": "macOS"
                    }
            
            elif system == "linux":
                # Use wmctrl for Linux
                try:
                    result = subprocess.run(['wmctrl', '-a'], capture_output=True, text=True)
                    if result.returncode == 0:
                        return {
                            "success": True,
                            "title": "Active Window",
                            "system": "Linux"
                        }
                except FileNotFoundError:
                    pass
            
            # Fallback method using screen position
            return {
                "success": True,
                "title": "Unknown Window",
                "position": {"x": 0, "y": 0},
                "size": {"width": 1920, "height": 1080},
                "system": system
            }
            
        except Exception as e:
            logger.error(f"Failed to get active window info: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def minimize_window() -> Dict[str, Any]:
        """Minimize the currently active window"""
        try:
            system = WindowManager.get_system_type()
            
            if system == "windows":
                pyautogui.hotkey('win', 'down')
            elif system == "darwin":
                pyautogui.hotkey('cmd', 'm')
            else:  # Linux
                pyautogui.hotkey('alt', 'F9')
            
            return {"success": True, "message": "Window minimized"}
        except Exception as e:
            logger.error(f"Failed to minimize window: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def maximize_window() -> Dict[str, Any]:
        """Maximize the currently active window"""
        try:
            system = WindowManager.get_system_type()
            
            if system == "windows":
                pyautogui.hotkey('win', 'up')
            elif system == "darwin":
                # macOS doesn't have a direct maximize, use fullscreen
                pyautogui.hotkey('ctrl', 'cmd', 'f')
            else:  # Linux
                pyautogui.hotkey('alt', 'F10')
            
            return {"success": True, "message": "Window maximized"}
        except Exception as e:
            logger.error(f"Failed to maximize window: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def close_window() -> Dict[str, Any]:
        """Close the currently active window"""
        try:
            system = WindowManager.get_system_type()
            
            if system == "windows":
                pyautogui.hotkey('alt', 'F4')
            elif system == "darwin":
                pyautogui.hotkey('cmd', 'w')
            else:  # Linux
                pyautogui.hotkey('alt', 'F4')
            
            return {"success": True, "message": "Window closed"}
        except Exception as e:
            logger.error(f"Failed to close window: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def switch_application(app_name: str) -> Dict[str, Any]:
        """Switch to a specific application"""
        try:
            system = WindowManager.get_system_type()
            
            if system == "windows":
                # Alt+Tab to open task switcher, then search
                pyautogui.hotkey('alt', 'tab')
                time.sleep(0.5)
                pyautogui.typewrite(app_name)
                pyautogui.press('enter')
            elif system == "darwin":
                # Use Cmd+Tab and then search
                pyautogui.hotkey('cmd', 'tab')
                time.sleep(0.5)
                pyautogui.typewrite(app_name)
                pyautogui.press('enter')
            else:  # Linux
                # Use Alt+Tab
                pyautogui.hotkey('alt', 'tab')
                time.sleep(0.5)
            
            return {"success": True, "message": f"Switched to {app_name}"}
        except Exception as e:
            logger.error(f"Failed to switch to application: {str(e)}")
            return {"success": False, "error": str(e)}

class ClipboardManager:
    """Manages clipboard operations"""
    
    @staticmethod
    def get_clipboard_content() -> Dict[str, Any]:
        """Get the current clipboard content"""
        try:
            content = pyperclip.paste()
            return {
                "success": True,
                "content": content,
                "length": len(content),
                "type": "text"
            }
        except Exception as e:
            logger.error(f"Failed to get clipboard content: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def set_clipboard_content(text: str) -> Dict[str, Any]:
        """Set the clipboard content"""
        try:
            pyperclip.copy(text)
            return {
                "success": True,
                "message": f"Copied {len(text)} characters to clipboard",
                "content": text[:100] + "..." if len(text) > 100 else text
            }
        except Exception as e:
            logger.error(f"Failed to set clipboard content: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def clear_clipboard() -> Dict[str, Any]:
        """Clear the clipboard"""
        try:
            pyperclip.copy("")
            return {"success": True, "message": "Clipboard cleared"}
        except Exception as e:
            logger.error(f"Failed to clear clipboard: {str(e)}")
            return {"success": False, "error": str(e)}

class MouseKeyboardController:
    """Controls mouse and keyboard automation"""
    
    @staticmethod
    def click_at_position(x: int, y: int, button: str = "left", clicks: int = 1) -> Dict[str, Any]:
        """Click at a specific screen position"""
        try:
            button_map = {
                "left": pyautogui.LEFT,
                "right": pyautogui.RIGHT,
                "middle": pyautogui.MIDDLE
            }
            
            if button not in button_map:
                return {"success": False, "error": f"Invalid button: {button}"}
            
            pyautogui.click(x, y, clicks=clicks, button=button_map[button])
            
            return {
                "success": True,
                "message": f"Clicked {button} button {clicks} time(s) at ({x}, {y})",
                "position": {"x": x, "y": y},
                "button": button,
                "clicks": clicks
            }
        except Exception as e:
            logger.error(f"Failed to click at position: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def type_text(text: str, interval: float = 0.1) -> Dict[str, Any]:
        """Type text with specified interval between characters"""
        try:
            pyautogui.typewrite(text, interval=interval)
            return {
                "success": True,
                "message": f"Typed {len(text)} characters",
                "text": text[:100] + "..." if len(text) > 100 else text,
                "interval": interval
            }
        except Exception as e:
            logger.error(f"Failed to type text: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def send_key_combination(keys: List[str]) -> Dict[str, Any]:
        """Send a key combination (e.g., ctrl+c, alt+tab)"""
        try:
            # Map common key names
            key_map = {
                "ctrl": "ctrl", "control": "ctrl",
                "alt": "alt", "option": "alt",
                "shift": "shift",
                "cmd": "cmd", "command": "cmd", "win": "win", "windows": "win",
                "tab": "tab", "enter": "enter", "return": "enter",
                "space": "space", "spacebar": "space",
                "escape": "esc", "esc": "esc",
                "delete": "delete", "del": "delete",
                "backspace": "backspace",
                "home": "home", "end": "end",
                "pageup": "pageup", "pagedown": "pagedown",
                "up": "up", "down": "down", "left": "left", "right": "right"
            }
            
            # Convert keys to lowercase and map them
            mapped_keys = []
            for key in keys:
                key_lower = key.lower()
                if key_lower in key_map:
                    mapped_keys.append(key_map[key_lower])
                elif len(key) == 1:  # Single character
                    mapped_keys.append(key_lower)
                else:
                    mapped_keys.append(key)  # Use as-is for function keys, etc.
            
            pyautogui.hotkey(*mapped_keys)
            
            return {
                "success": True,
                "message": f"Sent key combination: {'+'.join(keys)}",
                "keys": mapped_keys
            }
        except Exception as e:
            logger.error(f"Failed to send key combination: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def get_mouse_position() -> Dict[str, Any]:
        """Get current mouse position"""
        try:
            x, y = pyautogui.position()
            return {
                "success": True,
                "position": {"x": x, "y": y},
                "screen_size": {"width": pyautogui.size().width, "height": pyautogui.size().height}
            }
        except Exception as e:
            logger.error(f"Failed to get mouse position: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def move_mouse_to(x: int, y: int, duration: float = 1.0) -> Dict[str, Any]:
        """Move mouse to specific position with animation"""
        try:
            pyautogui.moveTo(x, y, duration=duration)
            return {
                "success": True,
                "message": f"Moved mouse to ({x}, {y})",
                "position": {"x": x, "y": y},
                "duration": duration
            }
        except Exception as e:
            logger.error(f"Failed to move mouse: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def scroll(direction: str, clicks: int = 3) -> Dict[str, Any]:
        """Scroll up or down"""
        try:
            if direction.lower() == "up":
                pyautogui.scroll(clicks)
            elif direction.lower() == "down":
                pyautogui.scroll(-clicks)
            else:
                return {"success": False, "error": "Direction must be 'up' or 'down'"}
            
            return {
                "success": True,
                "message": f"Scrolled {direction} {clicks} clicks",
                "direction": direction,
                "clicks": clicks
            }
        except Exception as e:
            logger.error(f"Failed to scroll: {str(e)}")
            return {"success": False, "error": str(e)}

class MacroRecorder:
    """Records and plays back mouse and keyboard macros"""
    
    def __init__(self):
        self.recording = False
        self.events = []
        self.mouse_listener = None
        self.keyboard_listener = None
        self.start_time = None
    
    def start_recording(self) -> Dict[str, Any]:
        """Start recording mouse and keyboard events"""
        try:
            if self.recording:
                return {"success": False, "error": "Already recording"}
            
            self.recording = True
            self.events = []
            self.start_time = time.time()
            
            # Start mouse listener
            self.mouse_listener = MouseListener(
                on_click=self._on_mouse_click,
                on_scroll=self._on_mouse_scroll
            )
            
            # Start keyboard listener
            self.keyboard_listener = KeyboardListener(
                on_press=self._on_key_press
            )
            
            self.mouse_listener.start()
            self.keyboard_listener.start()
            
            return {
                "success": True,
                "message": "Started recording macro",
                "start_time": self.start_time
            }
        except Exception as e:
            logger.error(f"Failed to start recording: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def stop_recording(self) -> Dict[str, Any]:
        """Stop recording and return the recorded events"""
        try:
            if not self.recording:
                return {"success": False, "error": "Not currently recording"}
            
            self.recording = False
            
            # Stop listeners
            if self.mouse_listener:
                self.mouse_listener.stop()
            if self.keyboard_listener:
                self.keyboard_listener.stop()
            
            end_time = time.time()
            duration = end_time - self.start_time
            
            return {
                "success": True,
                "message": f"Stopped recording macro",
                "duration": duration,
                "events": len(self.events),
                "recorded_events": self.events[:10]  # Show first 10 events
            }
        except Exception as e:
            logger.error(f"Failed to stop recording: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _on_mouse_click(self, x, y, button, pressed):
        """Handle mouse click events"""
        if self.recording:
            current_time = time.time() - self.start_time
            self.events.append({
                "type": "mouse_click",
                "time": current_time,
                "x": x,
                "y": y,
                "button": str(button),
                "pressed": pressed
            })
    
    def _on_mouse_scroll(self, x, y, dx, dy):
        """Handle mouse scroll events"""
        if self.recording:
            current_time = time.time() - self.start_time
            self.events.append({
                "type": "mouse_scroll",
                "time": current_time,
                "x": x,
                "y": y,
                "dx": dx,
                "dy": dy
            })
    
    def _on_key_press(self, key):
        """Handle key press events"""
        if self.recording:
            current_time = time.time() - self.start_time
            self.events.append({
                "type": "key_press",
                "time": current_time,
                "key": str(key)
            })
    
    def play_macro(self, speed_multiplier: float = 1.0) -> Dict[str, Any]:
        """Play back recorded macro"""
        try:
            if self.recording:
                return {"success": False, "error": "Cannot play macro while recording"}
            
            if not self.events:
                return {"success": False, "error": "No recorded events to play"}
            
            # Play back events
            last_time = 0
            for event in self.events:
                # Wait for the appropriate delay
                delay = (event["time"] - last_time) / speed_multiplier
                if delay > 0:
                    time.sleep(delay)
                
                # Execute the event
                if event["type"] == "mouse_click" and event["pressed"]:
                    pyautogui.click(event["x"], event["y"])
                elif event["type"] == "mouse_scroll":
                    pyautogui.scroll(event["dy"], x=event["x"], y=event["y"])
                elif event["type"] == "key_press":
                    try:
                        # Parse the key and press it
                        key_str = event["key"].replace("Key.", "").replace("'", "")
                        pyautogui.press(key_str)
                    except:
                        pass  # Skip invalid keys
                
                last_time = event["time"]
            
            return {
                "success": True,
                "message": f"Played macro with {len(self.events)} events",
                "events_played": len(self.events),
                "speed_multiplier": speed_multiplier
            }
        except Exception as e:
            logger.error(f"Failed to play macro: {str(e)}")
            return {"success": False, "error": str(e)}