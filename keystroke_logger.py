#!/usr/bin/env python3
"""
Keystroke Activity Logger
Privacy-aware keystroke logging with window context and password field detection
"""

import json
import time
import re
import subprocess
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Set
import threading
import logging

try:
    from pynput import keyboard
    from pynput.keyboard import Key
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False
    Key = None

try:
    import evdev
    EVDEV_AVAILABLE = True
except ImportError:
    EVDEV_AVAILABLE = False


class KeystrokeLogger:
    """Privacy-aware keystroke activity logger"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.enabled = config.get('enabled', False)
        self.log_passwords = config.get('log_passwords', False)
        self.exclude_patterns = [re.compile(pattern, re.IGNORECASE) 
                               for pattern in config.get('exclude_windows', [])]
        
        self.log_dir = Path.home() / ".local/share/screenshare-assistant/logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # State tracking
        self.running = False
        self.current_window = ""
        self.key_count = 0
        self.word_count = 0
        self.session_start = None
        
        # Privacy flags
        self.in_password_field = False
        self.password_indicators = {
            "password", "passwd", "pwd", "login", "authenticate", 
            "secret", "key", "pin", "token", "credential"
        }
        
        # Buffer for efficient logging
        self.log_buffer = []
        self.buffer_size = 100
        self.last_flush = time.time()
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
    def is_excluded_window(self, window_title: str) -> bool:
        """Check if current window should be excluded from logging"""
        for pattern in self.exclude_patterns:
            if pattern.search(window_title):
                return True
        return False
    
    def detect_password_field(self, window_title: str) -> bool:
        """Detect if we're likely in a password field"""
        title_lower = window_title.lower()
        return any(indicator in title_lower for indicator in self.password_indicators)
    
    def get_active_window(self) -> str:
        """Get the title of the currently active window"""
        try:
            # X11 method
            result = subprocess.run([
                'xdotool', 'getwindowfocus', 'getwindowname'
            ], capture_output=True, text=True, timeout=1)
            
            if result.returncode == 0:
                return result.stdout.strip()
            
            # Fallback method using xprop
            result = subprocess.run([
                'xprop', '-id', 
                subprocess.check_output(['xdotool', 'getwindowfocus']).decode().strip(),
                'WM_NAME'
            ], capture_output=True, text=True, timeout=1)
            
            if result.returncode == 0:
                # Parse xprop output: WM_NAME(STRING) = "Window Title"
                line = result.stdout.strip()
                if '=' in line:
                    title = line.split('=', 1)[1].strip()
                    return title.strip('"')
                    
        except Exception as e:
            self.logger.debug(f"Failed to get window title: {e}")
            
        return "Unknown Window"
    
    def should_log_keystroke(self) -> bool:
        """Determine if current keystroke should be logged"""
        if not self.enabled:
            return False
            
        # Update window info
        current_window = self.get_active_window()
        if current_window != self.current_window:
            self.current_window = current_window
            self.in_password_field = self.detect_password_field(current_window)
            
            # Log window change
            self.log_event({
                "type": "window_change",
                "window": current_window,
                "timestamp": time.time()
            })
        
        # Check exclusions
        if self.is_excluded_window(self.current_window):
            return False
            
        # Check password field
        if self.in_password_field and not self.log_passwords:
            return False
            
        return True
    
    def log_event(self, event: Dict):
        """Add event to log buffer"""
        event["session_id"] = id(self)
        event["date"] = datetime.now().isoformat()
        
        self.log_buffer.append(event)
        
        # Flush buffer if needed
        if (len(self.log_buffer) >= self.buffer_size or 
            time.time() - self.last_flush > 30):
            self.flush_buffer()
    
    def flush_buffer(self):
        """Write buffered events to log file"""
        if not self.log_buffer:
            return
            
        log_file = self.log_dir / f"keystrokes-{date.today().isoformat()}.jsonl"
        
        try:
            with open(log_file, 'a') as f:
                for event in self.log_buffer:
                    f.write(json.dumps(event) + '\n')
                    
            self.log_buffer.clear()
            self.last_flush = time.time()
            
        except Exception as e:
            self.logger.error(f"Failed to write keystroke log: {e}")
    
    def on_key_press(self, key):
        """Handle key press events"""
        if not self.should_log_keystroke():
            return
            
        self.key_count += 1
        
        # Determine key type and value
        if hasattr(key, 'char') and key.char is not None:
            key_type = "char"
            key_value = key.char
            
            # Count words (space indicates word boundary)
            if key.char == ' ':
                self.word_count += 1
        else:
            key_type = "special"
            key_value = str(key).replace('Key.', '') if hasattr(key, 'name') else str(key)
        
        # Log the keystroke (but not the actual character for privacy)
        self.log_event({
            "type": "keystroke",
            "key_type": key_type,
            "key_value": key_value if not self.in_password_field else "[REDACTED]",
            "window": self.current_window,
            "timestamp": time.time(),
            "session_key_count": self.key_count,
            "session_word_count": self.word_count
        })
    
    def start_pynput_logging(self):
        """Start keystroke logging using pynput"""
        if not PYNPUT_AVAILABLE:
            raise RuntimeError("pynput not available")
            
        self.listener = keyboard.Listener(on_press=self.on_key_press)
        self.listener.start()
        self.logger.info("Started pynput keystroke logging")
        
    def start_evdev_logging(self):
        """Start keystroke logging using evdev (requires root or user in input group)"""
        if not EVDEV_AVAILABLE:
            raise RuntimeError("evdev not available")
            
        def evdev_loop():
            try:
                # Find keyboard devices
                devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
                keyboards = [dev for dev in devices if evdev.ecodes.EV_KEY in dev.capabilities()]
                
                if not keyboards:
                    self.logger.error("No keyboard devices found for evdev")
                    return
                
                self.logger.info(f"Found {len(keyboards)} keyboard devices for evdev logging")
                
                # Monitor all keyboard devices
                for device in keyboards:
                    for event in device.read_loop():
                        if not self.running:
                            break
                            
                        if event.type == evdev.ecodes.EV_KEY and event.value == 1:  # Key press
                            if self.should_log_keystroke():
                                self.key_count += 1
                                
                                self.log_event({
                                    "type": "keystroke",
                                    "key_type": "evdev",
                                    "key_code": event.code,
                                    "window": self.current_window,
                                    "timestamp": time.time(),
                                    "session_key_count": self.key_count
                                })
                                
            except PermissionError:
                self.logger.error("Permission denied for evdev. Add user to 'input' group or run as root")
            except Exception as e:
                self.logger.error(f"evdev logging error: {e}")
        
        self.evdev_thread = threading.Thread(target=evdev_loop, daemon=True)
        self.evdev_thread.start()
        self.logger.info("Started evdev keystroke logging")
    
    def start(self):
        """Start keystroke logging"""
        if not self.enabled:
            self.logger.info("Keystroke logging is disabled in config")
            return False
            
        if self.running:
            self.logger.warning("Keystroke logging already running")
            return True
            
        self.running = True
        self.session_start = time.time()
        self.key_count = 0
        self.word_count = 0
        
        # Log session start
        self.log_event({
            "type": "session_start",
            "timestamp": self.session_start,
            "method": "unknown"
        })
        
        # Try pynput first (more stable), then evdev
        try:
            if PYNPUT_AVAILABLE:
                self.start_pynput_logging()
                self.log_event({"type": "session_start", "method": "pynput", "timestamp": time.time()})
                self.logger.info("Keystroke logging started with pynput")
                return True
            elif EVDEV_AVAILABLE:
                self.start_evdev_logging()
                self.log_event({"type": "session_start", "method": "evdev", "timestamp": time.time()})
                self.logger.info("Keystroke logging started with evdev")
                return True
            else:
                self.logger.error("No keystroke logging backend available (pynput or evdev)")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to start keystroke logging: {e}")
            self.running = False
            return False
    
    def stop(self):
        """Stop keystroke logging"""
        if not self.running:
            return
            
        self.running = False
        
        # Log session end
        session_duration = time.time() - self.session_start if self.session_start else 0
        self.log_event({
            "type": "session_end",
            "timestamp": time.time(),
            "duration": session_duration,
            "total_keys": self.key_count,
            "total_words": self.word_count
        })
        
        # Stop listeners
        if hasattr(self, 'listener'):
            self.listener.stop()
            self.listener.join()
            
        # Flush remaining buffer
        self.flush_buffer()
        
        self.logger.info(f"Keystroke logging stopped. Session: {self.key_count} keys, {self.word_count} words")
    
    def get_stats(self) -> Dict:
        """Get current logging statistics"""
        session_duration = time.time() - self.session_start if self.session_start else 0
        
        return {
            "enabled": self.enabled,
            "running": self.running,
            "current_window": self.current_window,
            "in_password_field": self.in_password_field,
            "session_duration": session_duration,
            "key_count": self.key_count,
            "word_count": self.word_count,
            "keys_per_minute": (self.key_count / (session_duration / 60)) if session_duration > 0 else 0
        }
    
    def cleanup_old_logs(self):
        """Remove old log files based on config"""
        max_files = self.config.get('max_log_files', 30)
        
        try:
            log_files = sorted(self.log_dir.glob("keystrokes-*.jsonl"))
            if len(log_files) > max_files:
                for old_file in log_files[:-max_files]:
                    old_file.unlink()
                    self.logger.info(f"Removed old keystroke log: {old_file.name}")
                    
        except Exception as e:
            self.logger.error(f"Failed to cleanup old logs: {e}")


def main():
    """Test keystroke logger"""
    import signal
    
    config = {
        "enabled": True,
        "log_passwords": False,
        "exclude_windows": [".*password.*", "KeePass.*"],
        "max_log_files": 10
    }
    
    logger = KeystrokeLogger(config)
    
    def signal_handler(sig, frame):
        print("\nStopping keystroke logger...")
        logger.stop()
        exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    if logger.start():
        print("🎹 Keystroke logging started")
        print("💡 Type in different applications to see logging in action")
        print("💡 Try opening password managers to see exclusion")
        print("💡 Press Ctrl+C to stop")
        
        try:
            while logger.running:
                time.sleep(1)
                stats = logger.get_stats()
                print(f"\r👁️  Keys: {stats['key_count']}, Words: {stats['word_count']}, "
                      f"Window: {stats['current_window'][:30]}...", end="")
        except KeyboardInterrupt:
            pass
    else:
        print("❌ Failed to start keystroke logging")


if __name__ == "__main__":
    main()