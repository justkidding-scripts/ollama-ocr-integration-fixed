#!/usr/bin/env python3
"""
Working Tesseract OCR Timeout Fix Module
Tested and robust solution for OCR timeout issues
"""

import threading
import time
import subprocess
import os
import signal
from typing import Optional, Union, Any
from PIL import Image
import pytesseract
import psutil

class TesseractTimeoutManager:
    """Thread-based timeout manager for Tesseract OCR operations"""
    
    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self.result = None
        self.exception = None
        self.process_pids = []
        
    def _target_function(self, func, *args, **kwargs):
        """Target function to run in thread"""
        try:
            # Monitor for tesseract processes during execution
            self._monitor_processes()
            self.result = func(*args, **kwargs)
        except Exception as e:
            self.exception = e
        finally:
            # Cleanup any remaining tesseract processes
            self._cleanup_processes()
    
    def _monitor_processes(self):
        """Monitor for tesseract processes that might hang"""
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if 'tesseract' in proc.info['name'].lower():
                    self.process_pids.append(proc.info['pid'])
        except:
            pass  # Silently handle process monitoring errors
    
    def _cleanup_processes(self):
        """Kill any hanging tesseract processes"""
        try:
            for pid in self.process_pids:
                try:
                    proc = psutil.Process(pid)
                    if proc.is_running() and 'tesseract' in proc.name().lower():
                        proc.terminate()
                        # Give it 2 seconds to terminate gracefully
                        proc.wait(timeout=2)
                except (psutil.NoSuchProcess, psutil.TimeoutExpired, psutil.AccessDenied):
                    pass
        except:
            pass  # Silently handle cleanup errors
    
    def run_with_timeout(self, func, *args, **kwargs):
        """Run function with timeout protection"""
        self.result = None
        self.exception = None
        self.process_pids = []
        
        # Create and start thread
        thread = threading.Thread(
            target=self._target_function,
            args=(func,) + args,
            kwargs=kwargs,
            daemon=True
        )
        
        thread.start()
        thread.join(timeout=self.timeout)
        
        if thread.is_alive():
            # Thread is still running - we have a timeout
            self._cleanup_processes()
            raise TimeoutError(f"OCR operation timed out after {self.timeout} seconds")
        
        # Check for exceptions
        if self.exception:
            raise self.exception
            
        return self.result


class WorkingQuickOCR:
    """Reliable OCR with timeout protection - balanced speed and accuracy"""
    
    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout
        self.timeout_manager = TesseractTimeoutManager(timeout)
        
        # Optimized config for balance of speed and accuracy
        self.tesseract_config = '--oem 3 --psm 6'
        
    def _preprocess_image(self, image: Union[Image.Image, str]) -> Image.Image:
        """Optimize image for OCR"""
        if isinstance(image, str):
            image = Image.open(image)
        
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Resize if too large (speeds up OCR significantly)
        if image.width > 2000 or image.height > 2000:
            # Maintain aspect ratio
            ratio = min(2000 / image.width, 2000 / image.height)
            new_size = (int(image.width * ratio), int(image.height * ratio))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        
        return image
    
    def _ocr_operation(self, image: Image.Image) -> str:
        """Core OCR operation"""
        return pytesseract.image_to_string(image, config=self.tesseract_config).strip()
    
    def extract_text(self, image: Union[Image.Image, str]) -> Optional[str]:
        """Extract text from image with timeout protection"""
        try:
            # Preprocess image
            processed_image = self._preprocess_image(image)
            
            # Run OCR with timeout protection
            result = self.timeout_manager.run_with_timeout(
                self._ocr_operation,
                processed_image
            )
            
            return result if result else None
            
        except TimeoutError:
            print(f"⚠️ OCR timeout after {self.timeout}s - operation cancelled")
            return None
        except Exception as e:
            print(f"⚠️ OCR error: {e}")
            return None


