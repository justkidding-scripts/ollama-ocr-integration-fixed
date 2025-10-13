#!/usr/bin/env python3
"""
Integration Script for Ollama Intelligent Prompting System
Updates the existing enhancement system launcher to include Ollama components
"""

import json
import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Optional


def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = [
        'requests',
        'tkinter',  # Usually built-in with Python
        'pathlib',
        'dataclasses',
        'threading',
        'logging'
    ]
    
    missing = []
    for package in required_packages:
        try:
            if package == 'tkinter':
                import tkinter
            else:
                __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ Missing required packages: {', '.join(missing)}")
        print("Please install them with: pip install " + " ".join(missing))
        return False
    
    print("✅ All dependencies are available")
    return True


def check_ollama_installation():
    """Check if Ollama is installed and running"""
    try:
        # Check if ollama command is available
        result = subprocess.run(['which', 'ollama'], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Ollama is not installed")
            print("Please install Ollama from https://ollama.ai/download")
            return False
        
        print("✅ Ollama is installed")
        
        # Check if Ollama service is running
        try:
            import requests
            response = requests.get("http://localhost:11434/api/version", timeout=5)
            if response.status_code == 200:
                print("✅ Ollama service is running")
                return True
            else:
                print("⚠️  Ollama service is not responding")
                return False
        except requests.exceptions.RequestException:
            print("⚠️  Ollama service is not running")
            print("Start it with: ollama serve")
            return False
            
    except Exception as e:
        print(f"❌ Error checking Ollama: {e}")
        return False


def check_ollama_models():
    """Check if required Ollama models are available"""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=10)
        
        if response.status_code == 200:
            models = response.json()
            model_names = [model['name'] for model in models.get('models', [])]
            
            recommended_models = ['llama3.2:latest', 'llama3.1:latest', 'mistral:latest']
            available_recommended = [model for model in recommended_models if model in model_names]
            
            if available_recommended:
                print(f"✅ Available models: {', '.join(available_recommended)}")
                return True, available_recommended[0]
            elif model_names:
                print(f"⚠️  Available models: {', '.join(model_names)}")
                print("Consider installing a recommended model:")
                for model in recommended_models:
                    print(f"  ollama pull {model}")
                return True, model_names[0]
            else:
                print("❌ No models installed")
                print("Install a model with: ollama pull llama3.2:latest")
                return False, None
        else:
            print("❌ Cannot check models - Ollama API not responding")
            return False, None
            
    except Exception as e:
        print(f"❌ Error checking models: {e}")
        return False, None


