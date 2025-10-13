#!/usr/bin/env python3
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
        print(f"\n{test_name}:")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"  ❌ Test crashed: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {test_name}: {status}")
        if success:
            passed += 1
    
    print(f"\n📈 Tests passed: {passed}/{len(tests)}")
    
    if passed == len(tests):
        print("🎉 All tests passed! Ollama integration is ready.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the error messages above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
