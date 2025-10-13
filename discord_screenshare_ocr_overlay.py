#!/usr/bin/env python3
"""
Discord Screenshare OCR Overlay
Real-time transparent overlay showing OCR text for Discord screenshare viewers
"""

import sys
import time
import json
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import threading
import traceback

from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, 
                             QSystemTrayIcon, QMenu, QAction, qApp,
                             QHBoxLayout, QPushButton, QSpinBox, QCheckBox,
                             QColorDialog, QFontDialog, QDialog, QFormLayout)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon, QPainter, QPixmap

import mss
from PIL import Image
from tesseract_timeout_fix_working import WorkingFastScreenOCR


class OCRWorker(QThread):
    """Background thread for OCR processing to keep UI responsive"""
    text_ready = pyqtSignal(str)
    
    def __init__(self, ocr_engine):
        super().__init__()
        self.ocr_engine = ocr_engine
        self.running = False
        self.last_text = ""
        self.image_queue = []
        
    def add_image(self, image):
        """Add image to processing queue"""
        # Keep only the latest image to avoid lag
        self.image_queue = [image]
        
    def run(self):
        """Main OCR processing loop"""
        self.running = True
        
        while self.running:
            try:
                if self.image_queue:
                    image = self.image_queue.pop(0)
                    
                    # Extract text using our working OCR
                    text = self.ocr_engine.extract_screen_text(image)
                    
                    # Only emit if text changed and is non-empty
                    if text and text.strip() and text != self.last_text:
                        self.last_text = text
                        self.text_ready.emit(text.strip())
                
                time.sleep(0.05)  # Small delay to prevent high CPU usage
                    
            except Exception as e:
                print(f"OCR Worker error: {e}")
                time.sleep(0.1)  # Brief pause on error
                
    def stop(self):
        """Stop the OCR processing"""
        self.running = False
        self.wait()


class ConfigDialog(QDialog):
    """Simple configuration dialog"""
    
    def __init__(self, config: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.config = config.copy()
        self.setWindowTitle("OCR Overlay Settings")
        self.setModal(True)
        
        layout = QFormLayout()
        
        # Capture region
        self.x_spin = QSpinBox()
        self.x_spin.setRange(0, 9999)
        self.x_spin.setValue(config['capture_region']['x'])
        layout.addRow("Capture X:", self.x_spin)
        
        self.y_spin = QSpinBox()
        self.y_spin.setRange(0, 9999)
        self.y_spin.setValue(config['capture_region']['y'])
        layout.addRow("Capture Y:", self.y_spin)
        
        self.w_spin = QSpinBox()
        self.w_spin.setRange(50, 9999)
        self.w_spin.setValue(config['capture_region']['width'])
        layout.addRow("Capture Width:", self.w_spin)
        
        self.h_spin = QSpinBox()
        self.h_spin.setRange(50, 9999)
        self.h_spin.setValue(config['capture_region']['height'])
        layout.addRow("Capture Height:", self.h_spin)
        
        # FPS
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 30)
        self.fps_spin.setValue(config['fps'])
        layout.addRow("FPS:", self.fps_spin)
        
        # Click through
        self.click_through_check = QCheckBox()
        self.click_through_check.setChecked(config['click_through'])
        layout.addRow("Click Through:", self.click_through_check)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addRow(button_layout)
        self.setLayout(layout)
        
    def get_config(self) -> Dict[str, Any]:
        """Get updated configuration"""
        self.config['capture_region'] = {
            'x': self.x_spin.value(),
            'y': self.y_spin.value(),
            'width': self.w_spin.value(),
            'height': self.h_spin.value()
        }
        self.config['fps'] = self.fps_spin.value()
        self.config['click_through'] = self.click_through_check.isChecked()
        return self.config


