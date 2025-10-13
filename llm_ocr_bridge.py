#!/usr/bin/env python3
"""
LLM OCR Bridge Module
Real-time OCR service that feeds screen content to LLMs for live analysis
"""

import asyncio
import json
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict
from queue import Queue, Empty
import logging

import mss
from PIL import Image
from tesseract_timeout_fix_working import WorkingFastScreenOCR, WorkingQuickOCR


@dataclass
class OCRFrame:
    """Single OCR frame with metadata"""
    timestamp: float
    text: str
    confidence: float
    region: Dict[str, int]
    processing_time: float
    frame_id: int
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class ScreenContext:
    """Aggregated screen context for LLM consumption"""
    current_text: str
    recent_changes: List[str]
    text_history: List[OCRFrame]
    active_regions: List[Dict[str, int]]
    session_stats: Dict[str, Any]
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


class LLMOCRBridge:
    """Main OCR bridge service for LLM integration"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = Path(config_file) if config_file else Path.home() / ".llm_ocr_config.json"
        self.config = self.load_config()
        
        # OCR engines
        self.fast_ocr = WorkingFastScreenOCR(timeout=self.config['ocr']['fast_timeout'])
        self.quality_ocr = WorkingQuickOCR(timeout=self.config['ocr']['quality_timeout'])
        
        # Screen capture
        self.sct = mss.mss()
        
        # State management
        self.running = False
        self.frame_counter = 0
        self.text_buffer = Queue(maxsize=self.config['buffer']['max_frames'])
        self.context_history = []
        self.last_text = ""
        self.session_start = time.time()
        
        # Callbacks for external integration
        self.text_callbacks: List[Callable[[OCRFrame], None]] = []
        self.context_callbacks: List[Callable[[ScreenContext], None]] = []
        
        # Logging
        self.setup_logging()
        
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        default_config = {
            "capture": {
                "regions": [
                    {"name": "main", "x": 100, "y": 100, "width": 800, "height": 600}
                ],
                "fps": 5,
                "quality_mode_interval": 10  # Use quality OCR every N frames
            },
            "ocr": {
                "fast_timeout": 2.0,
                "quality_timeout": 8.0,
                "min_text_length": 3,
                "confidence_threshold": 0.5
            },
            "buffer": {
                "max_frames": 100,
                "context_window": 10,
                "change_threshold": 0.1  # Minimum change to consider new content
            },
            "llm": {
                "update_interval": 1.0,  # Send context updates every N seconds
                "summarize_interval": 30.0,  # Create summaries every N seconds
                "max_context_length": 5000  # Max characters in context
            },
            "logging": {
                "level": "INFO",
                "file": "llm_ocr_bridge.log"
            }
        }
        
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    loaded = json.load(f)
                # Merge with defaults
                def merge_config(default, loaded):
                    for key, value in loaded.items():
                        if key in default:
                            if isinstance(default[key], dict) and isinstance(value, dict):
                                merge_config(default[key], value)
                            else:
                                default[key] = value
                merge_config(default_config, loaded)
        except Exception as e:
            print(f"Error loading config: {e}, using defaults")
            
        return default_config
    
    def save_config(self):
        """Save current configuration"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")
    
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=getattr(logging, self.config['logging']['level']),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.config['logging']['file']),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def add_text_callback(self, callback: Callable[[OCRFrame], None]):
        """Add callback for individual OCR frames"""
        self.text_callbacks.append(callback)
    
    def add_context_callback(self, callback: Callable[[ScreenContext], None]):
        """Add callback for aggregated context updates"""
        self.context_callbacks.append(callback)
    
    def capture_frame(self, region: Dict[str, int]) -> Optional[OCRFrame]:
        """Capture and process a single frame"""
        try:
            start_time = time.time()
            
            # Capture screen
            monitor_config = {
                "top": region['y'],
                "left": region['x'],
                "width": region['width'],
                "height": region['height']
            }
            
            screenshot = self.sct.grab(monitor_config)
            img = Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')
            
            # Choose OCR engine based on frame counter
            use_quality = (self.frame_counter % self.config['capture']['quality_mode_interval'] == 0)
            ocr_engine = self.quality_ocr if use_quality else self.fast_ocr
            
            # Extract text
            text = ocr_engine.extract_screen_text(img) if use_quality else ocr_engine.extract_screen_text(img)
            
            if not text or len(text) < self.config['ocr']['min_text_length']:
                return None
            
            processing_time = time.time() - start_time
            
            # Create OCR frame
            frame = OCRFrame(
                timestamp=time.time(),
                text=text.strip(),
                confidence=0.8 if use_quality else 0.6,  # Placeholder confidence
                region=region,
                processing_time=processing_time,
                frame_id=self.frame_counter
            )
            
            self.frame_counter += 1
            return frame
            
        except Exception as e:
            self.logger.error(f"Frame capture error: {e}")
            return None
    
    def process_frame(self, frame: OCRFrame) -> bool:
        """Process a captured frame and determine if it's significant"""
        # Check for meaningful changes
        text_similarity = self.calculate_similarity(frame.text, self.last_text)
        
        if text_similarity < (1.0 - self.config['buffer']['change_threshold']):
            # Significant change detected
            self.last_text = frame.text
            
            # Add to buffer
            try:
                self.text_buffer.put(frame, block=False)
            except:
                # Buffer full, remove oldest
                try:
                    self.text_buffer.get(block=False)
                    self.text_buffer.put(frame, block=False)
                except Empty:
                    pass
            
            # Notify callbacks
            for callback in self.text_callbacks:
                try:
                    callback(frame)
                except Exception as e:
                    self.logger.error(f"Callback error: {e}")
            
            return True
        
        return False
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity (simple implementation)"""
        if not text1 or not text2:
            return 0.0
        
        # Simple character-based similarity
        set1, set2 = set(text1.lower()), set(text2.lower())
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    def build_context(self) -> ScreenContext:
        """Build current screen context for LLM consumption"""
        # Get recent frames from buffer
        frames = []
        temp_queue = Queue()
        
        while not self.text_buffer.empty():
            try:
                frame = self.text_buffer.get(block=False)
                frames.append(frame)
                temp_queue.put(frame)
            except Empty:
                break
        
        # Restore frames to buffer
        while not temp_queue.empty():
            try:
                self.text_buffer.put(temp_queue.get(block=False))
            except:
                break
        
        # Sort by timestamp
        frames.sort(key=lambda f: f.timestamp)
        
        # Get recent window
        recent_frames = frames[-self.config['buffer']['context_window']:]
        
        # Build context
        current_text = recent_frames[-1].text if recent_frames else ""
        recent_changes = [f.text for f in recent_frames[-5:]]  # Last 5 changes
        
        # Calculate session stats
        session_duration = time.time() - self.session_start
        stats = {
            "session_duration": session_duration,
            "total_frames": self.frame_counter,
            "frames_per_minute": (self.frame_counter / session_duration) * 60 if session_duration > 0 else 0,
            "active_regions": len(self.config['capture']['regions']),
            "avg_processing_time": sum(f.processing_time for f in recent_frames) / len(recent_frames) if recent_frames else 0
        }
        
        context = ScreenContext(
            current_text=current_text,
            recent_changes=recent_changes,
            text_history=recent_frames,
            active_regions=self.config['capture']['regions'],
            session_stats=stats
        )
        
        return context
    
    def context_update_loop(self):
        """Background loop for sending context updates"""
        last_update = 0
        
        while self.running:
            try:
                current_time = time.time()
                
                if current_time - last_update >= self.config['llm']['update_interval']:
                    context = self.build_context()
                    
                    # Notify context callbacks
                    for callback in self.context_callbacks:
                        try:
                            callback(context)
                        except Exception as e:
                            self.logger.error(f"Context callback error: {e}")
                    
                    last_update = current_time
                
                time.sleep(0.1)  # Small delay to prevent high CPU usage
                
            except Exception as e:
                self.logger.error(f"Context update loop error: {e}")
                time.sleep(1)
    
    def capture_loop(self):
        """Main capture loop"""
        interval = 1.0 / self.config['capture']['fps']
        
        while self.running:
            try:
                loop_start = time.time()
                
                # Process all configured regions
                for region in self.config['capture']['regions']:
                    if not self.running:
                        break
                        
                    frame = self.capture_frame(region)
                    if frame:
                        self.process_frame(frame)
                
                # Frame rate limiting
                elapsed = time.time() - loop_start
                if elapsed < interval:
                    time.sleep(interval - elapsed)
                    
            except Exception as e:
                self.logger.error(f"Capture loop error: {e}")
                time.sleep(1)
    
    def start(self):
        """Start the OCR bridge service"""
        if self.running:
            return
        
        self.running = True
        self.session_start = time.time()
        
        # Start background threads
        self.capture_thread = threading.Thread(target=self.capture_loop, daemon=True)
        self.context_thread = threading.Thread(target=self.context_update_loop, daemon=True)
        
        self.capture_thread.start()
        self.context_thread.start()
        
        self.logger.info("LLM OCR Bridge started")
        print("🚀 LLM OCR Bridge started")
        print(f"📊 Monitoring {len(self.config['capture']['regions'])} regions at {self.config['capture']['fps']} FPS")
        
    def stop(self):
        """Stop the OCR bridge service"""
        if not self.running:
            return
        
        self.running = False
        
        # Wait for threads to finish
        if hasattr(self, 'capture_thread'):
            self.capture_thread.join(timeout=2)
        if hasattr(self, 'context_thread'):
            self.context_thread.join(timeout=2)
        
        self.logger.info("LLM OCR Bridge stopped")
        print("🛑 LLM OCR Bridge stopped")
    
    def get_current_context(self) -> ScreenContext:
        """Get current screen context (synchronous)"""
        return self.build_context()
    
    def get_recent_text(self, max_frames: int = 10) -> List[str]:
        """Get recent text extractions"""
        frames = []
        temp_queue = Queue()
        
        while not self.text_buffer.empty():
            try:
                frame = self.text_buffer.get(block=False)
                frames.append(frame)
                temp_queue.put(frame)
            except Empty:
                break
        
        # Restore frames
        while not temp_queue.empty():
            try:
                self.text_buffer.put(temp_queue.get(block=False))
            except:
                break
        
        # Return recent text
        frames.sort(key=lambda f: f.timestamp)
        return [f.text for f in frames[-max_frames:]]


# Example integration functions for different LLM services

def openai_integration_example(bridge: LLMOCRBridge):
    """Example OpenAI integration"""
    def on_context_update(context: ScreenContext):
        # Format context for OpenAI API
        prompt = f"""
        Current screen content: {context.current_text}
        
        Recent changes: {' -> '.join(context.recent_changes[-3:])}
        
        Session stats: {context.session_stats}
        
        Please analyze what the user is currently doing and provide helpful insights.
        """
        
        # Here you would call OpenAI API
        print(f"📤 Sending to OpenAI: {len(prompt)} chars")
        # response = openai.Completion.create(...)
        
    bridge.add_context_callback(on_context_update)


def local_llm_integration_example(bridge: LLMOCRBridge):
    """Example local LLM integration"""
    def on_text_frame(frame: OCRFrame):
        # Send individual frames to local LLM
        print(f"🤖 Frame {frame.frame_id}: {frame.text[:50]}...")
        # Send to local LLM via API/subprocess
        
    bridge.add_text_callback(on_text_frame)


def websocket_integration_example(bridge: LLMOCRBridge):
    """Example WebSocket integration for real-time LLM communication"""
    import asyncio
    import websockets
    import json
    
    async def websocket_handler():
        async with websockets.connect("ws://localhost:8765") as websocket:
            def on_context_update(context: ScreenContext):
                # Send context via WebSocket
                asyncio.create_task(websocket.send(context.to_json()))
            
            bridge.add_context_callback(on_context_update)
            
            # Keep connection alive
            await websocket.ping()


def main():
    """Example usage"""
    import signal
    
    # Create bridge
    bridge = LLMOCRBridge()
    
    # Add example integrations
    def on_text_update(frame: OCRFrame):
        print(f"📝 Text detected: {frame.text[:100]}...")
    
    def on_context_update(context: ScreenContext):
        print(f"🔄 Context update: {len(context.current_text)} chars, {len(context.recent_changes)} recent changes")
        
        # Example: Send to LLM every few updates
        if len(context.recent_changes) > 3:
            llm_prompt = f"""
            The user's screen currently shows: "{context.current_text}"
            
            Recent activity shows these text changes: {context.recent_changes}
            
            What is the user likely doing? Provide brief analysis.
            """
            print(f"🤖 LLM Prompt ready: {len(llm_prompt)} characters")
    
    bridge.add_text_callback(on_text_update)
    bridge.add_context_callback(on_context_update)
    
    # Handle shutdown
    def signal_handler(sig, frame):
        print("\n🛑 Shutting down...")
        bridge.stop()
        exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start service
    bridge.start()
    
    print("\n💡 LLM OCR Bridge running!")
    print("💡 Screen text will be captured and processed for LLM analysis")
    print("💡 Press Ctrl+C to stop")
    
    # Keep main thread alive
    try:
        while bridge.running:
            time.sleep(1)
    except KeyboardInterrupt:
        bridge.stop()


if __name__ == "__main__":
    main()