#!/bin/bash

# Discord Screen Sharing Setup for Linux with PipeWire
# Enables native screen sharing without virtual camera

echo "=== Discord Screen Sharing Setup ==="
echo "Setting up Discord for native screen sharing on X11 with PipeWire"

# Check current environment
echo "Environment check:"
echo "Display: $DISPLAY"
echo "Session: $XDG_SESSION_TYPE" 
echo "Desktop: $XDG_CURRENT_DESKTOP"

# Check PipeWire status
echo -e "\nPipeWire status:"
systemctl --user status pipewire.service | grep Active || echo "PipeWire not running"

# Check xdg-desktop-portal status
echo -e "\nDesktop portal status:"
systemctl --user status xdg-desktop-portal.service | grep Active || echo "Portal not running"

# Create Discord wrapper with WebRTC flags
DISCORD_WRAPPER="/media/nike/5f57e86a-891a-4785-b1c8-fae01ada4edd1/Modular Deepdive/Screenshare/discord-with-screenshare.sh"

cat > "$DISCORD_WRAPPER" << 'EOF'
#!/bin/bash
# Discord launcher with screen sharing support

# Enable WebRTC PipeWire capturer
export DISCORD_FLAGS="--enable-features=WebRTCPipeWireCapturer,WebRTCDesktopCaptureLinux"

# Additional Electron flags for better screen capture
export DISCORD_FLAGS="$DISCORD_FLAGS --enable-gpu-rasterization"
export DISCORD_FLAGS="$DISCORD_FLAGS --enable-zero-copy"
export DISCORD_FLAGS="$DISCORD_FLAGS --ozone-platform=x11"

echo "Starting Discord with screen sharing support..."
echo "Flags: $DISCORD_FLAGS"

# Launch Discord with flags
exec /usr/bin/discord $DISCORD_FLAGS "$@"
EOF

chmod +x "$DISCORD_WRAPPER"

# Create desktop entry for Discord with screen sharing
DESKTOP_ENTRY="$HOME/.local/share/applications/discord-screenshare.desktop"
mkdir -p "$HOME/.local/share/applications"

cat > "$DESKTOP_ENTRY" << EOF
[Desktop Entry]
Name=Discord (with Screen Share)
Comment=All-in-one voice, video and text chat for gamers (Screen Share Enabled)
GenericName=Internet Messenger
Exec=$DISCORD_WRAPPER
Icon=discord
Type=Application
Categories=Network;InstantMessaging;
Path=/usr/bin
EOF

echo -e "\nSetup complete!"
echo "Created Discord wrapper: $DISCORD_WRAPPER"
echo "Created desktop entry: $DESKTOP_ENTRY"

echo -e "\nTo use Discord screen sharing:"
echo "1. Launch Discord using the new desktop entry 'Discord (with Screen Share)'"
echo "2. Or run directly: $DISCORD_WRAPPER"
echo "3. In Discord voice channel, click camera icon and select 'Screen'"
echo "4. Choose your screen or specific window"

echo -e "\nTroubleshooting:"
echo "- If screen sharing doesn't work, try browser Discord first"
echo "- Ensure xdg-desktop-portal-gtk is running: systemctl --user status xdg-desktop-portal.service"
echo "- Check Discord logs in ~/.config/discord/logs/"

# Test screen capture permissions
echo -e "\nTesting screen capture permissions..."
if command -v grim >/dev/null 2>&1; then
    echo "Taking test screenshot with grim..."
    grim "/tmp/test-screenshot.png" && echo "✓ Screen capture working" || echo "✗ Screen capture failed"
else
    echo "grim not installed - installing for testing..."
    if command -v apt >/dev/null 2>&1; then
        sudo apt update && sudo apt install -y grim
    fi
fi