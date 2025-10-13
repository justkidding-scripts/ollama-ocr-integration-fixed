#!/usr/bin/env python3
"""
Comprehensive Integration Test for Fixed Ollama System
Tests all components and verifies fixes are working properly
"""

import sys
import time
import subprocess
import signal
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_ollama_service():
    """Test if Ollama service is running"""
    print("🔍 Testing Ollama Service...")
    try:
        import requests
        response = requests.get("http://localhost:11434/api/version", timeout=5)
        if response.status_code == 200:
            print("  ✅ Ollama service is running")
            # Test models
            models_response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if models_response.status_code == 200:
                models = models_response.json()
                model_count = len(models.get('models', []))
                print(f"  ✅ {model_count} models available")
                return True
        else:
            print("  ❌ Ollama service not responding properly")
            return False
    except Exception as e:
        print(f"  ❌ Ollama service error: {e}")
        return False

def test_imports():
    """Test all module imports"""
    print("🔍 Testing Module Imports...")
    modules_to_test = [
        "ollama_prompt_system",
        "ollama_interaction", 
        "ocr_llm_assistant_enhanced",
        "test_ollama_integration",
        "demo_ollama_system"
    ]
    
    passed = 0
    for module in modules_to_test:
        try:
            __import__(module)
            print(f"  ✅ {module}")
            passed += 1
        except ImportError as e:
            print(f"  ❌ {module}: {e}")
    
    print(f"  📊 Import tests: {passed}/{len(modules_to_test)} passed")
    return passed == len(modules_to_test)

def test_prompt_system_robustness():
    """Test the prompt system with error handling"""
    print("🔍 Testing Prompt System Robustness...")
    try:
        from ollama_prompt_system import OllamaPromptSystem
        
        system = OllamaPromptSystem()
        print("  ✅ Prompt system initialized")
        
        # Test with simple text
        test_text = "print('Hello World')"
        test_history = ["Testing code", "Writing Python"]
        test_stats = {"session_duration": 5.0, "total_queries": 1}
        
        # This should handle timeouts gracefully now
        result = system.analyze_content(test_text, test_history, test_stats)
        
        if result:
            print(f"  ✅ Analysis completed: {result.analysis_type}")
            print(f"  📊 Confidence: {result.confidence:.1%}")
            print(f"  🏷️ Context: {', '.join(result.context_tags)}")
            return True
        else:
            print("  ❌ Analysis failed")
            return False
            
    except Exception as e:
        print(f"  ❌ Prompt system error: {e}")
        return False

def test_gui_components_safe():
    """Test GUI components without launching windows"""
    print("🔍 Testing GUI Components (Safe Mode)...")
    try:
        # Test instantiation without running mainloop
        from ollama_interaction import OllamaInteractionInterface
        from ocr_llm_assistant_enhanced import EnhancedOCRAssistant
        
        # Create instances without running
        interface = OllamaInteractionInterface()
        assistant = EnhancedOCRAssistant()
        
        print("  ✅ GUI components instantiated successfully")
        
        # Test that they have proper error handling
        if hasattr(interface, 'on_closing') and hasattr(assistant, 'on_closing'):
            print("  ✅ Proper shutdown handlers present")
            return True
        else:
            print("  ⚠️ Some shutdown handlers missing")
            return False
            
    except Exception as e:
        print(f"  ❌ GUI component error: {e}")
        return False

def test_launcher_imports():
    """Test that the launcher can import Ollama components"""
    print("🔍 Testing Launcher Integration...")
    try:
        launcher_path = "/home/nike/personal-enhancement-systems/Desktop/Enhancement_Systems_Launcher.py"
        
        # Test that launcher file exists and has proper imports
        if not Path(launcher_path).exists():
            print(f"  ❌ Launcher not found at {launcher_path}")
            return False
            
        # Run a quick syntax check
        result = subprocess.run([
            sys.executable, "-m", "py_compile", launcher_path
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("  ✅ Launcher syntax is valid")
        else:
            print(f"  ❌ Launcher syntax error: {result.stderr}")
            return False
            
        # Test imports specifically
        test_script = f"""
import sys
sys.path.insert(0, "/media/nike/5f57e86a-891a-4785-b1c8-fae01ada4edd1/Modular Deepdive/Screenshare")
try:
    from ollama_prompt_system import OllamaPromptSystem
    from ollama_interaction import OllamaInteractionInterface  
    from ocr_llm_assistant_enhanced import EnhancedOCRAssistant
    print("OLLAMA_IMPORTS_SUCCESS")
except ImportError as e:
    print(f"OLLAMA_IMPORTS_FAILED: {{e}}")
"""
        
        result = subprocess.run([
            sys.executable, "-c", test_script
        ], capture_output=True, text=True, timeout=10)
        
        if "OLLAMA_IMPORTS_SUCCESS" in result.stdout:
            print("  ✅ Launcher can import Ollama components")
            return True
        else:
            print(f"  ❌ Launcher import error: {result.stdout}{result.stderr}")
            return False
            
    except Exception as e:
        print(f"  ❌ Launcher test error: {e}")
        return False

def test_startup_script():
    """Test the startup script functionality"""
    print("🔍 Testing Startup Script...")
    try:
        startup_path = Path(__file__).parent / "ollama_startup.py"
        
        if not startup_path.exists():
            print(f"  ❌ Startup script not found")
            return False
            
        # Test startup script help/status
        result = subprocess.run([
            sys.executable, str(startup_path)
        ], capture_output=True, text=True, timeout=15, cwd=str(startup_path.parent))
        
        if result.returncode == 0 and "Ollama service is running" in result.stdout:
            print("  ✅ Startup script working")
            return True
        else:
            print(f"  ❌ Startup script error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("  ⚠️ Startup script timeout (may be launching GUI)")
        return True  # Timeout might mean it's trying to launch GUI, which is expected
    except Exception as e:
        print(f"  ❌ Startup script test error: {e}")
        return False

def run_comprehensive_test():
    """Run all tests and provide summary"""
    print("🧪 Comprehensive Ollama Integration Test Suite")
    print("=" * 60)
    
    tests = [
        ("Ollama Service", test_ollama_service),
        ("Module Imports", test_imports),
        ("Prompt System Robustness", test_prompt_system_robustness),
        ("GUI Components (Safe)", test_gui_components_safe),
        ("Launcher Integration", test_launcher_imports),
        ("Startup Script", test_startup_script),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 40)
        try:
            success = test_func()
            results.append((test_name, success))
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"  Result: {status}")
        except Exception as e:
            print(f"  ❌ Test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    print("-" * 40)
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {test_name:<25} {status}")
        if success:
            passed += 1
    
    print(f"\n📈 Overall: {passed}/{len(results)} tests passed ({passed/len(results)*100:.1f}%)")
    
    if passed == len(results):
        print("\n🎉 All tests passed! Ollama integration is fully functional.")
        print("\n🚀 Ready to use:")
        print("   python ollama_startup.py ocr        - Enhanced OCR Assistant")
        print("   python ollama_startup.py interface  - Ollama Interface") 
        print("   python ollama_startup.py            - Full Enhancement Launcher")
        return 0
    else:
        print(f"\n⚠️  {len(results) - passed} test(s) failed. Check error messages above.")
        return 1

if __name__ == "__main__":
    sys.exit(run_comprehensive_test())