class OCROverlayWindow(QWidget):
    """Main transparent overlay window for OCR text display"""
    
    def __init__(self):
        super().__init__()
        self.config_file = Path.home() / ".ocr_overlay_config.json"
        self.config = self.load_config()
        
        # Initialize OCR and screen capture
        self.ocr_engine = WorkingFastScreenOCR(timeout=3.0)
        self.sct = mss.mss()
        
        # OCR worker thread
        self.ocr_worker = None
        
        # Timer for screen capture
        self.capture_timer = QTimer()
        self.capture_timer.timeout.connect(self.capture_screen)
        self.fps = 8
        
        # Setup UI
        self.init_ui()
        self.setup_tray()
        
        # Start OCR processing
        self.start_ocr()
        
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        default_config = {
            "window": {
                "x": 50,
                "y": 50,
                "width": 400,
                "height": 200
            },
            "capture_region": {
                "x": 100,
                "y": 100,
                "width": 800,
                "height": 600
            },
            "fps": 8,
            "click_through": True,
            "font": {
                "family": "Arial",
                "size": 12,
                "bold": False
            },
            "colors": {
                "text": "#00FF00",
                "background": "#000000"
            },
            "opacity": 0.8
        }
        
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                # Merge with defaults to handle missing keys
                for key, value in default_config.items():
                    if key not in loaded_config:
                        loaded_config[key] = value
                return loaded_config
        except Exception as e:
            print(f"Error loading config: {e}")
            
        return default_config
    
    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def init_ui(self):
        """Initialize the overlay window"""
        # Window properties for transparent overlay
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool
        )
        
        if self.config['click_through']:
            self.setAttribute(Qt.WA_TransparentForMouseEvents)
            
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowOpacity(self.config['opacity'])
        
        # Layout
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Text display label
        self.text_label = QLabel("Waiting for text...")
        self.text_label.setWordWrap(True)
        self.text_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        # Apply styling
        self.update_styling()
        
        layout.addWidget(self.text_label)
        self.setLayout(layout)
        
        # Window position and size
        self.setGeometry(
            self.config['window']['x'],
            self.config['window']['y'],
            self.config['window']['width'],
            self.config['window']['height']
        )
        
    def update_styling(self):
        """Update text styling from config"""
        font = QFont(
            self.config['font']['family'],
            self.config['font']['size']
        )
        font.setBold(self.config['font']['bold'])
        self.text_label.setFont(font)
        
        # Set colors
        self.text_label.setStyleSheet(f"""
            QLabel {{
                color: {self.config['colors']['text']};
                background-color: {self.config['colors']['background']};
                padding: 8px;
                border-radius: 4px;
            }}
        """)
        
    def setup_tray(self):
        """Setup system tray icon and menu"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            print("System tray not available")
            return
            
        # Create tray icon
        self.tray_icon = QSystemTrayIcon(self)
        
        # Create a simple icon
        pixmap = QPixmap(16, 16)
        pixmap.fill(QColor(0, 255, 0))
        self.tray_icon.setIcon(QIcon(pixmap))
        
        # Create tray menu
        tray_menu = QMenu()
        
        show_action = QAction("Show/Hide", self)
        show_action.triggered.connect(self.toggle_visibility)
        tray_menu.addAction(show_action)
        
        tray_menu.addSeparator()
        
        config_action = QAction("Settings", self)
        config_action.triggered.connect(self.show_config)
        tray_menu.addAction(config_action)
        
        tray_menu.addSeparator()
        
        quit_action = QAction("Exit", self)
        quit_action.triggered.connect(qApp.quit)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_activated)
        self.tray_icon.show()
        
    def tray_activated(self, reason):
        """Handle tray icon activation"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.toggle_visibility()
            
    def toggle_visibility(self):
        """Toggle window visibility"""
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            
    def show_config(self):
        """Show configuration dialog"""
        dialog = ConfigDialog(self.config, self)
        if dialog.exec_() == QDialog.Accepted:
            self.config = dialog.get_config()
            self.apply_config()
            self.save_config()
            
    def apply_config(self):
        """Apply configuration changes"""
        # Update window properties
        if self.config['click_through']:
            self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        else:
            self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            
        self.setWindowOpacity(self.config['opacity'])
        
        # Update styling
        self.update_styling()
        
        # Restart OCR with new settings
        self.stop_ocr()
        time.sleep(0.1)
        self.start_ocr()
        
    def capture_screen(self):
        """Capture screen and send to OCR worker"""
        try:
            # Create monitor configuration for mss
            monitor_config = {
                "top": self.config['capture_region']['y'],
                "left": self.config['capture_region']['x'],
                "width": self.config['capture_region']['width'],
                "height": self.config['capture_region']['height']
            }
            
            # Capture screen region
            screenshot = self.sct.grab(monitor_config)
            img = Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')
            
            # Send to OCR worker if it's running
            if self.ocr_worker and self.ocr_worker.isRunning():
                self.ocr_worker.add_image(img)
                
        except Exception as e:
            print(f"Screen capture error: {e}")
    
    def start_ocr(self):
        """Start OCR processing"""
        if self.ocr_worker and self.ocr_worker.isRunning():
            return
            
        # Start OCR worker thread
        self.ocr_worker = OCRWorker(self.ocr_engine)
        self.ocr_worker.text_ready.connect(self.update_text)
        self.ocr_worker.start()
        
        # Start screen capture timer
        self.fps = self.config['fps']
        interval = int(1000 / self.fps)  # Convert to milliseconds
        self.capture_timer.start(interval)
        
        capture_config = {
            "top": self.config['capture_region']['y'],
            "left": self.config['capture_region']['x'],
            "width": self.config['capture_region']['width'],
            "height": self.config['capture_region']['height']
        }
        
        print(f"✅ OCR Overlay started - capturing region {capture_config} at {self.fps} FPS")
        
    def stop_ocr(self):
        """Stop OCR processing"""
        # Stop screen capture timer
        if self.capture_timer.isActive():
            self.capture_timer.stop()
            
        # Stop OCR worker thread
        if self.ocr_worker and self.ocr_worker.isRunning():
            self.ocr_worker.stop()
            self.ocr_worker = None
            
    @pyqtSlot(str)
    def update_text(self, text: str):
        """Update the displayed text"""
        # Limit text length to prevent UI issues
        if len(text) > 500:
            text = text[:500] + "..."
            
        self.text_label.setText(text)
        
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        if event.key() == Qt.Key_Escape:
            self.hide()
        elif event.key() == Qt.Key_F1:
            self.show_config()
        elif event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_Q:
            qApp.quit()
        else:
            super().keyPressEvent(event)
            
    def closeEvent(self, event):
        """Handle window close event"""
        # Save window position
        self.config['window']['x'] = self.x()
        self.config['window']['y'] = self.y()
        self.config['window']['width'] = self.width()
        self.config['window']['height'] = self.height()
        self.save_config()
        
        # Stop OCR thread
        self.stop_ocr()
        
        # Hide to tray instead of closing
        if self.tray_icon and self.tray_icon.isVisible():
            self.hide()
            event.ignore()
        else:
            event.accept()


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Keep app running when window is closed
    
    # Check dependencies
    try:
        import mss
        from tesseract_timeout_fix_working import WorkingFastScreenOCR
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please install required packages:")
        print("pip install mss")
        print("Ensure tesseract_timeout_fix_working.py is available")
        return 1
    
    try:
        # Create overlay window
        overlay = OCROverlayWindow()
        overlay.show()
        
        print("🚀 Discord OCR Overlay started!")
        print("💡 Right-click system tray icon for settings")
        print("💡 Press ESC to hide, F1 for settings")
        print("💡 Text will appear when detected in capture region")
        
        # Run application
        return app.exec_()
        
    except Exception as e:
        print(f"❌ Error starting overlay: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())