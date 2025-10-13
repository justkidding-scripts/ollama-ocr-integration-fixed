#!/bin/bash
# WARP OCR Screenshare Quick Launcher
# One-click launcher for WARP Terminal integration

echo "🎥 WARP OCR Screenshare Launcher"
echo "================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAUNCHER="${SCRIPT_DIR}/WARP_OCR_Screenshare_Launcher.py"

# Check if launcher exists
if [ ! -f "$LAUNCHER" ]; then
    echo "❌ Error: WARP OCR Launcher not found at $LAUNCHER"
    exit 1
fi

echo "📍 Location: $SCRIPT_DIR"
echo "🚀 Starting WARP OCR Screenshare Launcher..."
echo ""

# Check for command line arguments
case "${1:-}" in
    "--install-deps")
        echo "📦 Installing dependencies..."
        python3 "$LAUNCHER" --install-deps
        ;;
    "--start-all")
        echo "🎯 Starting all OCR services..."
        python3 "$LAUNCHER" --start-all
        ;;
    "--help")
        echo "WARP OCR Screenshare Launcher"
        echo ""
        echo "Usage: $0 [option]"
        echo ""
        echo "Options:"
        echo "  --install-deps    Install all dependencies"
        echo "  --start-all      Start all OCR services"
        echo "  --help           Show this help"
        echo "  (no args)        Launch GUI interface"
        echo ""
        echo "WARP Integration:"
        echo "  Add to ~/.zshrc or ~/.bashrc:"
        echo "  alias ocr-screenshare=\"$0\""
        ;;
    *)
        # Default: launch GUI
        echo "💡 Launching GUI interface..."
        python3 "$LAUNCHER"
        ;;
esac