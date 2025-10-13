#!/bin/bash
# Quick Start Script for Discord LLM Assistant

echo "🚀 Discord LLM Assistant Quick Start"
echo "===================================="

# Check if Ollama is available (common local LLM)
if command -v ollama &> /dev/null; then
    echo "✅ Ollama found - using local LLM"
    PROVIDER="ollama"
    MODEL="llama3.2:latest"
    
    # Check if model is available
    if ! ollama list | grep -q "llama3.2"; then
        echo "⬇️ Downloading llama3.2 model..."
        ollama pull llama3.2:latest
    fi
else
    echo "⚠️ Ollama not found - using local fallback"
    PROVIDER="local"
    MODEL="placeholder"
fi

echo ""
echo "🔧 Configuration:"
echo "   Provider: $PROVIDER"
echo "   Model: $MODEL"
echo "   OCR Region: 200,150,1000,700"
echo ""

# Start the Discord LLM Assistant
echo "🎬 Starting Discord LLM Assistant..."
echo "💡 Start your Discord screenshare and the AI will analyze it!"
echo "💡 Press Ctrl+C to stop"
echo ""

python3 discord_llm_assistant.py --provider "$PROVIDER" --model "$MODEL"