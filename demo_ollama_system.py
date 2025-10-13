#!/usr/bin/env python3
"""
Demo Script for Ollama Enhanced OCR System
Demonstrates the key features of the intelligent prompting system
"""

import sys
import time
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def demo_prompt_system():
    """Demonstrate the prompt system with different activity types"""
    print("🎪 Ollama Enhanced OCR System Demo")
    print("=" * 50)
    
    try:
        from ollama_prompt_system import OllamaPromptSystem
        
        system = OllamaPromptSystem()
        print("✅ Ollama prompt system initialized")
        
        # Demo different activity types
        demo_scenarios = [
            {
                "name": "Coding Activity",
                "text": "def calculate_fibonacci(n):\n    if n <= 1:\n        return n\n    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)",
                "history": ["Working on algorithms", "Implementing recursive functions", "Testing fibonacci implementation"],
                "expected_activity": "coding"
            },
            {
                "name": "Research Activity", 
                "text": "This study examines the effectiveness of machine learning algorithms in predicting market volatility. Our methodology involves collecting historical data from multiple exchanges and applying various regression models to identify patterns.",
                "history": ["Literature review", "Data collection phase", "Statistical analysis"],
                "expected_activity": "research"
            },
            {
                "name": "Presentation Activity",
                "text": "Welcome to our quarterly review presentation. Today we'll cover our achievements, challenges, and roadmap for the next quarter. Let's start with our key performance indicators.",
                "history": ["Preparing slides", "Rehearsing presentation", "Setting up demo"],
                "expected_activity": "presentation"
            },
            {
                "name": "Terminal/Command Activity",
                "text": "sudo apt update && sudo apt install python3-pip\nnpm install -g typescript\ngit clone https://github.com/user/repo.git",
                "history": ["Setting up development environment", "Installing dependencies", "Cloning repositories"],
                "expected_activity": "terminal"
            }
        ]
        
        for i, scenario in enumerate(demo_scenarios, 1):
            print(f"\n🎯 Demo {i}: {scenario['name']}")
            print("-" * 30)
            
            # Show input
            preview = scenario['text'][:100] + "..." if len(scenario['text']) > 100 else scenario['text']
            print(f"📝 Input Text: {preview}")
            print(f"📚 History: {' -> '.join(scenario['history'][-2:])}")
            
            # Analyze with prompt system
            session_stats = {
                'session_duration': 10.0 + i * 2,
                'total_queries': i,
                'frames_per_minute': 2.5
            }
            
            try:
                result = system.analyze_content(scenario['text'], scenario['history'], session_stats)
            except Exception as e:
                print(f"Error analyzing content: {e}")
                # Create a fallback result
                from ollama_prompt_system import AnalysisResponse
                result = AnalysisResponse(
                    analysis_type="fallback",
                    confidence=0.5,
                    main_insight="Good use of design patterns. Unit tests could strengthen this further.",
                    suggestions=[],
                    questions=["What edge cases should this code handle?", "How would you test this function?"],
                    follow_up_prompts=[],
                    context_tags=[scenario['expected_activity']],
                    timestamp=time.time()
                )
            
            # Display results
            print(f"🔍 Detected Activity: {result.context_tags[0] if result.context_tags else 'Unknown'}")
            print(f"📊 Confidence: {result.confidence:.1%}")
            print(f"🧠 Analysis Type: {result.analysis_type}")
            
            if result.analysis_type == "ai_generated":
                print(f"💡 AI Insight: {result.main_insight[:150]}...")
            elif result.analysis_type == "premade":
                print(f"⚡ Quick Response: {result.main_insight}")
            else:
                print(f"🔄 Fallback: {result.main_insight}")
            
            if result.suggestions:
                print(f"💭 Suggestions ({len(result.suggestions)}):")
                for j, suggestion in enumerate(result.suggestions[:2], 1):
                    print(f"   {j}. {suggestion}")
            
            if result.questions:
                print(f"❓ Guided Questions ({len(result.questions)}):")
                for j, question in enumerate(result.questions[:2], 1):
                    print(f"   {j}. {question}")
            
            # Small delay for demo effect
            time.sleep(1)
        
        # Show session summary
        print(f"\n📈 Demo Session Summary:")
        summary = system.get_analysis_summary()
        print(f"   Total Analyses: {summary.get('total_analyses', 0)}")
        print(f"   Average Confidence: {summary.get('average_confidence', 0):.1%}")
        
        top_activities = summary.get('top_activities', [])
        if top_activities:
            print(f"   Top Activities: {', '.join([f'{act[0]}({act[1]})' for act in top_activities[:3]])}")
        
        print("\n🎉 Demo completed successfully!")
        print("\n🚀 Ready to launch the full system:")
        print("   python ollama_startup.py ocr        - Enhanced OCR Assistant")
        print("   python ollama_startup.py interface  - Ollama Interface")
        print("   python ollama_startup.py            - Full Enhancement Launcher")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        return 1
    
    return 0


def show_feature_overview():
    """Show overview of system features"""
    print("\n🔧 Ollama Enhanced OCR System Features:")
    print("=" * 50)
    
    features = [
        {
            "name": "🧠 Context-Aware Analysis",
            "description": "Automatically detects activity type (coding, research, presentations) and adapts prompts accordingly"
        },
        {
            "name": "💡 Intelligent Prompting",
            "description": "Uses different prompt templates based on detected context for more relevant AI responses"
        },
        {
            "name": "⚡ Premade Responses",
            "description": "Quick responses for common scenarios when AI is unavailable or confidence is low"
        },
        {
            "name": "❓ Guided Questions",
            "description": "Context-aware questions to help users think deeper about their work"
        },
        {
            "name": "🔄 Follow-up Prompts", 
            "description": "Suggests next steps and deeper analysis opportunities"
        },
        {
            "name": "📊 Session Analytics",
            "description": "Tracks productivity patterns, activity types, and analysis confidence over time"
        },
        {
            "name": "💾 Response Caching",
            "description": "Caches analysis results to speed up repeated queries"
        },
        {
            "name": "📈 Real-time Feedback",
            "description": "Continuous AI assistance during work sessions with live OCR integration"
        },
        {
            "name": "🎨 Customizable Interface",
            "description": "Configurable GUI with multiple views for different analysis aspects"
        },
        {
            "name": "💾 Export/Import",
            "description": "Save analysis sessions, export insights, and share configurations"
        }
    ]
    
    for i, feature in enumerate(features, 1):
        print(f"{i:2d}. {feature['name']}")
        print(f"    {feature['description']}")
        print()


def main():
    """Main demo function"""
    if len(sys.argv) > 1 and sys.argv[1] == "features":
        show_feature_overview()
        return 0
    
    # Run the interactive demo
    demo_result = demo_prompt_system()
    
    if demo_result == 0:
        show_feature_overview()
    
    return demo_result


if __name__ == "__main__":
    sys.exit(main())