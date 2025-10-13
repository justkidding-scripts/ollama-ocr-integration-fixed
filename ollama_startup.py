#!/usr/bin/env python3
"""
Ollama Enhanced OCR System Startup Script
Quick launcher for the integrated Ollama OCR analysis system
"""

import sys
import subprocess
from pathlib import Path

def main():
    """Main startup function"""
    print("🚀 Starting Ollama Enhanced OCR System...")
    
    # Check if Ollama is running
    try:
        import requests
        response = requests.get("http://localhost:11434/api/version", timeout=3)
        if response.status_code != 200:
            raise Exception("Ollama not responding")
        print("✅ Ollama service is running")
    except Exception:
        print("❌ Ollama service not running")
        print("Please start Ollama with: ollama serve")
        return 1
    
    # Set up path
    script_dir = Path(__file__).parent
    sys.path.insert(0, str(script_dir))
    
    # Launch the enhanced system
    try:
        # Option 1: Launch enhanced OCR assistant directly
        if len(sys.argv) > 1 and sys.argv[1] == "ocr":
            from ocr_llm_assistant_enhanced import EnhancedOCRAssistant
            assistant = EnhancedOCRAssistant()
            assistant.run()
            
        # Option 2: Launch Ollama interface directly
        elif len(sys.argv) > 1 and sys.argv[1] == "interface":
            from ollama_interaction import OllamaInteractionInterface
            interface = OllamaInteractionInterface()
            interface.run()
            
        # Option 3: Launch full enhancement systems launcher
        else:
            launcher_path = Path("/home/nike/personal-enhancement-systems/Desktop/Enhancement_Systems_Launcher.py")
            if launcher_path.exists():
                subprocess.run([sys.executable, str(launcher_path)])
            else:
                print("❌ Enhancement systems launcher not found")
                print("Available options:")
                print("  python ollama_startup.py ocr        - Launch enhanced OCR assistant")
                print("  python ollama_startup.py interface  - Launch Ollama interface")
                return 1
                
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please ensure all Ollama components are properly installed")
        return 1
    except Exception as e:
        print(f"❌ Error starting system: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