def update_launcher_integration(base_dir: Path):
    """Update the enhancement system launcher to include Ollama components"""
    
    launcher_script = Path("/home/nike/personal-enhancement-systems/Desktop/Enhancement_Systems_Launcher.py")
    
    if not launcher_script.exists():
        print(f"❌ Launcher script not found at {launcher_script}")
        return False
    
    # Read the current launcher
    try:
        with open(launcher_script, 'r') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Error reading launcher: {e}")
        return False
    
    # Check if Ollama integration is already added
    if "ollama_prompt_system" in content:
        print("✅ Ollama integration already present in launcher")
        return True
    
    # Add Ollama imports at the top
    ollama_imports = """
# Ollama Integration Imports
try:
    from Screenshare.ollama_prompt_system import OllamaPromptSystem
    from Screenshare.ollama_interaction import OllamaInteractionInterface
    from Screenshare.ocr_llm_assistant_enhanced import EnhancedOCRAssistant
    OLLAMA_AVAILABLE = True
except ImportError as e:
    print(f"Ollama components not available: {e}")
    OLLAMA_AVAILABLE = False
"""
    
    # Add Ollama integration to the launcher class
    ollama_methods = '''
    def launch_ollama_interface(self):
        """Launch the Ollama interaction interface"""
        if not OLLAMA_AVAILABLE:
            self.log_message("❌ Ollama components not available")
            return
            
        try:
            from Screenshare.ollama_interaction import OllamaInteractionInterface
            
            def start_ollama():
                interface = OllamaInteractionInterface()
                interface.run()
                
            self.launch_in_background("Ollama Interface", start_ollama)
            self.log_message("✅ Ollama interface launched")
            
        except Exception as e:
            self.log_message(f"❌ Failed to launch Ollama interface: {e}")
    
    def launch_enhanced_ocr(self):
        """Launch the enhanced OCR assistant with Ollama integration"""
        if not OLLAMA_AVAILABLE:
            self.log_message("❌ Enhanced OCR not available")
            return
            
        try:
            from Screenshare.ocr_llm_assistant_enhanced import EnhancedOCRAssistant
            
            def start_enhanced_ocr():
                assistant = EnhancedOCRAssistant()
                assistant.run()
                
            self.launch_in_background("Enhanced OCR Assistant", start_enhanced_ocr)
            self.log_message("✅ Enhanced OCR assistant launched")
            
        except Exception as e:
            self.log_message(f"❌ Failed to launch enhanced OCR: {e}")
    
    def test_ollama_connection(self):
        """Test connection to Ollama service"""
        if not OLLAMA_AVAILABLE:
            self.log_message("❌ Ollama not available for testing")
            return
            
        try:
            from Screenshare.ollama_prompt_system import OllamaPromptSystem
            prompt_system = OllamaPromptSystem()
            
            response = prompt_system.query_ollama("Test connection - respond with 'Hello'")
            if response:
                self.log_message("✅ Ollama connection successful")
            else:
                self.log_message("❌ Ollama connection failed")
                
        except Exception as e:
            self.log_message(f"❌ Ollama connection error: {e}")
'''
    
    # Add Ollama buttons to the GUI setup
    ollama_gui_additions = '''
        # Ollama Integration Section
        if OLLAMA_AVAILABLE:
            ollama_frame = ttk.LabelFrame(tab, text="Ollama AI Integration", padding=5)
            ollama_frame.pack(fill=tk.X, pady=5)
            
            ttk.Button(ollama_frame, text="🧠 Launch Ollama Interface", 
                      command=self.launch_ollama_interface).pack(side=tk.LEFT, padx=2)
            ttk.Button(ollama_frame, text="🔍 Enhanced OCR Assistant", 
                      command=self.launch_enhanced_ocr).pack(side=tk.LEFT, padx=2)
            ttk.Button(ollama_frame, text="🔗 Test Ollama Connection", 
                      command=self.test_ollama_connection).pack(side=tk.LEFT, padx=2)
        else:
            unavailable_frame = ttk.LabelFrame(tab, text="Ollama Integration (Unavailable)", padding=5)
            unavailable_frame.pack(fill=tk.X, pady=5)
            ttk.Label(unavailable_frame, text="Install Ollama components to enable AI features", 
                     foreground="gray").pack()
'''
    
    # Try to intelligently insert the code
    try:
        # Insert imports after existing imports
        import_insertion_point = content.find("import tkinter as tk")
        if import_insertion_point == -1:
            import_insertion_point = content.find("from tkinter")
        
        if import_insertion_point != -1:
            # Find end of imports section
            lines = content.split('\n')
            insert_line = 0
            for i, line in enumerate(lines):
                if line.strip().startswith(('import ', 'from ')) or line.strip().startswith('#'):
                    insert_line = i + 1
                elif line.strip() == '':
                    continue
                else:
                    break
            
            lines.insert(insert_line, ollama_imports)
            content = '\n'.join(lines)
        
        # Insert methods into the launcher class
        class_insertion_point = content.find("class EnhancementSystemsLauncher:")
        if class_insertion_point != -1:
            # Find a good place to insert methods (before the run method)
            run_method_point = content.find("def run(self):", class_insertion_point)
            if run_method_point != -1:
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if "def run(self):" in line:
                        lines.insert(i, ollama_methods)
                        break
                content = '\n'.join(lines)
        
        # Insert GUI components
        gui_setup_point = content.find("def setup_gui(self):")
        if gui_setup_point != -1:
            # Look for the end of the tab setup
            tab_setup_end = content.find("notebook.pack(", gui_setup_point)
            if tab_setup_end != -1:
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if "notebook.pack(" in line:
                        lines.insert(i, ollama_gui_additions)
                        break
                content = '\n'.join(lines)
        
        # Write the updated launcher
        backup_file = launcher_script.with_suffix('.py.backup')
        
        # Create backup
        with open(backup_file, 'w') as f:
            with open(launcher_script, 'r') as orig:
                f.write(orig.read())
        
        # Write updated version
        with open(launcher_script, 'w') as f:
            f.write(content)
        
        print(f"✅ Launcher updated successfully")
        print(f"📁 Backup created: {backup_file}")
        return True
        
    except Exception as e:
        print(f"❌ Error updating launcher: {e}")
        return False


