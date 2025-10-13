#!/usr/bin/env python3
"""
Screenshare LLM Assistant Launcher
Main integration script that coordinates all components
"""

import sys
import os
import json
import signal
import time
import threading
from pathlib import Path
from typing import Dict, Optional

# Add the current directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from gui_chat_window import ScreenshareGUI, QApplication
    from llm_ocr_bridge import LLMOCRBridge, ScreenContext, OCRFrame
    from keystroke_logger import KeystrokeLogger
    from health_monitor import HealthMonitor
    import requests
    GUI_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    GUI_AVAILABLE = False


class ScreenshareAssistant:
    """Main orchestrator for all screenshare assistant components"""
    
    def __init__(self, config_path: Optional[str] = None):
        # Load configuration
        self.config = self.load_config(config_path)
        
        # Component instances
        self.ocr_bridge: Optional[LLMOCRBridge] = None
        self.keystroke_logger: Optional[KeystrokeLogger] = None
        self.health_monitor: Optional[HealthMonitor] = None
        self.gui: Optional[ScreenshareGUI] = None
        self.gui_app: Optional[QApplication] = None
        
        # State tracking
        self.running = False
        self.shutdown_initiated = False
        
        # LLM configuration
        self.llm_config = self.config.get('llm', {})
        
        # Setup signal handlers
        self.setup_signal_handlers()
        
    def load_config(self, config_path: Optional[str] = None) -> Dict:
        """Load configuration from file"""
        if config_path:
            config_file = Path(config_path)
        else:
            config_file = Path.home() / ".config/screenshare-assistant/config.json"
        
        try:
            with open(config_file) as f:
                config = json.load(f)
                print(f"✅ Loaded configuration from {config_file}")
                return config
        except FileNotFoundError:
            print(f"❌ Configuration file not found: {config_file}")
            print("💡 Use default configuration or create config file")
            return self.get_default_config()
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in configuration file: {e}")
            return self.get_default_config()
    
    def get_default_config(self) -> Dict:
        """Get default configuration"""
        return {
            "llm": {
                "provider": "ollama",
                "model": "llama3.2:latest",
                "api_url": "http://localhost:11434/api/generate",
                "max_tokens": 400,
                "temperature": 0.3
            },
            "ocr": {
                "regions": [
                    {"name": "main_screen", "x": 100, "y": 100, "width": 1200, "height": 800}
                ],
                "fps": 4,
                "quality_mode_interval": 8
            },
            "keystroke_logging": {
                "enabled": False
            },
            "gui": {
                "theme": "dark",
                "always_on_top": True
            },
            "health": {
                "heartbeat_interval": 5
            }
        }
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            print(f"\n🛑 Received signal {signum}, initiating graceful shutdown...")
            self.shutdown()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def query_llm(self, prompt: str) -> Optional[str]:
        """Query the configured LLM service"""
        try:
            if self.llm_config.get("provider") == "ollama":
                return self.query_ollama(prompt)
            elif self.llm_config.get("provider") == "openai":
                return self.query_openai(prompt)
            else:
                return f"Local LLM response to: {prompt}"
        except Exception as e:
            print(f"❌ LLM query error: {e}")
            return f"Error: {str(e)}"
    
    def query_ollama(self, prompt: str) -> Optional[str]:
        """Query Ollama local LLM"""
        try:
            payload = {
                "model": self.llm_config["model"],
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.llm_config.get("temperature", 0.3),
                    "num_predict": self.llm_config.get("max_tokens", 400)
                }
            }
            
            response = requests.post(
                self.llm_config["api_url"],
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "").strip()
            else:
                return f"Ollama API error: {response.status_code}"
                
        except Exception as e:
            return f"Ollama query error: {e}"
    
    def query_openai(self, prompt: str) -> Optional[str]:
        """Query OpenAI API (placeholder)"""
        return f"OpenAI response to: {prompt[:50]}..."
    
    def on_ocr_frame_detected(self, frame: OCRFrame):
        """Handle OCR frame detection"""
        # Update health metrics
        if self.health_monitor:
            self.health_monitor.update_metric('last_ocr_time', frame.timestamp)
            self.health_monitor.update_metric('current_fps', 1.0 / max(frame.processing_time, 0.1))
        
        # Update GUI
        if self.gui:
            # Show brief OCR detection in GUI occasionally
            if frame.frame_id % 20 == 0:  # Every 20th frame
                self.gui.add_ocr_analysis(f"Detected: {frame.text[:100]}...")
    
    def on_context_update(self, context: ScreenContext):
        """Handle context updates from OCR bridge"""
        # Update health metrics
        if self.health_monitor:
            self.health_monitor.update_metric('last_context_update', time.time())
            self.health_monitor.update_metric('queue_depth', len(context.text_history))
        
        # Update GUI status
        if self.gui:
            status_update = {
                'fps': context.session_stats.get('frames_per_minute', 0) / 60,
                'active_regions': len(context.active_regions),
                'last_update': time.time()
            }
            self.gui.signals.ocr_update.emit(status_update)
        
        # Analyze context with LLM periodically
        if len(context.recent_changes) >= 3 and context.current_text:
            analysis = self.analyze_screen_context(context)
            if analysis and self.gui:
                self.gui.add_llm_response(f"📊 Screen Analysis: {analysis}")
    
    def analyze_screen_context(self, context: ScreenContext) -> Optional[str]:
        """Analyze screen context with LLM"""
        try:
            recent_activity = " -> ".join(context.recent_changes[-3:])
            
            prompt = f"""Current screen shows: "{context.current_text[:500]}"

Recent activity: {recent_activity}

Briefly describe what the user is currently doing and provide one helpful suggestion."""
            
            return self.query_llm(prompt)
        except Exception as e:
            print(f"❌ Context analysis error: {e}")
            return None
    
    def toggle_keystroke_logging(self, enabled: bool):
        """Toggle keystroke logging on/off"""
        if not self.keystroke_logger:
            return
        
        if enabled:
            success = self.keystroke_logger.start()
            print(f"🎹 Keystroke logging: {'started' if success else 'failed to start'}")
        else:
            self.keystroke_logger.stop()
            print("🎹 Keystroke logging stopped")
        
        # Update GUI status
        if self.gui and self.keystroke_logger:
            stats = self.keystroke_logger.get_stats()
            self.gui.signals.keystroke_update.emit(stats)
    
    def start_components(self):
        """Start all assistant components"""
        print("🚀 Starting Screenshare LLM Assistant components...")
        
        # Start health monitor first
        self.health_monitor = HealthMonitor(self.config)
        self.health_monitor.start()
        print("✅ Health monitor started")
        
        # Start OCR bridge
        self.ocr_bridge = LLMOCRBridge(config_file=None)
        self.ocr_bridge.config = {
            'capture': self.config.get('ocr', {}),
            'ocr': self.config.get('ocr', {}),
            'buffer': {'max_frames': 100, 'context_window': 10, 'change_threshold': 0.1},
            'llm': {'update_interval': 1.0},
            'logging': {'level': 'INFO', 'file': 'llm_ocr_bridge.log'}
        }
        
        # Add callbacks
        self.ocr_bridge.add_text_callback(self.on_ocr_frame_detected)
        self.ocr_bridge.add_context_callback(self.on_context_update)
        
        self.ocr_bridge.start()
        print("✅ OCR bridge started")
        
        # Start keystroke logger (but don't enable by default)
        self.keystroke_logger = KeystrokeLogger(self.config.get('keystroke_logging', {}))
        print("✅ Keystroke logger initialized")
        
        # Start GUI if available
        if GUI_AVAILABLE:
            self.gui_app = QApplication(sys.argv)
            self.gui = ScreenshareGUI(self.config)
            
            # Set GUI callbacks
            self.gui.set_llm_query_callback(self.query_llm)
            self.gui.set_keystroke_toggle_callback(self.toggle_keystroke_logging)
            
            self.gui.show()
            print("✅ GUI window started")
            
            # Initial GUI status update
            if self.keystroke_logger:
                stats = self.keystroke_logger.get_stats()
                self.gui.signals.keystroke_update.emit(stats)
        
        self.running = True
        
        # Update health metrics
        if self.health_monitor:
            self.health_monitor.update_metric('gui_active', GUI_AVAILABLE)
        
        print("🎉 All components started successfully!")
        print("💡 Start Discord screenshare to begin OCR analysis")
        
        if GUI_AVAILABLE:
            print("💡 Use the GUI window to interact with the AI assistant")
        
        return True
    
    def stop_components(self):
        """Stop all components gracefully"""
        print("🛑 Stopping assistant components...")
        
        # Stop OCR bridge
        if self.ocr_bridge:
            self.ocr_bridge.stop()
            print("✅ OCR bridge stopped")
        
        # Stop keystroke logger
        if self.keystroke_logger:
            self.keystroke_logger.stop()
            print("✅ Keystroke logger stopped")
        
        # Stop health monitor
        if self.health_monitor:
            self.health_monitor.stop()
            print("✅ Health monitor stopped")
        
        # Close GUI
        if self.gui:
            self.gui.close()
            print("✅ GUI closed")
        
        if self.gui_app:
            self.gui_app.quit()
        
        self.running = False
        print("🏁 All components stopped")
    
    def run(self):
        """Main run loop"""
        try:
            if not self.start_components():
                return 1
            
            if GUI_AVAILABLE and self.gui_app:
                # Run GUI event loop
                return self.gui_app.exec_()
            else:
                # Run without GUI
                print("🔄 Running in headless mode (no GUI)")
                try:
                    while self.running:
                        time.sleep(1)
                except KeyboardInterrupt:
                    pass
                
                return 0
                
        except Exception as e:
            print(f"❌ Fatal error: {e}")
            return 1
        finally:
            self.stop_components()
    
    def shutdown(self):
        """Initiate graceful shutdown"""
        if self.shutdown_initiated:
            return
        
        self.shutdown_initiated = True
        
        # Stop components in separate thread to avoid blocking
        def shutdown_thread():
            self.stop_components()
            if self.gui_app:
                self.gui_app.quit()
        
        threading.Thread(target=shutdown_thread, daemon=True).start()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Screenshare LLM Assistant")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--headless", action="store_true", help="Run without GUI")
    parser.add_argument("--test-llm", help="Test LLM with a query")
    
    args = parser.parse_args()
    
    # Override GUI availability if headless requested
    if args.headless:
        global GUI_AVAILABLE
        GUI_AVAILABLE = False
    
    # Create assistant
    assistant = ScreenshareAssistant(args.config)
    
    # Test LLM if requested
    if args.test_llm:
        print(f"🧠 Testing LLM with query: {args.test_llm}")
        response = assistant.query_llm(args.test_llm)
        print(f"🤖 Response: {response}")
        return 0
    
    print("🤖 Screenshare LLM Assistant")
    print("=" * 50)
    print(f"📁 Config: {assistant.config.get('llm', {}).get('provider', 'unknown')} LLM")
    print(f"🎥 OCR: {len(assistant.config.get('ocr', {}).get('regions', []))} regions")
    print(f"🎹 Keylog: {'enabled' if assistant.config.get('keystroke_logging', {}).get('enabled') else 'disabled'}")
    print(f"🖥️  GUI: {'available' if GUI_AVAILABLE else 'headless mode'}")
    print("=" * 50)
    
    # Run assistant
    return assistant.run()


if __name__ == "__main__":
    exit(main())