#!/usr/bin/env python3
"""
GUI Chat Window for Screenshare LLM Assistant
Real-time LLM interaction window with OCR status and keystroke monitoring
"""

import sys
import json
import time
import threading
from datetime import datetime
from typing import Dict, Optional, Callable

try:
    from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                QHBoxLayout, QTextEdit, QLineEdit, QPushButton, 
                                QLabel, QFrame, QSplitter, QCheckBox, QGroupBox,
                                QProgressBar, QSystemTrayIcon, QMenu, QAction)
    from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread
    from PyQt5.QtGui import QFont, QPalette, QColor, QIcon, QPixmap
    PYQT5_AVAILABLE = True
except ImportError:
    PYQT5_AVAILABLE = False


class LLMResponseSignal(QObject):
    """Signal emitter for thread-safe LLM responses"""
    new_response = pyqtSignal(str)
    ocr_update = pyqtSignal(dict)
    keystroke_update = pyqtSignal(dict)


class ScreenshareGUI(QMainWindow):
    """Main GUI window for screenshare assistant"""
    
    def __init__(self, config: Dict):
        super().__init__()
        
        if not PYQT5_AVAILABLE:
            raise RuntimeError("PyQt5 not available")
            
        self.config = config
        self.gui_config = config.get('gui', {})
        
        # Signal handler for thread-safe updates
        self.signals = LLMResponseSignal()
        self.signals.new_response.connect(self.add_llm_response)
        self.signals.ocr_update.connect(self.update_ocr_status)
        self.signals.keystroke_update.connect(self.update_keystroke_status)
        
        # State tracking
        self.llm_query_callback: Optional[Callable] = None
        self.keystroke_toggle_callback: Optional[Callable] = None
        
        # Setup UI
        self.setup_ui()
        self.setup_theme()
        self.setup_system_tray()
        
        # Auto-update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.refresh_status)
        self.update_timer.start(1000)  # Update every second
        
    def setup_ui(self):
        """Setup the user interface"""
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Window properties
        self.setWindowTitle("🤖 Screenshare LLM Assistant")
        self.setGeometry(
            self.gui_config.get('window_x', 50),
            self.gui_config.get('window_y', 50),
            self.gui_config.get('window_width', 450),
            self.gui_config.get('window_height', 600)
        )
        
        # Always on top if configured
        if self.gui_config.get('always_on_top', True):
            self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Window)
        
        # Create main splitter
        splitter = QSplitter(Qt.Vertical)
        layout.addWidget(splitter)
        
        # Top section: OCR Status Panel
        self.create_ocr_status_panel(splitter)
        
        # Middle section: LLM Chat Area
        self.create_chat_area(splitter)
        
        # Bottom section: Input and Controls
        self.create_input_controls(layout)
        
        # Set splitter proportions
        splitter.setSizes([120, 350, 50])
        
    def create_ocr_status_panel(self, parent):
        """Create OCR status monitoring panel"""
        status_group = QGroupBox("📊 OCR & System Status")
        status_layout = QVBoxLayout(status_group)
        
        # OCR metrics
        ocr_frame = QFrame()
        ocr_layout = QHBoxLayout(ocr_frame)
        
        self.fps_label = QLabel("FPS: --")
        self.regions_label = QLabel("Regions: --")
        self.last_update_label = QLabel("Last: --")
        
        ocr_layout.addWidget(QLabel("🎥"))
        ocr_layout.addWidget(self.fps_label)
        ocr_layout.addWidget(QLabel("|"))
        ocr_layout.addWidget(self.regions_label)
        ocr_layout.addWidget(QLabel("|"))
        ocr_layout.addWidget(self.last_update_label)
        ocr_layout.addStretch()
        
        # OCR Progress bar
        self.ocr_progress = QProgressBar()
        self.ocr_progress.setRange(0, 100)
        self.ocr_progress.setValue(0)
        self.ocr_progress.setTextVisible(False)
        self.ocr_progress.setMaximumHeight(8)
        
        # Keystroke status
        keystroke_frame = QFrame()
        keystroke_layout = QHBoxLayout(keystroke_frame)
        
        self.keystroke_toggle = QCheckBox("🎹 Keystroke Logging")
        self.keystroke_toggle.toggled.connect(self.toggle_keystroke_logging)
        
        self.keystroke_status = QLabel("Disabled")
        self.keystroke_counter = QLabel("Keys: 0")
        
        keystroke_layout.addWidget(self.keystroke_toggle)
        keystroke_layout.addWidget(self.keystroke_status)
        keystroke_layout.addWidget(QLabel("|"))
        keystroke_layout.addWidget(self.keystroke_counter)
        keystroke_layout.addStretch()
        
        # LLM Status
        llm_frame = QFrame()
        llm_layout = QHBoxLayout(llm_frame)
        
        self.llm_status = QLabel("🤖 LLM: Disconnected")
        self.llm_model = QLabel(f"Model: {self.config.get('llm', {}).get('model', 'Unknown')}")
        
        llm_layout.addWidget(self.llm_status)
        llm_layout.addWidget(QLabel("|"))
        llm_layout.addWidget(self.llm_model)
        llm_layout.addStretch()
        
        # Add all to status layout
        status_layout.addWidget(ocr_frame)
        status_layout.addWidget(self.ocr_progress)
        status_layout.addWidget(keystroke_frame)
        status_layout.addWidget(llm_frame)
        
        parent.addWidget(status_group)
        
    def create_chat_area(self, parent):
        """Create LLM chat display area"""
        chat_group = QGroupBox("💬 LLM Analysis & Chat")
        chat_layout = QVBoxLayout(chat_group)
        
        # Main chat display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setPlaceholderText("🤖 AI responses will appear here as screen content is analyzed...\n\n💡 Start Discord screenshare to begin OCR analysis")
        
        # Set font
        font = QFont("Consolas", self.gui_config.get('font_size', 10))
        self.chat_display.setFont(font)
        
        chat_layout.addWidget(self.chat_display)
        parent.addWidget(chat_group)
        
    def create_input_controls(self, parent_layout):
        """Create user input and control buttons"""
        # Input frame
        input_frame = QFrame()
        input_layout = QHBoxLayout(input_frame)
        
        # User input
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Ask about screen content or type your question...")
        self.user_input.returnPressed.connect(self.send_user_query)
        
        # Send button
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_user_query)
        self.send_button.setMaximumWidth(80)
        
        # Clear button
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_chat)
        self.clear_button.setMaximumWidth(60)
        
        input_layout.addWidget(self.user_input)
        input_layout.addWidget(self.send_button)
        input_layout.addWidget(self.clear_button)
        
        parent_layout.addWidget(input_frame)
        
    def setup_theme(self):
        """Apply dark theme"""
        if self.gui_config.get('theme') == 'dark':
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QGroupBox {
                    font-weight: bold;
                    border: 1px solid #555555;
                    margin-top: 10px;
                    padding-top: 10px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                }
                QTextEdit {
                    background-color: #1e1e1e;
                    color: #ffffff;
                    border: 1px solid #555555;
                    selection-background-color: #0078d4;
                }
                QLineEdit {
                    background-color: #1e1e1e;
                    color: #ffffff;
                    border: 1px solid #555555;
                    padding: 5px;
                }
                QPushButton {
                    background-color: #0078d4;
                    color: #ffffff;
                    border: none;
                    padding: 5px 10px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #106ebe;
                }
                QPushButton:pressed {
                    background-color: #005a9e;
                }
                QLabel {
                    color: #ffffff;
                }
                QCheckBox {
                    color: #ffffff;
                }
                QProgressBar {
                    border: 1px solid #555555;
                    background-color: #1e1e1e;
                }
                QProgressBar::chunk {
                    background-color: #0078d4;
                }
            """)
            
        # Set opacity
        opacity = self.gui_config.get('opacity', 0.95)
        self.setWindowOpacity(opacity)
        
    def setup_system_tray(self):
        """Setup system tray icon and menu"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
            
        # Create tray icon
        self.tray_icon = QSystemTrayIcon(self)
        
        # Create icon (simple text-based icon if no image available)
        pixmap = QPixmap(16, 16)
        pixmap.fill(QColor(0, 120, 212))  # Blue color
        icon = QIcon(pixmap)
        self.tray_icon.setIcon(icon)
        
        # Create tray menu
        tray_menu = QMenu()
        
        show_action = QAction("Show Window", self)
        show_action.triggered.connect(self.show)
        
        hide_action = QAction("Hide Window", self)
        hide_action.triggered.connect(self.hide)
        
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.close)
        
        tray_menu.addAction(show_action)
        tray_menu.addAction(hide_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
        # Tray icon click behavior
        self.tray_icon.activated.connect(self.tray_icon_activated)
        
    def tray_icon_activated(self, reason):
        """Handle tray icon activation"""
        if reason == QSystemTrayIcon.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.raise_()
                self.activateWindow()
                
    def set_llm_query_callback(self, callback: Callable):
        """Set callback for LLM queries"""
        self.llm_query_callback = callback
        
    def set_keystroke_toggle_callback(self, callback: Callable):
        """Set callback for keystroke logging toggle"""
        self.keystroke_toggle_callback = callback
        
    def send_user_query(self):
        """Send user query to LLM"""
        query = self.user_input.text().strip()
        if not query:
            return
            
        # Display user query
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.chat_display.append(f"\n<b>[{timestamp}] 👤 You:</b> {query}")
        
        # Clear input
        self.user_input.clear()
        
        # Send to LLM if callback is set
        if self.llm_query_callback:
            threading.Thread(target=self._query_llm_thread, args=(query,), daemon=True).start()
        else:
            self.add_llm_response("❌ LLM not connected")
            
    def _query_llm_thread(self, query: str):
        """Query LLM in separate thread"""
        try:
            response = self.llm_query_callback(query)
            if response:
                self.signals.new_response.emit(response)
            else:
                self.signals.new_response.emit("❌ No response from LLM")
        except Exception as e:
            self.signals.new_response.emit(f"❌ LLM Error: {str(e)}")
            
    def add_llm_response(self, response: str):
        """Add LLM response to chat display (thread-safe)"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.chat_display.append(f"\n<b>[{timestamp}] 🤖 AI:</b> {response}")
        
        # Auto-scroll to bottom
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def add_ocr_analysis(self, analysis: str):
        """Add OCR analysis to chat display"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.chat_display.append(f"\n<i>[{timestamp}] 👁️  OCR Analysis:</i> {analysis}")
        
        # Auto-scroll to bottom
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def update_ocr_status(self, status: Dict):
        """Update OCR status display"""
        fps = status.get('fps', 0)
        regions = status.get('active_regions', 0)
        last_update = status.get('last_update', 0)
        
        self.fps_label.setText(f"FPS: {fps:.1f}")
        self.regions_label.setText(f"Regions: {regions}")
        
        if last_update > 0:
            seconds_ago = time.time() - last_update
            if seconds_ago < 60:
                self.last_update_label.setText(f"Last: {seconds_ago:.0f}s ago")
            else:
                self.last_update_label.setText(f"Last: {seconds_ago/60:.1f}m ago")
        else:
            self.last_update_label.setText("Last: Never")
            
        # Update progress bar based on activity
        if seconds_ago < 5:
            self.ocr_progress.setValue(100)
        elif seconds_ago < 15:
            self.ocr_progress.setValue(70)
        elif seconds_ago < 30:
            self.ocr_progress.setValue(40)
        else:
            self.ocr_progress.setValue(10)
            
        # Update LLM status
        if fps > 0:
            self.llm_status.setText("🤖 LLM: Active")
        else:
            self.llm_status.setText("🤖 LLM: Idle")
            
    def update_keystroke_status(self, status: Dict):
        """Update keystroke logging status"""
        enabled = status.get('enabled', False)
        running = status.get('running', False)
        key_count = status.get('key_count', 0)
        
        # Update checkbox without triggering signal
        self.keystroke_toggle.blockSignals(True)
        self.keystroke_toggle.setChecked(enabled and running)
        self.keystroke_toggle.blockSignals(False)
        
        if enabled and running:
            self.keystroke_status.setText("Active")
        elif enabled:
            self.keystroke_status.setText("Enabled")
        else:
            self.keystroke_status.setText("Disabled")
            
        self.keystroke_counter.setText(f"Keys: {key_count}")
        
    def toggle_keystroke_logging(self, checked: bool):
        """Toggle keystroke logging"""
        if self.keystroke_toggle_callback:
            self.keystroke_toggle_callback(checked)
            
    def clear_chat(self):
        """Clear chat display"""
        self.chat_display.clear()
        self.chat_display.append("💬 Chat cleared. Continue with your questions about screen content...")
        
    def refresh_status(self):
        """Refresh status displays periodically"""
        # This would normally be called by external status updates
        # For now, just update the timestamp displays
        pass
        
    def closeEvent(self, event):
        """Handle window close event"""
        if hasattr(self, 'tray_icon') and self.tray_icon.isVisible():
            # Hide to tray instead of closing
            self.hide()
            event.ignore()
        else:
            event.accept()
            
    def show_notification(self, title: str, message: str):
        """Show system tray notification"""
        if hasattr(self, 'tray_icon') and self.tray_icon.isVisible():
            self.tray_icon.showMessage(title, message, QSystemTrayIcon.Information, 3000)


def main():
    """Test GUI window"""
    app = QApplication(sys.argv)
    
    # Sample config
    config = {
        "gui": {
            "theme": "dark",
            "always_on_top": True,
            "window_x": 100,
            "window_y": 100,
            "window_width": 450,
            "window_height": 600,
            "font_size": 10,
            "opacity": 0.95
        },
        "llm": {
            "model": "llama3.2:latest"
        }
    }
    
    # Create window
    window = ScreenshareGUI(config)
    window.show()
    
    # Test LLM callback
    def test_llm_query(query):
        time.sleep(1)  # Simulate processing
        return f"Test response to: {query}"
    
    window.set_llm_query_callback(test_llm_query)
    
    # Test status updates
    def update_test_status():
        window.signals.ocr_update.emit({
            'fps': 3.2,
            'active_regions': 2,
            'last_update': time.time()
        })
        
        window.signals.keystroke_update.emit({
            'enabled': True,
            'running': True,
            'key_count': 1234
        })
        
    # Update status every 2 seconds for demo
    timer = QTimer()
    timer.timeout.connect(update_test_status)
    timer.start(2000)
    
    # Add some sample LLM responses
    window.add_llm_response("🚀 Screenshare assistant started! I can see your screen content.")
    window.add_ocr_analysis("Detected terminal window with Python code")
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()