def create_integration_config(base_dir: Path):
    """Create configuration file for Ollama integration"""
    
    config = {
        "ollama": {
            "base_url": "http://localhost:11434",
            "model": "llama3.2:latest",
            "timeout": 30,
            "temperature": 0.3,
            "max_tokens": 500
        },
        "integration": {
            "auto_start_with_launcher": True,
            "enable_ocr_integration": True,
            "background_analysis": True,
            "cache_responses": True
        },
        "ui": {
            "show_notifications": True,
            "auto_hide_interface": False,
            "theme": "default"
        }
    }
    
    config_file = base_dir / "ollama_integration_config.json"
    
    try:
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"✅ Configuration created: {config_file}")
        return True
    except Exception as e:
        print(f"❌ Error creating config: {e}")
        return False


def create_startup_script(base_dir: Path):
    """Create a startup script for easy Ollama system launch"""
    
    startup_script_content = '''#!/usr/bin/env python3
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
'''
    
    startup_script = base_dir / "ollama_startup.py"
    
    try:
        with open(startup_script, 'w') as f:
            f.write(startup_script_content)
        
        # Make executable
        os.chmod(startup_script, 0o755)
        
        print(f"✅ Startup script created: {startup_script}")
        print("Usage:")
        print(f"  python {startup_script} ocr        - Enhanced OCR Assistant")
        print(f"  python {startup_script} interface  - Ollama Interface")  
        print(f"  python {startup_script}            - Full Enhancement Launcher")
        
        return True
    except Exception as e:
        print(f"❌ Error creating startup script: {e}")
        return False


def create_test_script(base_dir: Path):
    """Create a test script to verify the integration"""
    
    test_script_content = '''#!/usr/bin/env python3
"""
Ollama Integration Test Script
Test all components of the Ollama intelligent prompting system
"""

import sys
import time
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test if all components can be imported"""
    print("🧪 Testing imports...")
    
    try:
        from ollama_prompt_system import OllamaPromptSystem, AnalysisResponse, PromptContext
        print("  ✅ ollama_prompt_system")
    except ImportError as e:
        print(f"  ❌ ollama_prompt_system: {e}")
        return False
    
    try:
        from ollama_interaction import OllamaInteractionInterface
        print("  ✅ ollama_interaction")
    except ImportError as e:
        print(f"  ❌ ollama_interaction: {e}")
        return False
    
    try:
        from ocr_llm_assistant_enhanced import EnhancedOCRAssistant
        print("  ✅ ocr_llm_assistant_enhanced")
    except ImportError as e:
        print(f"  ❌ ocr_llm_assistant_enhanced: {e}")
        return False
    
    print("✅ All imports successful")
    return True

def test_ollama_connection():
    """Test connection to Ollama"""
    print("🧪 Testing Ollama connection...")
    
    try:
        from ollama_prompt_system import OllamaPromptSystem
        
        system = OllamaPromptSystem()
        response = system.query_ollama("Hello, please respond with 'Test successful'")
        
        if response and response.get('response'):
            print(f"  ✅ Ollama responded: {response['response'][:50]}...")
            return True
        else:
            print("  ❌ Ollama did not respond properly")
            return False
            
    except Exception as e:
        print(f"  ❌ Ollama connection failed: {e}")
        return False

def test_prompt_system():
    """Test the prompt system functionality"""
    print("🧪 Testing prompt system...")
    
    try:
        from ollama_prompt_system import OllamaPromptSystem
        
        system = OllamaPromptSystem()
        
        # Test analysis
        test_text = "def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)"
        test_history = ["Working on algorithms", "Implementing recursive functions"]
        test_stats = {"session_duration": 10.0, "total_queries": 1}
        
        result = system.analyze_content(test_text, test_history, test_stats)
        
        if result and result.main_insight:
            print(f"  ✅ Analysis completed: {result.analysis_type}")
            print(f"     Activity detected: {result.context_tags[0] if result.context_tags else 'None'}")
            print(f"     Confidence: {result.confidence:.1%}")
            return True
        else:
            print("  ❌ Analysis failed")
            return False
            
    except Exception as e:
        print(f"  ❌ Prompt system test failed: {e}")
        return False

def test_gui_components():
    """Test GUI components (without actually launching)"""
    print("🧪 Testing GUI components...")
    
    try:
        # Test imports and basic instantiation
        from ollama_interaction import OllamaInteractionInterface
        from ocr_llm_assistant_enhanced import EnhancedOCRAssistant
        
        # Test basic instantiation (without running GUI)
        interface = OllamaInteractionInterface()
        assistant = EnhancedOCRAssistant()
        
        print("  ✅ GUI components instantiated successfully")
        return True
        
    except Exception as e:
        print(f"  ❌ GUI component test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Ollama Integration Test Suite")
    print("=" * 50)
    
    tests = [
        ("Component Imports", test_imports),
        ("Ollama Connection", test_ollama_connection),
        ("Prompt System", test_prompt_system),
        ("GUI Components", test_gui_components),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\\n{test_name}:")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"  ❌ Test crashed: {e}")
            results.append((test_name, False))
    
    print("\\n" + "=" * 50)
    print("📊 Test Results:")
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {test_name}: {status}")
        if success:
            passed += 1
    
    print(f"\\n📈 Tests passed: {passed}/{len(tests)}")
    
    if passed == len(tests):
        print("🎉 All tests passed! Ollama integration is ready.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the error messages above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
'''
    
    test_script = base_dir / "test_ollama_integration.py"
    
    try:
        with open(test_script, 'w') as f:
            f.write(test_script_content)
        
        os.chmod(test_script, 0o755)
        
        print(f"✅ Test script created: {test_script}")
        print(f"Run tests with: python {test_script}")
        
        return True
    except Exception as e:
        print(f"❌ Error creating test script: {e}")
        return False


