# 🤖 Screenshare LLM Assistant

**Real-time OCR analysis with LLM integration for enhanced screensharing experiences**

## 🎯 Features

- **🎥 Real-time OCR**: Capture and analyze screen content during Discord screenshares
- **🤖 LLM Integration**: AI assistant analyzes screen content and provides insights
- **💬 Interactive GUI**: Dark-themed chat window for real-time interaction
- **🎹 Keystroke Logging**: Privacy-aware activity tracking (optional)
- **🏥 Health Monitoring**: System health tracking with automatic recovery
- **⚙️ Systemd Integration**: Run as a system service with automatic startup
- **🔒 Privacy Features**: Password field detection and window exclusion rules

## 📋 Installation

### Prerequisites

```bash
# Install system dependencies
sudo apt update
sudo apt install tesseract-ocr python3-venv python3-pip xdotool curl

# Optional: For better keystroke monitoring
sudo apt install python3-evdev
sudo usermod -a -G input $USER  # For evdev support
```

### Setup

```bash
# Clone or extract to ~/screenshare-assistant
cd ~/screenshare-assistant

# Install Python dependencies (already done)
source venv/bin/activate

# Verify installation
python3 screenshare_assistant_launcher.py --test-llm "Hello"
```

## 🚀 Quick Start

### Option 1: GUI Application

```bash
# Launch with GUI
python3 screenshare_assistant_launcher.py

# Or use desktop launcher
# Look for "Screenshare LLM Assistant" in your applications menu
```

### Option 2: Systemd Service

```bash
# Enable and start the service
systemctl --user enable screenshare-llm.service
systemctl --user start screenshare-llm.service

# Check status
systemctl --user status screenshare-llm.service
```

### Option 3: Headless Mode

```bash
# Run without GUI
python3 screenshare_assistant_launcher.py --headless
```

## ⚙️ Configuration

Edit `~/.config/screenshare-assistant/config.json`:

```json
{
  "llm": {
    "provider": "ollama",
    "model": "llama3.2:latest",
    "api_url": "http://localhost:11434/api/generate"
  },
  "ocr": {
    "regions": [
      {"name": "main_screen", "x": 100, "y": 100, "width": 1200, "height": 800}
    ],
    "fps": 4
  },
  "keystroke_logging": {
    "enabled": false,
    "exclude_windows": [".*password.*", "KeePass.*"]
  },
  "gui": {
    "theme": "dark",
    "always_on_top": true
  }
}
```

### OCR Regions

Define screen areas to monitor:
- **Full Screen**: `{"x": 0, "y": 0, "width": 1920, "height": 1080}`
- **Center Area**: `{"x": 400, "y": 300, "width": 1120, "height": 480}`
- **Multiple Regions**: Add multiple objects to the `regions` array

## 🔒 Privacy & Security

### Keystroke Logging

**⚠️ Privacy Notice**: Keystroke logging is **disabled by default** and requires explicit activation.

**What is logged**:
- Keystroke timing and frequency
- Window titles for context
- Key types (character vs special keys)
- Word count estimates

**What is NOT logged**:
- Actual passwords (automatically detected and redacted)
- Content from excluded windows (password managers, etc.)
- Special keys in sensitive contexts

**Exclusion Rules**:
```json
{
  "keystroke_logging": {
    "exclude_windows": [
      ".*password.*",
      ".*login.*", 
      "KeePass.*",
      "Bitwarden.*"
    ]
  }
}
```

### Data Storage

- **Keystroke logs**: `~/.local/share/screenshare-assistant/logs/keystrokes-YYYY-MM-DD.jsonl`
- **Health data**: `~/.local/share/screenshare-assistant/health.json`
- **Application logs**: `~/.local/share/screenshare-assistant/logs/health.log`
- **Configuration**: `~/.config/screenshare-assistant/config.json`

### Log Retention

- Keystroke logs: 30 days (configurable)
- Health logs: 30 days with rotation
- Automatic cleanup on startup

## 🖥️ Usage Scenarios

### 1. Discord Screenshare with AI Analysis

1. Start the assistant: `python3 screenshare_assistant_launcher.py`
2. Begin Discord screenshare
3. AI automatically analyzes screen content
4. Ask questions in the GUI chat window
5. Get real-time insights about what's on screen

### 2. Live Coding Sessions

1. Configure OCR region over your code editor
2. Enable keystroke logging for activity tracking
3. Stream provides AI commentary on code changes
4. Interactive Q&A with viewers through AI assistant

### 3. Research Presentations

1. Display documents or research materials
2. AI extracts and analyzes text content
3. Provides context and explanations in real-time
4. Answers audience questions about material

### 4. Educational Content

1. Share technical documentation or tutorials  
2. AI explains complex concepts as they appear
3. Interactive assistance for viewers
4. Real-time text extraction for accessibility

## 🔧 Systemd Service Management

### Service Commands

