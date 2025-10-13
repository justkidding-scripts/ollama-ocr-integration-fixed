#!/usr/bin/env python3
"""
Health Monitor for Screenshare LLM Assistant
Tracks system health, performance metrics, and provides heartbeat monitoring
"""

import json
import time
import threading
import logging
import psutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
from logging.handlers import RotatingFileHandler
import queue
import subprocess


class HealthMonitor:
    """Monitors health and performance of screenshare assistant components"""
    
    def __init__(self, config: Dict):
        self.config = config.get('health', {})
        self.logging_config = config.get('logging', {})
        
        # Health data storage
        self.health_file = Path.home() / ".local/share/screenshare-assistant/health.json"
        self.health_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Metrics tracking
        self.metrics = {
            'session_start': time.time(),
            'last_ocr_time': 0,
            'last_context_update': 0,
            'current_fps': 0,
            'queue_depth': 0,
            'keystroke_count': 0,
            'llm_queries': 0,
            'gui_active': False,
            'memory_usage': 0,
            'cpu_usage': 0,
            'last_heartbeat': time.time()
        }
        
        # Threading
        self.running = False
        self.heartbeat_interval = self.config.get('heartbeat_interval', 5)
        self.metrics_queue = queue.Queue()
        
        # Setup logging
        self.setup_logging()
        
        # Performance thresholds
        self.max_stale_seconds = self.config.get('max_stale_seconds', 30)
        self.min_fps_threshold = self.config.get('min_fps_threshold', 1.0)
        self.max_queue_depth = self.config.get('max_queue_depth', 50)
        
    def setup_logging(self):
        """Setup health monitoring logging"""
        log_dir = Path.home() / ".local/share/screenshare-assistant/logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger('health_monitor')
        self.logger.setLevel(getattr(logging, self.logging_config.get('level', 'INFO')))
        
        # File handler with rotation
        log_file = log_dir / "health.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=self.logging_config.get('max_log_mb', 10) * 1024 * 1024,
            backupCount=self.logging_config.get('backup_count', 5)
        )
        
        # JSON formatter if specified
        if self.logging_config.get('format') == 'json':
            formatter = JsonFormatter()
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # Console handler for debug
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
    def update_metric(self, key: str, value: Any):
        """Update a metric value (thread-safe)"""
        try:
            self.metrics_queue.put((key, value, time.time()), block=False)
        except queue.Full:
            # Queue full, skip this update
            pass
    
    def process_metric_updates(self):
        """Process queued metric updates"""
        updates_processed = 0
        
        while not self.metrics_queue.empty() and updates_processed < 100:
            try:
                key, value, timestamp = self.metrics_queue.get(block=False)
                self.metrics[key] = value
                self.metrics['last_update'] = timestamp
                updates_processed += 1
            except queue.Empty:
                break
                
        return updates_processed
    
    def collect_system_metrics(self):
        """Collect system performance metrics"""
        try:
            # CPU and memory usage
            self.metrics['cpu_usage'] = psutil.cpu_percent(interval=0.1)
            
            process = psutil.Process()
            memory_info = process.memory_info()
            self.metrics['memory_usage'] = memory_info.rss / 1024 / 1024  # MB
            
            # Disk usage for log directory
            log_dir = Path.home() / ".local/share/screenshare-assistant/logs"
            if log_dir.exists():
                disk_usage = sum(f.stat().st_size for f in log_dir.rglob('*') if f.is_file())
                self.metrics['log_disk_usage'] = disk_usage / 1024 / 1024  # MB
            
            # Network connectivity (check if Ollama is reachable)
            try:
                result = subprocess.run([
                    'curl', '-s', '--connect-timeout', '2', 
                    'http://localhost:11434/api/version'
                ], capture_output=True, timeout=3)
                self.metrics['llm_connectivity'] = result.returncode == 0
            except:
                self.metrics['llm_connectivity'] = False
                
        except Exception as e:
            self.logger.error(f"Failed to collect system metrics: {e}")
    
    def calculate_health_score(self) -> float:
        """Calculate overall health score (0-100)"""
        score = 100.0
        current_time = time.time()
        
        # OCR freshness penalty
        ocr_staleness = current_time - self.metrics.get('last_ocr_time', 0)
        if ocr_staleness > self.max_stale_seconds:
            score -= min(50, ocr_staleness / self.max_stale_seconds * 25)
        
        # FPS penalty
        current_fps = self.metrics.get('current_fps', 0)
        if current_fps < self.min_fps_threshold:
            score -= 20
        
        # Queue depth penalty
        queue_depth = self.metrics.get('queue_depth', 0)
        if queue_depth > self.max_queue_depth:
            score -= 15
        
        # Memory usage penalty (if over 500MB)
        memory_usage = self.metrics.get('memory_usage', 0)
        if memory_usage > 500:
            score -= min(10, (memory_usage - 500) / 100 * 5)
        
        # CPU usage penalty (if over 80%)
        cpu_usage = self.metrics.get('cpu_usage', 0)
        if cpu_usage > 80:
            score -= min(10, (cpu_usage - 80) / 20 * 10)
        
        # LLM connectivity bonus/penalty
        if self.metrics.get('llm_connectivity', False):
            score += 5
        else:
            score -= 10
        
        return max(0, min(100, score))
    
    def write_health_data(self):
        """Write current health data to file"""
        try:
            # Process any pending metric updates
            self.process_metric_updates()
            
            # Collect fresh system metrics
            self.collect_system_metrics()
            
            # Calculate health score
            health_score = self.calculate_health_score()
            
            # Build health data
            health_data = {
                'timestamp': time.time(),
                'datetime': datetime.now().isoformat(),
                'health_score': health_score,
                'metrics': self.metrics.copy(),
                'thresholds': {
                    'max_stale_seconds': self.max_stale_seconds,
                    'min_fps_threshold': self.min_fps_threshold,
                    'max_queue_depth': self.max_queue_depth
                },
                'status': self.get_status_summary()
            }
            
            # Update heartbeat
            self.metrics['last_heartbeat'] = time.time()
            health_data['metrics']['last_heartbeat'] = self.metrics['last_heartbeat']
            
            # Write to file atomically
            temp_file = self.health_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(health_data, f, indent=2)
            
            temp_file.replace(self.health_file)
            
            # Log health status periodically
            if int(time.time()) % 60 == 0:  # Every minute
                self.logger.info(f"Health score: {health_score:.1f}, "
                               f"FPS: {self.metrics.get('current_fps', 0):.1f}, "
                               f"Memory: {self.metrics.get('memory_usage', 0):.1f}MB")
            
        except Exception as e:
            self.logger.error(f"Failed to write health data: {e}")
    
    def get_status_summary(self) -> Dict[str, str]:
        """Get human-readable status summary"""
        current_time = time.time()
        ocr_staleness = current_time - self.metrics.get('last_ocr_time', 0)
        
        return {
            'ocr_status': 'active' if ocr_staleness < 10 else 'stale' if ocr_staleness < 30 else 'dead',
            'fps_status': 'good' if self.metrics.get('current_fps', 0) >= self.min_fps_threshold else 'low',
            'memory_status': 'normal' if self.metrics.get('memory_usage', 0) < 300 else 'high',
            'llm_status': 'connected' if self.metrics.get('llm_connectivity', False) else 'disconnected',
            'queue_status': 'normal' if self.metrics.get('queue_depth', 0) < 20 else 'high'
        }
    
    def heartbeat_loop(self):
        """Main heartbeat loop"""
        while self.running:
            try:
                self.write_health_data()
                time.sleep(self.heartbeat_interval)
            except Exception as e:
                self.logger.error(f"Heartbeat loop error: {e}")
                time.sleep(5)  # Avoid tight error loop
    
    def start(self):
        """Start health monitoring"""
        if self.running:
            self.logger.warning("Health monitor already running")
            return
        
        self.running = True
        self.metrics['session_start'] = time.time()
        
        # Start heartbeat thread
        self.heartbeat_thread = threading.Thread(target=self.heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()
        
        self.logger.info("Health monitor started")
        
    def stop(self):
        """Stop health monitoring"""
        if not self.running:
            return
        
        self.running = False
        
        # Final health write
        self.write_health_data()
        
        # Wait for thread to finish
        if hasattr(self, 'heartbeat_thread'):
            self.heartbeat_thread.join(timeout=2)
        
        self.logger.info("Health monitor stopped")
    
    def cleanup_old_logs(self):
        """Clean up old log files"""
        try:
            log_dir = Path.home() / ".local/share/screenshare-assistant/logs"
            if not log_dir.exists():
                return
            
            # Clean up keystroke logs older than max_log_files
            from keystroke_logger import KeystrokeLogger
            keystroke_config = {'max_log_files': 30}  # From config
            dummy_logger = KeystrokeLogger(keystroke_config)
            dummy_logger.cleanup_old_logs()
            
            # Clean up health logs older than 30 days
            cutoff_date = datetime.now() - timedelta(days=30)
            
            for log_file in log_dir.glob("health.log.*"):
                try:
                    if log_file.stat().st_mtime < cutoff_date.timestamp():
                        log_file.unlink()
                        self.logger.info(f"Removed old health log: {log_file.name}")
                except Exception as e:
                    self.logger.error(f"Failed to remove old log {log_file}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Failed to cleanup old logs: {e}")


class JsonFormatter(logging.Formatter):
    """JSON log formatter"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry)


def health_check_script() -> bool:
    """Standalone health check script for systemd monitoring"""
    try:
        health_file = Path.home() / ".local/share/screenshare-assistant/health.json"
        
        if not health_file.exists():
            print("❌ Health file not found")
            return False
        
        # Check file age
        file_age = time.time() - health_file.stat().st_mtime
        if file_age > 60:  # 1 minute
            print(f"❌ Health file too old: {file_age:.0f}s")
            return False
        
        # Read health data
        with open(health_file) as f:
            health_data = json.load(f)
        
        health_score = health_data.get('health_score', 0)
        metrics = health_data.get('metrics', {})
        status = health_data.get('status', {})
        
        # Check health score
        if health_score < 50:
            print(f"❌ Low health score: {health_score:.1f}")
            return False
        
        # Check critical metrics
        current_time = time.time()
        last_ocr = metrics.get('last_ocr_time', 0)
        
        if current_time - last_ocr > 120:  # 2 minutes
            print(f"❌ OCR stale for {current_time - last_ocr:.0f}s")
            return False
        
        print(f"✅ Health OK: {health_score:.1f} score, OCR active, {status.get('llm_status', 'unknown')} LLM")
        return True
        
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False


def main():
    """Test health monitor"""
    import signal
    
    # Sample config
    config = {
        'health': {
            'heartbeat_interval': 2,
            'max_stale_seconds': 10,
            'min_fps_threshold': 1.0
        },
        'logging': {
            'level': 'INFO',
            'format': 'json'
        }
    }
    
    monitor = HealthMonitor(config)
    
    def signal_handler(sig, frame):
        print("\nStopping health monitor...")
        monitor.stop()
        exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start monitoring
    monitor.start()
    
    print("🏥 Health monitor started")
    print("💡 Simulating metrics updates...")
    
    # Simulate some activity
    try:
        counter = 0
        while True:
            time.sleep(1)
            counter += 1
            
            # Simulate OCR activity
            monitor.update_metric('last_ocr_time', time.time())
            monitor.update_metric('current_fps', 2.5 + (counter % 5) * 0.5)
            monitor.update_metric('queue_depth', counter % 20)
            monitor.update_metric('keystroke_count', counter * 10)
            
            if counter % 5 == 0:
                print(f"📊 Metrics updated: FPS={monitor.metrics.get('current_fps', 0):.1f}, "
                      f"Queue={monitor.metrics.get('queue_depth', 0)}")
                
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        # Run as health check script
        exit(0 if health_check_script() else 1)
    else:
        # Run as test
        main()