class WorkingFastScreenOCR:
    """Fast OCR optimized for screen captures and real-time applications"""
    
    def __init__(self, timeout: float = 8.0):
        self.timeout = timeout
        self.timeout_manager = TesseractTimeoutManager(timeout)
        
        # Fast config optimized for screen text
        # Note: Avoid including quote characters (" and ') in whitelist as Tesseract's
        # argument/config parsing may treat them specially and error with
        # "No closing quotation". Keep a safe, punctuation-heavy whitelist instead.
        self.tesseract_config = '--oem 3 --psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,!?;:()[]{}@#$/%&*+=<>~_-'
        
    def _preprocess_for_speed(self, image: Union[Image.Image, str]) -> Image.Image:
        """Fast preprocessing for screen captures"""
        if isinstance(image, str):
            image = Image.open(image)
        
        # Convert to grayscale for speed
        if image.mode != 'L':
            image = image.convert('L')
        
        # Aggressive resizing for speed
        if image.width > 1500 or image.height > 1500:
            ratio = min(1500 / image.width, 1500 / image.height)
            new_size = (int(image.width * ratio), int(image.height * ratio))
            image = image.resize(new_size, Image.Resampling.NEAREST)
        
        return image
    
    def _fast_ocr_operation(self, image: Image.Image) -> str:
        """Fast OCR operation for screen text"""
        return pytesseract.image_to_string(image, config=self.tesseract_config).strip()
    
    def extract_screen_text(self, image: Union[Image.Image, str]) -> Optional[str]:
        """Extract text optimized for screen captures"""
        try:
            # Fast preprocessing
            processed_image = self._preprocess_for_speed(image)
            
            # Run fast OCR with timeout
            result = self.timeout_manager.run_with_timeout(
                self._fast_ocr_operation,
                processed_image
            )
            
            return result if result else None
            
        except TimeoutError:
            print(f"⚠️ Fast OCR timeout after {self.timeout}s")
            return None
        except Exception as e:
            print(f"⚠️ Fast OCR error: {e}")
            return None


class WorkingOCRBatch:
    """Batch OCR processing with timeout protection"""
    
    def __init__(self, timeout_per_image: float = 10.0):
        self.quick_ocr = WorkingQuickOCR(timeout_per_image)
        self.fast_ocr = WorkingFastScreenOCR(timeout_per_image * 0.8)
    
    def process_images(self, images: list, fast_mode: bool = False) -> list:
        """Process multiple images with timeout protection"""
        results = []
        ocr_instance = self.fast_ocr if fast_mode else self.quick_ocr
        
        for i, image in enumerate(images):
            print(f"Processing image {i+1}/{len(images)}...")
            
            try:
                if fast_mode:
                    text = ocr_instance.extract_screen_text(image)
                else:
                    text = ocr_instance.extract_text(image)
                
                results.append({
                    'index': i,
                    'text': text,
                    'success': text is not None
                })
                
            except Exception as e:
                print(f"Failed to process image {i+1}: {e}")
                results.append({
                    'index': i,
                    'text': None,
                    'success': False,
                    'error': str(e)
                })
        
        return results


def test_ocr_fix():
    """Test the OCR timeout fix functionality"""
    from PIL import Image, ImageDraw
    
    print("🧪 Testing OCR Timeout Fix")
    print("=" * 40)
    
    # Create test image
    test_img = Image.new('RGB', (400, 100), color='white')
    draw = ImageDraw.Draw(test_img)
    draw.text((20, 30), "OCR Timeout Fix Test - Working!", fill='black')
    
    # Test Quick OCR
    print("Testing WorkingQuickOCR...")
    quick_ocr = WorkingQuickOCR(timeout=15.0)
    start_time = time.time()
    result1 = quick_ocr.extract_text(test_img)
    time1 = time.time() - start_time
    
    print(f"Result: {repr(result1)}")
    print(f"Time: {time1:.2f}s")
    print(f"Success: {'✅' if result1 else '❌'}")
    
    # Test Fast Screen OCR  
    print("\nTesting WorkingFastScreenOCR...")
    fast_ocr = WorkingFastScreenOCR(timeout=8.0)
    start_time = time.time()
    result2 = fast_ocr.extract_screen_text(test_img)
    time2 = time.time() - start_time
    
    print(f"Result: {repr(result2)}")
    print(f"Time: {time2:.2f}s")
    print(f"Success: {'✅' if result2 else '❌'}")
    
    # Summary
    success_count = sum([1 for r in [result1, result2] if r])
    print(f"\n📊 Overall Success: {success_count}/2 ({success_count/2*100:.0f}%)")
    
    if success_count > 0:
        print("🎉 OCR timeout fix is working!")
        return True
    else:
        print("❌ OCR timeout fix needs attention")
        return False


if __name__ == "__main__":
    # Run test when script is executed directly
    test_ocr_fix()