```bash
# Start service
systemctl --user start screenshare-llm.service

# Stop service  
systemctl --user stop screenshare-llm.service

# Restart service
systemctl --user restart screenshare-llm.service

# Enable auto-start
systemctl --user enable screenshare-llm.service

# Check status
systemctl --user status screenshare-llm.service

# View logs
journalctl --user -u screenshare-llm.service -f
```

### Health Monitoring

```bash
# Enable health checks
systemctl --user enable screenshare-llm-health.timer
systemctl --user start screenshare-llm-health.timer

# Check health manually
python3 health_monitor.py check

# View health data
cat ~/.local/share/screenshare-assistant/health.json
```

## 🛠️ Troubleshooting

### Common Issues

**1. OCR Not Working**
```bash
# Check tesseract installation
tesseract --version

# Test screen capture permissions
python3 -c "import mss; print('Screen capture:', bool(mss.mss()))"
```

**2. LLM Connection Failed**
```bash
# Check Ollama is running
curl http://localhost:11434/api/version

# Start Ollama if needed
ollama serve

# Test specific model
ollama run llama3.2:latest
```

**3. GUI Not Appearing**
```bash
# Check X11 environment
echo $DISPLAY
echo $XDG_SESSION_TYPE

# Test PyQt5 installation
python3 -c "from PyQt5.QtWidgets import QApplication; print('PyQt5 OK')"
```

**4. Permission Errors**
```bash
# For keystroke logging
sudo usermod -a -G input $USER
# Then log out and back in

# For X11 access
xhost +local:
```

**5. Systemd Service Issues**
```bash
# Check service files
systemctl --user cat screenshare-llm.service

# Reload after changes
systemctl --user daemon-reload

# Check environment variables
systemctl --user show-environment
```

### Log Analysis

```bash
# Application logs
tail -f ~/.local/share/screenshare-assistant/logs/health.log

# Keystroke logs (if enabled)
tail -f ~/.local/share/screenshare-assistant/logs/keystrokes-$(date +%Y-%m-%d).jsonl

# Systemd logs
journalctl --user -u screenshare-llm.service --since "1 hour ago"
```

## 🔗 Integration with Modular Deepdive Tools

This assistant integrates with your existing toolkit at:
- **Main Tools**: `https://github.com/justkidding-scripts/utility-tools`
- **Existing Scripts**: Compatible with current modular framework
- **Extension Points**: OCR callbacks, LLM providers, GUI plugins

### Integration Examples

```python
# Custom LLM provider
def custom_llm_handler(prompt):
    # Your existing LLM integration
    return custom_response

assistant.llm_query_callback = custom_llm_handler

# OCR data forwarding  
def forward_to_existing_tools(ocr_frame):
    # Send to your existing pipeline
    existing_tool.process_ocr(ocr_frame.text)

assistant.ocr_bridge.add_text_callback(forward_to_existing_tools)
```

## 📊 Performance Optimization

### Resource Usage

- **Memory**: ~100-300MB typical usage
- **CPU**: ~10-20% during active OCR
- **Disk**: <100MB for logs (with rotation)
- **Network**: Minimal (only LLM API calls)

### Optimization Tips

1. **Reduce OCR FPS**: Lower `fps` in config for less CPU usage
2. **Limit Regions**: Monitor only relevant screen areas  
3. **Disable Logging**: Turn off keystroke logging if not needed
4. **Local LLM**: Use Ollama to avoid API latency
5. **Headless Mode**: Run without GUI for servers/remote systems

## 📝 Advanced Configuration

### Multiple OCR Regions

```json
{
  "ocr": {
    "regions": [
      {"name": "code_area", "x": 50, "y": 100, "width": 800, "height": 600},
      {"name": "terminal", "x": 900, "y": 100, "width": 600, "height": 400},
      {"name": "browser", "x": 50, "y": 750, "width": 1450, "height": 300}
    ]
  }
}
```

### Custom LLM Providers

```json
{
  "llm": {
    "provider": "openai",
    "model": "gpt-4",
    "api_key_env": "OPENAI_API_KEY"
  }
}
```

### Enhanced Security

```json
{
  "keystroke_logging": {
    "exclude_windows": [
      ".*[Pp]assword.*",
      ".*[Ll]ogin.*",
      ".*[Aa]uthenticate.*", 
      "KeePass.*",
      "Bitwarden.*",
      "1Password.*",
      "LastPass.*",
      ".*SSH.*",
      ".*Terminal.*sudo.*"
    ]
  }
}
```

---

## 🤝 Contributing

This tool is part of a larger modular framework. For contributions:

1. Follow existing code patterns from utility-tools repository
2. Maintain compatibility with current module system  
3. Add appropriate logging and health checks
4. Include privacy considerations for any new features

## 📄 License

Licensed under the same terms as the main utility-tools project.

---

**⚡ Ready to enhance your screenshares with AI-powered analysis!**

**🎯 Perfect for educational content, live coding, research presentations, and technical demonstrations.**