def main():
    """Main integration function"""
    print("🚀 Ollama Intelligent Prompting System Integration")
    print("=" * 60)
    
    # Get base directory
    base_dir = Path(__file__).parent
    print(f"📁 Base directory: {base_dir}")
    
    # Check dependencies
    print("\n1. Checking Dependencies...")
    if not check_dependencies():
        return 1
    
    # Check Ollama installation
    print("\n2. Checking Ollama Installation...")
    if not check_ollama_installation():
        print("⚠️  Ollama is not properly set up")
        print("The system will still be integrated, but AI features won't work until Ollama is configured")
    
    # Check Ollama models
    print("\n3. Checking Ollama Models...")
    models_available, default_model = check_ollama_models()
    if not models_available:
        print("⚠️  No Ollama models found")
        print("Install a model with: ollama pull llama3.2:latest")
    
    # Update launcher integration
    print("\n4. Updating Enhancement Systems Launcher...")
    if not update_launcher_integration(base_dir):
        print("❌ Failed to update launcher")
        return 1
    
    # Create integration config
    print("\n5. Creating Integration Configuration...")
    if not create_integration_config(base_dir):
        print("❌ Failed to create configuration")
        return 1
    
    # Create startup script
    print("\n6. Creating Startup Script...")
    if not create_startup_script(base_dir):
        print("❌ Failed to create startup script")
        return 1
    
    # Create test script
    print("\n7. Creating Test Script...")
    if not create_test_script(base_dir):
        print("❌ Failed to create test script")
        return 1
    
    print("\n" + "=" * 60)
    print("🎉 Ollama Integration Complete!")
    print("\nNext Steps:")
    print("1. Ensure Ollama is running: ollama serve")
    print("2. Pull a model if needed: ollama pull llama3.2:latest")
    print("3. Test the integration: python test_ollama_integration.py")
    print("4. Launch the system: python ollama_startup.py")
    
    print("\n🔧 Enhancement Recommendations:")
    print("1. **Context-Aware Prompts**: Automatically adjust prompts based on detected activity")
    print("2. **Guided Questions**: Interactive questions to improve analysis")
    print("3. **Premade Responses**: Fast responses for common scenarios")
    print("4. **Follow-up Prompts**: Suggestions for deeper analysis")
    print("5. **Activity Detection**: Classify coding, research, presentations, etc.")
    print("6. **Response Caching**: Speed up repeated analyses")
    print("7. **Session Analytics**: Track productivity and analysis patterns")
    print("8. **Export/Import**: Save analysis sessions and share insights")
    print("9. **Custom Templates**: Create specialized prompts for specific tasks")
    print("10. **Real-time Feedback**: Continuous AI assistance during work sessions")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())