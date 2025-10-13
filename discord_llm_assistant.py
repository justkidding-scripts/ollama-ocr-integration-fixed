#!/usr/bin/env python3
"""
Discord LLM Assistant
Connects OCR bridge to LLMs for real-time Discord screenshare analysis
"""

import asyncio
import json
import time
import requests
from typing import Dict, List, Optional
from datetime import datetime
import subprocess
import signal
import sys

from llm_ocr_bridge import LLMOCRBridge, ScreenContext, OCRFrame


class DiscordLLMAssistant:
    """LLM assistant that analyzes Discord screenshare content in real-time"""
    
    def __init__(self, llm_config: Dict = None):
        self.llm_config = llm_config or self.get_default_llm_config()
        self.bridge = LLMOCRBridge()
        self.conversation_history = []
        self.analysis_count = 0
        self.session_start = time.time()
        
        # Setup callbacks
        self.bridge.add_context_callback(self.on_context_update)
        self.bridge.add_text_callback(self.on_text_detected)
        
    def get_default_llm_config(self) -> Dict:
        """Default LLM configuration"""
        return {
            "provider": "local",  # "openai", "anthropic", "local", "ollama"
            "model": "llama3.2:latest",
            "api_url": "http://localhost:11434/api/generate",
            "max_tokens": 500,
            "temperature": 0.3,
            "system_prompt": """You are an AI assistant analyzing a user's screen in real-time during a Discord screenshare. 
Your role is to:
1. Identify what the user is currently doing
2. Provide helpful insights or suggestions
3. Answer questions about the screen content
4. Assist with technical tasks when possible

Keep responses concise and actionable. Focus on what's currently visible and changing on screen."""
        }
    
    def on_text_detected(self, frame: OCRFrame):
        """Handle individual OCR frame detection"""
        print(f"👁️  OCR Frame {frame.frame_id}: {frame.text[:80]}...")
        
        # Log significant text changes
        if len(frame.text) > 20:  # Only log substantial text
            timestamp = datetime.fromtimestamp(frame.timestamp).strftime("%H:%M:%S")
            print(f"📄 [{timestamp}] Detected: {frame.text[:100]}...")
    
    def on_context_update(self, context: ScreenContext):
        """Handle context updates from OCR bridge"""
        if not context.current_text or len(context.current_text) < 10:
            return
            
        # Only analyze every few updates to avoid spam
        self.analysis_count += 1
        if self.analysis_count % 3 != 0:
            return
            
        print(f"\n🧠 Analyzing screen context (update #{self.analysis_count})...")
        self.analyze_screen_content(context)
    
    def analyze_screen_content(self, context: ScreenContext):
        """Send screen context to LLM for analysis"""
        try:
            # Build analysis prompt
            prompt = self.build_analysis_prompt(context)
            
            # Get LLM response
            response = self.query_llm(prompt)
            
            if response:
                print(f"\n🤖 AI Analysis:")
                print(f"📝 {response}")
                print("-" * 60)
                
                # Store in conversation history
                self.conversation_history.append({
                    "timestamp": time.time(),
                    "context": context.current_text[:200],
                    "analysis": response
                })
                
                # Keep history manageable
                if len(self.conversation_history) > 20:
                    self.conversation_history = self.conversation_history[-15:]
                    
        except Exception as e:
            print(f"❌ Analysis error: {e}")
    
    def build_analysis_prompt(self, context: ScreenContext) -> str:
        """Build prompt for LLM analysis"""
        recent_activity = " -> ".join(context.recent_changes[-3:]) if context.recent_changes else "No recent changes"
        
        prompt = f"""Current screen shows: "{context.current_text}"

Recent activity: {recent_activity}

Session stats: {context.session_stats}

What is the user currently doing? Provide a brief analysis and any helpful suggestions."""
        
        return prompt
    
    def query_llm(self, prompt: str) -> Optional[str]:
        """Query the configured LLM service"""
        if self.llm_config["provider"] == "ollama":
            return self.query_ollama(prompt)
        elif self.llm_config["provider"] == "openai":
            return self.query_openai(prompt)
        elif self.llm_config["provider"] == "local":
            return self.query_local_llm(prompt)
        else:
            print(f"❌ Unsupported LLM provider: {self.llm_config['provider']}")
            return None
    
    def query_ollama(self, prompt: str) -> Optional[str]:
        """Query Ollama local LLM"""
        try:
            payload = {
                "model": self.llm_config["model"],
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.llm_config["temperature"],
                    "num_predict": self.llm_config["max_tokens"]
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
                print(f"❌ Ollama API error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Ollama query error: {e}")
            return None
    
    def query_openai(self, prompt: str) -> Optional[str]:
        """Query OpenAI API"""
        try:
            import openai
            
            response = openai.ChatCompletion.create(
                model=self.llm_config["model"],
                messages=[
                    {"role": "system", "content": self.llm_config["system_prompt"]},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.llm_config["max_tokens"],
                temperature=self.llm_config["temperature"]
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"❌ OpenAI query error: {e}")
            return None
    
    def query_local_llm(self, prompt: str) -> Optional[str]:
        """Query local LLM via subprocess"""
        try:
            # Example for local model via command line
            # Adjust command based on your local LLM setup
            cmd = ["python3", "-c", f"""
import sys
# Placeholder for local LLM integration
print("Local LLM analysis: User appears to be working with text content.")
print("Suggestion: Consider using OCR confidence scores for better accuracy.")
"""]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                print(f"❌ Local LLM error: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"❌ Local LLM query error: {e}")
            return None
    
    def interactive_mode(self):
        """Interactive mode for asking questions about screen content"""
        print("\n💬 Interactive Mode Started")
        print("💡 Ask questions about what's on screen, or type 'exit' to quit")
        
        while True:
            try:
                user_input = input("\n❓ Your question: ").strip()
                
                if user_input.lower() in ['exit', 'quit', 'stop']:
                    break
                
                if not user_input:
                    continue
                
                # Get current screen context
                context = self.bridge.get_current_context()
                
                # Build interactive prompt
                prompt = f"""Current screen content: "{context.current_text}"

User question: {user_input}

Please answer based on what's currently visible on the screen."""
                
                # Get LLM response
                response = self.query_llm(prompt)
                
                if response:
                    print(f"\n🤖 AI Response: {response}")
                else:
                    print("❌ Sorry, I couldn't process that question.")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Interactive mode error: {e}")
        
        print("💬 Interactive mode ended")
    
    def start(self):
        """Start the Discord LLM assistant"""
        print("🚀 Starting Discord LLM Assistant...")
        
        # Start OCR bridge
        self.bridge.start()
        
        # Setup signal handlers
        def signal_handler(sig, frame):
            print("\n🛑 Shutting down Discord LLM Assistant...")
            self.bridge.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        print("✅ Discord LLM Assistant is running!")
        print("📺 Start your Discord screenshare now")
        print("🤖 AI will analyze screen content in real-time")
        print("💡 Press Ctrl+I for interactive mode, Ctrl+C to quit")
        
        # Main loop
        try:
            while True:
                time.sleep(1)
                
                # Check for interactive mode trigger (simplified)
                # In a real implementation, you might use keyboard listeners
                
        except KeyboardInterrupt:
            self.bridge.stop()
            print("👋 Discord LLM Assistant stopped")


def create_assistant_config():
    """Helper to create configuration file"""
    config = {
        "llm": {
            "provider": "ollama",  # Change to your preferred provider
            "model": "llama3.2:latest",
            "api_url": "http://localhost:11434/api/generate",
            "max_tokens": 300,
            "temperature": 0.3
        },
        "ocr": {
            "regions": [
                {"name": "main_content", "x": 200, "y": 150, "width": 1000, "height": 700}
            ],
            "fps": 3,  # Lower FPS for LLM analysis
            "quality_mode_interval": 5
        }
    }
    
    with open("discord_llm_config.json", "w") as f:
        json.dump(config, f, indent=2)
    
    print("📄 Created discord_llm_config.json")
    print("💡 Edit this file to customize LLM provider and OCR regions")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Discord LLM Assistant")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--create-config", action="store_true", help="Create sample configuration")
    parser.add_argument("--provider", choices=["ollama", "openai", "local"], default="ollama", help="LLM provider")
    parser.add_argument("--model", default="llama3.2:latest", help="LLM model name")
    parser.add_argument("--interactive", "-i", action="store_true", help="Start in interactive mode")
    
    args = parser.parse_args()
    
    if args.create_config:
        create_assistant_config()
        return
    
    # Setup LLM configuration
    llm_config = {
        "provider": args.provider,
        "model": args.model,
        "api_url": "http://localhost:11434/api/generate" if args.provider == "ollama" else None,
        "max_tokens": 300,
        "temperature": 0.3,
        "system_prompt": """You are an AI assistant analyzing screen content during a live Discord screenshare. 
Provide helpful, concise insights about what the user is doing and suggest improvements when appropriate."""
    }
    
    # Create assistant
    assistant = DiscordLLMAssistant(llm_config)
    
    # Start assistant
    assistant.start()
    
    # Enter interactive mode if requested
    if args.interactive:
        time.sleep(2)  # Let OCR bridge initialize
        assistant.interactive_mode()


if __name__ == "__main__":
    main()