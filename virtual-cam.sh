#!/bin/bash

# Virtual Camera Script - USE AFTER DISABLING SECURE BOOT
# Creates a virtual webcam device that shows your screen

echo "=== Virtual Camera Setup ==="
echo "This script requires Secure Boot to be disabled or MOK enrolled"

# Check if v4l2loopback module is available
if ! modinfo v4l2loopback &>/dev/null; then
    echo "Error: v4l2loopback-dkms not properly installed"
    echo "Install with: sudo apt install v4l2loopback-dkms"
    exit 1
fi

# Check if module is already loaded
if lsmod | grep -q v4l2loopback; then
    echo "v4l2loopback module already loaded"
else
    echo "Loading v4l2loopback module..."
    if ! sudo modprobe v4l2loopback devices=1 video_nr=10 card_label="VirtualCam" exclusive_caps=1; then
        echo "Failed to load v4l2loopback module!"
        echo "This is likely due to Secure Boot being enabled."
        echo ""
        echo "To fix this:"
        echo "1. Disable Secure Boot in BIOS/UEFI settings, or"
        echo "2. Enroll a MOK key to sign the module"
        echo ""
        echo "For MOK enrollment:"
        echo "sudo mokutil --import /var/lib/shim-signed/mok/MOK.der"
        echo "sudo update-secureboot-policy --enroll-key"
        echo "Reboot and follow the blue screen prompts"
        exit 1
    fi
fi

# Check if virtual device was created
VIRTUAL_DEVICE="/dev/video10"
if [ ! -e "$VIRTUAL_DEVICE" ]; then
    echo "Virtual device $VIRTUAL_DEVICE not found!"
    echo "Module loaded but device not created"
    exit 1
fi

echo "Virtual camera device created: $VIRTUAL_DEVICE"
echo "Device info:"
v4l2-ctl --device="$VIRTUAL_DEVICE" --info 2>/dev/null || echo "v4l2-ctl not available"

# Get screen resolution
SCREEN_SIZE=$(xdpyinfo | grep dimensions | awk '{print $2}')
echo "Screen resolution: $SCREEN_SIZE"

echo ""
echo "Starting virtual camera stream..."
echo "Your screen will be available as 'VirtualCam' in Discord/OBS/etc."
echo "Press Ctrl+C to stop"

# Stream screen to virtual camera
ffmpeg -f x11grab -s "$SCREEN_SIZE" -r 30 -i :1 \
    -f v4l2 -pix_fmt yuv420p \
    -s "$SCREEN_SIZE" -r 30 \
    "$VIRTUAL_DEVICE"

echo ""
echo "Virtual camera stopped"

# Cleanup function
cleanup() {
    echo "Cleaning up..."
    sudo rmmod v4l2loopback 2>/dev/null && echo "Module unloaded" || echo "Module cleanup failed"
}

trap cleanup EXIT