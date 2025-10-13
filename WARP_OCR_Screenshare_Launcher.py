#!/usr/bin/env python3
"""
WARP OCR Screenshare Launcher
Complete launcher for Discord OCR integration with WARP Terminal
Auto-installs dependencies and provides one-click OCR screenshare functionality
"""

import os
import sys
import subprocess
import json
import time
import threading
import signal
from pathlib import Path
from typing import Dict, List, Any, Optional
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime
import webbrowser

class WARPOCRLauncher:
    """WARP-integrated OCR Screenshare launcher with dependency management"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("WARP OCR Screenshare Launcher")
        self.root.geometry("900x700")
        self.root.resizable(True, True)
        
        # Current directory (Screenshare module location)
        self.module_path = Path(__file__).parent.resolve()
        self.home_path = Path.home()
        
        # Dependency configuration
        self.dependencies = {
            'system': {
                'tesseract-ocr': 'OCR engine',
                'python3-tk': 'GUI framework', 
                'python3-pip': 'Python package manager',
                'python3-venv': 'Virtual environments',
                'git': 'Version control'
            },
            'python': {
                'pytesseract': 'OCR Python wrapper',
                'pillow': 'Image processing',
                'mss': 'Screen capture',
                'psutil': 'Process management',
                'requests': 'HTTP requests',
                'PyQt5': 'Advanced GUI framework'
            },
            'optional': {
                'ollama': 'Local LLM server',
                'curl': 'HTTP client'
            }
        }
        
        # OCR Services configuration
        self.ocr_services = {
            'llm_assistant': {
                'name': 'Discord LLM Assistant',
                'script': 'discord_llm_assistant.py',
                'description': 'AI-powered real-time analysis',
                'auto_start': True,
                'icon': '🤖'
            },
            'overlay': {
                'name': 'Visual OCR Overlay', 
                'script': 'discord_screenshare_ocr_overlay.py',
                'description': 'Transparent text overlay',
                'auto_start': False,
                'icon': '🎥'
            },
            'bridge': {
                'name': 'OCR Bridge Service',
                'script': 'llm_ocr_bridge.py', 
                'description': 'Core OCR processing',
                'auto_start': True,
                'icon': '🌉'
            }
        }
        
        # Running processes
        self.processes = {}
        self.running_services = set()
        
        # Setup GUI
        self.setup_gui()
        self.check_warp_integration()
        
    def setup_gui(self):
        """Setup the main GUI interface"""
        # Create notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Main launch tab
        main_frame = ttk.Frame(notebook)
        notebook.add(main_frame, text="🚀 Launch OCR")
        self.setup_main_tab(main_frame)
        
        # Dependencies tab
        deps_frame = ttk.Frame(notebook)
        notebook.add(deps_frame, text="📦 Dependencies")
        self.setup_deps_tab(deps_frame)
        
        # WARP Integration tab
        warp_frame = ttk.Frame(notebook)
        notebook.add(warp_frame, text="⚡ WARP Integration")
        self.setup_warp_tab(warp_frame)
        
        # Logs tab
        log_frame = ttk.Frame(notebook)
        notebook.add(log_frame, text="📋 Logs")
        self.setup_log_tab(log_frame)
        
    def setup_main_tab(self, parent):
        """Setup main OCR launch tab"""
        # Title
        title_label = ttk.Label(parent, text="🎥 WARP OCR Screenshare System", 
                               font=('Arial', 18, 'bold'))
        title_label.pack(pady=15)
        
        subtitle_label = ttk.Label(parent, text="Real-time OCR analysis for Discord screenshare", 
                                  font=('Arial', 12), foreground='gray')
        subtitle_label.pack(pady=5)
        
        # Status frame
        status_frame = ttk.LabelFrame(parent, text="System Status", padding=10)
        status_frame.pack(fill='x', padx=20, pady=10)
        
        self.status_var = tk.StringVar(value="🟡 Initializing...")
        status_label = ttk.Label(status_frame, textvariable=self.status_var, 
                                font=('Arial', 12, 'bold'))
        status_label.pack()
        
        # Quick Launch buttons
        launch_frame = ttk.LabelFrame(parent, text="Quick Launch", padding=15)
        launch_frame.pack(fill='x', padx=20, pady=10)
        
        quick_buttons = [
            ("🎯 Start All OCR Services", self.start_all_services, "Start complete OCR system"),
            ("🤖 LLM Assistant Only", lambda: self.start_service('llm_assistant'), "AI analysis only"),
            ("🎥 Visual Overlay Only", lambda: self.start_service('overlay'), "Visual overlay only"),
            ("🛑 Stop All Services", self.stop_all_services, "Stop everything")
        ]
        
        for i, (text, command, desc) in enumerate(quick_buttons):
            btn_frame = ttk.Frame(launch_frame)
            btn_frame.pack(fill='x', pady=3)
            
            btn = ttk.Button(btn_frame, text=text, command=command, width=25)
            btn.pack(side='left', padx=5)
            
            desc_label = ttk.Label(btn_frame, text=desc, foreground='gray')
            desc_label.pack(side='left', padx=10)
        
        # Services status
        services_frame = ttk.LabelFrame(parent, text="Service Status", padding=10)
        services_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        self.service_labels = {}
        for service_id, service_info in self.ocr_services.items():
            service_frame = ttk.Frame(services_frame)
            service_frame.pack(fill='x', pady=2)
            
            # Service icon and name
            name_label = ttk.Label(service_frame, 
                                  text=f"{service_info['icon']} {service_info['name']}",
                                  font=('Arial', 10, 'bold'))
            name_label.pack(side='left')
            
            # Status label
            status_label = ttk.Label(service_frame, text="⚪ Stopped", foreground='red')
            status_label.pack(side='right')
            self.service_labels[service_id] = status_label
            
            # Description
            desc_label = ttk.Label(service_frame, text=service_info['description'], 
                                  foreground='gray', font=('Arial', 9))
            desc_label.pack(side='left', padx=10)
    
    def setup_deps_tab(self, parent):
        """Setup dependencies management tab"""
        # Title
        title_label = ttk.Label(parent, text="📦 Dependency Management", 
                               font=('Arial', 16, 'bold'))
        title_label.pack(pady=10)
        
        # Auto-install frame
        auto_frame = ttk.LabelFrame(parent, text="Automatic Installation", padding=10)
        auto_frame.pack(fill='x', padx=20, pady=10)
        
        install_all_btn = ttk.Button(auto_frame, text="🚀 Install All Dependencies", 
                                    command=self.install_all_dependencies,
                                    style='Accent.TButton')
        install_all_btn.pack(pady=5)
        
        ttk.Label(auto_frame, text="Automatically installs all required packages", 
                 foreground='gray').pack()
        
        # Manual check frame
        manual_frame = ttk.LabelFrame(parent, text="Manual Check", padding=10)
        manual_frame.pack(fill='x', padx=20, pady=10)
        
        check_btn = ttk.Button(manual_frame, text="🔍 Check Dependencies", 
                              command=self.check_dependencies)
        check_btn.pack(pady=5)
        
        # Dependencies display
        self.deps_display = ttk.Frame(parent)
        self.deps_display.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(parent, variable=self.progress_var, 
                                           maximum=100, mode='determinate')
        self.progress_bar.pack(fill='x', padx=20, pady=5)
        
    def setup_warp_tab(self, parent):
        """Setup WARP integration tab"""
        # Title
        title_label = ttk.Label(parent, text="⚡ WARP Terminal Integration", 
                               font=('Arial', 16, 'bold'))
        title_label.pack(pady=10)
        
        # WARP status
        warp_status_frame = ttk.LabelFrame(parent, text="WARP Status", padding=10)
        warp_status_frame.pack(fill='x', padx=20, pady=10)
        
        self.warp_status_var = tk.StringVar(value="🔍 Checking WARP integration...")
        warp_status_label = ttk.Label(warp_status_frame, textvariable=self.warp_status_var)
        warp_status_label.pack()
        
        # Integration options
        integration_frame = ttk.LabelFrame(parent, text="Integration Options", padding=10)
        integration_frame.pack(fill='x', padx=20, pady=10)
        
        integration_buttons = [
            ("🔗 Register with WARP", self.register_with_warp, "Add OCR to WARP command palette"),
            ("🖥️ Create WARP Alias", self.create_warp_alias, "Create 'ocr-screenshare' command"),
            ("📋 Copy WARP Command", self.copy_warp_command, "Copy command for WARP terminal"),
            ("🌐 Open WARP Docs", lambda: webbrowser.open("https://docs.warp.dev"), "WARP documentation")
        ]
        
        for text, command, desc in integration_buttons:
            btn_frame = ttk.Frame(integration_frame)
            btn_frame.pack(fill='x', pady=2)
            
            btn = ttk.Button(btn_frame, text=text, command=command, width=25)
            btn.pack(side='left', padx=5)
            
            desc_label = ttk.Label(btn_frame, text=desc, foreground='gray')
            desc_label.pack(side='left', padx=10)
        
        # WARP command display
        command_frame = ttk.LabelFrame(parent, text="WARP Commands", padding=10)
        command_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        self.warp_commands = scrolledtext.ScrolledText(command_frame, height=8, wrap=tk.WORD)
        self.warp_commands.pack(fill='both', expand=True)
        
        # Populate with example commands
        example_commands = """# WARP OCR Screenshare Commands

# Start complete OCR system
python3 /media/nike/5f57e86a-891a-4785-b1c8-fae01ada4edd1/Modular\\ Deepdive/Screenshare/WARP_OCR_Screenshare_Launcher.py

# Quick start LLM assistant
./start_discord_ai.sh

# Visual overlay only
python3 discord_screenshare_ocr_overlay.py

# Background service management
python3 /home/nike/personal-enhancement-systems/discord_ocr_service.py --status

# Create WARP alias (add to ~/.zshrc or ~/.bashrc)
alias ocr-screenshare="python3 /media/nike/5f57e86a-891a-4785-b1c8-fae01ada4edd1/Modular\\ Deepdive/Screenshare/WARP_OCR_Screenshare_Launcher.py"
"""
        self.warp_commands.insert(tk.END, example_commands)
        
    def setup_log_tab(self, parent):
        """Setup logging tab"""
        # Title
        title_label = ttk.Label(parent, text="📋 System Logs", 
                               font=('Arial', 16, 'bold'))
        title_label.pack(pady=10)
        
        # Log controls
        controls_frame = ttk.Frame(parent)
        controls_frame.pack(fill='x', padx=20, pady=5)
        
        clear_btn = ttk.Button(controls_frame, text="🗑️ Clear Logs", 
                              command=self.clear_logs)
        clear_btn.pack(side='left', padx=5)
        
        auto_scroll_var = tk.BooleanVar(value=True)
        auto_scroll_check = ttk.Checkbutton(controls_frame, text="Auto-scroll", 
                                           variable=auto_scroll_var)
        auto_scroll_check.pack(side='left', padx=10)
        self.auto_scroll_var = auto_scroll_var
        
        # Log display
        self.log_text = scrolledtext.ScrolledText(parent, width=100, height=30, 
                                                 wrap=tk.WORD, font=('Courier', 9))
        self.log_text.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Initial log message
        self.log_message("🚀 WARP OCR Screenshare Launcher initialized")
        self.log_message("💡 Use the Dependencies tab to install required packages")
        self.log_message("💡 Use the Launch tab to start OCR services")
        
    def log_message(self, message: str):
        """Log message to GUI and console"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_entry)
        
        if self.auto_scroll_var.get():
            self.log_text.see(tk.END)
        
        self.root.update()
        print(log_entry.strip())
        
    def clear_logs(self):
        """Clear log display"""
        self.log_text.delete(1.0, tk.END)
        
    def check_warp_integration(self):
        """Check WARP terminal integration status"""
        def check_thread():
            try:
                # Check if running in WARP terminal
                warp_session = os.environ.get('WARP_SESSION')
                term_program = os.environ.get('TERM_PROGRAM')
                
                if warp_session or term_program == 'WarpTerminal':
                    status = "✅ Running in WARP Terminal"
                    integration_level = "Native"
                else:
                    status = "⚠️ Not detected in WARP Terminal"
                    integration_level = "External"
                    
                # Check WARP CLI availability
                try:
                    subprocess.run(['warp', '--version'], check=True, 
                                 capture_output=True, text=True)
                    cli_status = "WARP CLI available"
                except (subprocess.CalledProcessError, FileNotFoundError):
                    cli_status = "WARP CLI not found"
                
                final_status = f"{status} ({integration_level}) | {cli_status}"
                self.root.after(0, lambda: self.warp_status_var.set(final_status))
                self.root.after(0, lambda: self.log_message(f"WARP Integration: {final_status}"))
                
            except Exception as e:
                error_msg = f"❌ WARP check error: {e}"
                self.root.after(0, lambda: self.warp_status_var.set(error_msg))
                
        threading.Thread(target=check_thread, daemon=True).start()
        
    def check_dependencies(self):
        """Check all dependencies"""
        def check_thread():
            self.log_message("🔍 Checking system dependencies...")
            self.progress_var.set(10)
            
            # Clear previous display
            for widget in self.deps_display.winfo_children():
                widget.destroy()
            
            # Check system packages
            sys_frame = ttk.LabelFrame(self.deps_display, text="System Packages", padding=5)
            sys_frame.pack(fill='x', pady=5)
            
            sys_results = {}
            for pkg, desc in self.dependencies['system'].items():
                try:
                    result = subprocess.run(['dpkg', '-l', pkg], 
                                          capture_output=True, text=True)
                    installed = result.returncode == 0
                    sys_results[pkg] = installed
                    
                    status_text = "✅ Installed" if installed else "❌ Missing"
                    color = "green" if installed else "red"
                    
                    pkg_frame = ttk.Frame(sys_frame)
                    pkg_frame.pack(fill='x')
                    
                    ttk.Label(pkg_frame, text=f"{pkg} ({desc})").pack(side='left')
                    ttk.Label(pkg_frame, text=status_text, foreground=color).pack(side='right')
                    
                except Exception:
                    sys_results[pkg] = False
                    
            self.progress_var.set(50)
            
            # Check Python packages
            py_frame = ttk.LabelFrame(self.deps_display, text="Python Packages", padding=5)
            py_frame.pack(fill='x', pady=5)
            
            py_results = {}
            for pkg, desc in self.dependencies['python'].items():
                try:
                    __import__(pkg.replace('-', '_').lower())
                    py_results[pkg] = True
                    status_text = "✅ Installed"
                    color = "green"
                except ImportError:
                    py_results[pkg] = False
                    status_text = "❌ Missing"
                    color = "red"
                    
                pkg_frame = ttk.Frame(py_frame)
                pkg_frame.pack(fill='x')
                
                ttk.Label(pkg_frame, text=f"{pkg} ({desc})").pack(side='left')
                ttk.Label(pkg_frame, text=status_text, foreground=color).pack(side='right')
            
            self.progress_var.set(100)
            
            # Summary
            missing_sys = [pkg for pkg, installed in sys_results.items() if not installed]
            missing_py = [pkg for pkg, installed in py_results.items() if not installed]
            
            if not missing_sys and not missing_py:
                self.root.after(0, lambda: self.status_var.set("✅ All dependencies ready"))
                self.log_message("✅ All dependencies are installed")
            else:
                missing_count = len(missing_sys) + len(missing_py)
                self.root.after(0, lambda: self.status_var.set(f"⚠️ {missing_count} dependencies missing"))
                self.log_message(f"⚠️ Missing: {missing_count} dependencies")
                
        threading.Thread(target=check_thread, daemon=True).start()
        
    def install_all_dependencies(self):
        """Install all missing dependencies"""
        def install_thread():
            try:
                self.log_message("🚀 Installing all dependencies...")
                self.progress_var.set(5)
                
                # Update package lists
                self.log_message("📦 Updating package lists...")
                subprocess.run(['sudo', 'apt', 'update'], check=True, capture_output=True)
                self.progress_var.set(20)
                
                # Install system packages
                self.log_message("🔧 Installing system packages...")
                sys_packages = list(self.dependencies['system'].keys())
                
                subprocess.run(['sudo', 'apt', 'install', '-y'] + sys_packages, 
                             check=True, capture_output=True)
                self.progress_var.set(60)
                
                # Install Python packages
                self.log_message("🐍 Installing Python packages...")
                py_packages = list(self.dependencies['python'].keys())
                
                for pkg in py_packages:
                    try:
                        subprocess.run([sys.executable, '-m', 'pip', 'install', 
                                      '--break-system-packages', pkg], 
                                     check=True, capture_output=True)
                        self.log_message(f"✅ Installed {pkg}")
                    except subprocess.CalledProcessError as e:
                        self.log_message(f"⚠️ Failed to install {pkg}: {e}")
                        
                self.progress_var.set(100)
                
                self.log_message("🎉 Dependency installation completed!")
                self.root.after(0, lambda: self.status_var.set("✅ Dependencies installed"))
                
                # Auto-check dependencies
                self.root.after(1000, self.check_dependencies)
                
            except subprocess.CalledProcessError as e:
                self.log_message(f"❌ Installation error: {e}")
                self.root.after(0, lambda: messagebox.showerror("Error", 
                    "Installation failed. Check logs for details."))
                    
        threading.Thread(target=install_thread, daemon=True).start()
        
    def start_service(self, service_id: str):
        """Start a specific OCR service"""
        if service_id in self.running_services:
            self.log_message(f"⚠️ {self.ocr_services[service_id]['name']} already running")
            return
            
        service_info = self.ocr_services[service_id]
        script_path = self.module_path / service_info['script']
        
        if not script_path.exists():
            self.log_message(f"❌ Script not found: {script_path}")
            messagebox.showerror("Error", f"Script not found: {service_info['script']}")
            return
            
        self.log_message(f"🚀 Starting {service_info['name']}...")
        
        try:
            # Determine command
            if script_path.suffix == '.sh':
                cmd = ['/bin/bash', str(script_path)]
            else:
                cmd = [sys.executable, str(script_path)]
                
            # Start process
            process = subprocess.Popen(
                cmd,
                cwd=self.module_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            self.processes[service_id] = process
            self.running_services.add(service_id)
            
            # Update status
            self.service_labels[service_id].config(text="🟢 Running", foreground="green")
            
            # Monitor output
            self.monitor_service(service_id, process)
            
            self.log_message(f"✅ {service_info['name']} started (PID: {process.pid})")
            
        except Exception as e:
            self.log_message(f"❌ Failed to start {service_info['name']}: {e}")
            messagebox.showerror("Error", f"Failed to start {service_info['name']}: {e}")
            
    def stop_service(self, service_id: str):
        """Stop a specific service"""
        if service_id not in self.processes:
            return
            
        process = self.processes[service_id]
        service_info = self.ocr_services[service_id]
        
        try:
            if process.poll() is None:
                self.log_message(f"🛑 Stopping {service_info['name']}...")
                process.terminate()
                
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                    
                self.log_message(f"✅ {service_info['name']} stopped")
                
            del self.processes[service_id]
            self.running_services.discard(service_id)
            
            # Update status
            self.service_labels[service_id].config(text="⚪ Stopped", foreground="red")
            
        except Exception as e:
            self.log_message(f"❌ Error stopping {service_info['name']}: {e}")
            
    def start_all_services(self):
        """Start all configured OCR services"""
        self.log_message("🎯 Starting complete OCR system...")
        
        # Start services in order
        for service_id, service_info in self.ocr_services.items():
            if service_info.get('auto_start', True):
                self.start_service(service_id)
                time.sleep(0.5)  # Brief delay between starts
                
        self.status_var.set("✅ OCR System Running")
        self.log_message("🎉 Complete OCR system started!")
        self.log_message("💡 Ready for Discord screenshare")
        
    def stop_all_services(self):
        """Stop all running services"""
        self.log_message("🛑 Stopping all OCR services...")
        
        for service_id in list(self.running_services):
            self.stop_service(service_id)
            
        self.status_var.set("⚪ All services stopped")
        self.log_message("✅ All OCR services stopped")
        
    def monitor_service(self, service_id: str, process: subprocess.Popen):
        """Monitor service output"""
        def monitor_thread():
            service_info = self.ocr_services[service_id]
            
            try:
                while process.poll() is None:
                    output = process.stdout.readline()
                    if output:
                        self.root.after(0, lambda msg=output.strip(): 
                                       self.log_message(f"[{service_info['name']}] {msg}"))
                        
                # Process ended
                return_code = process.poll()
                self.root.after(0, lambda: self.log_message(
                    f"🔴 {service_info['name']} ended (exit: {return_code})"))
                
                # Update status
                if service_id in self.running_services:
                    self.running_services.discard(service_id)
                    self.root.after(0, lambda: self.service_labels[service_id].config(
                        text="🔴 Stopped", foreground="red"))
                        
            except Exception as e:
                self.root.after(0, lambda: self.log_message(
                    f"❌ Monitor error for {service_info['name']}: {e}"))
                    
        threading.Thread(target=monitor_thread, daemon=True).start()
        
    def register_with_warp(self):
        """Register OCR system with WARP"""
        self.log_message("🔗 Registering with WARP terminal...")
        
        # Create WARP configuration
        warp_config = {
            "name": "OCR Screenshare",
            "description": "Real-time OCR analysis for Discord screenshare",
            "command": f"python3 {self.module_path / 'WARP_OCR_Screenshare_Launcher.py'}",
            "icon": "🎥",
            "tags": ["ocr", "discord", "screenshare", "ai"]
        }
        
        self.log_message("✅ WARP registration prepared")
        self.log_message("💡 Use 'Create WARP Alias' for command line integration")
        
    def create_warp_alias(self):
        """Create WARP shell alias"""
        alias_command = f"alias ocr-screenshare=\"python3 '{self.module_path / 'WARP_OCR_Screenshare_Launcher.py'}'\""
        
        # Copy to clipboard if possible
        try:
            import pyperclip
            pyperclip.copy(alias_command)
            self.log_message("📋 Alias copied to clipboard")
        except ImportError:
            pass
            
        self.log_message("🔗 WARP alias created:")
        self.log_message(f"   {alias_command}")
        self.log_message("💡 Add this to your ~/.zshrc or ~/.bashrc")
        
        messagebox.showinfo("WARP Alias", 
            f"Add this line to your shell config:\n\n{alias_command}")
            
    def copy_warp_command(self):
        """Copy WARP command to clipboard"""
        command = f"python3 '{self.module_path / 'WARP_OCR_Screenshare_Launcher.py'}'"
        
        try:
            import pyperclip
            pyperclip.copy(command)
            self.log_message("📋 WARP command copied to clipboard")
            messagebox.showinfo("Copied", "Command copied to clipboard!")
        except ImportError:
            messagebox.showinfo("WARP Command", f"Command:\n{command}")
            
    def on_closing(self):
        """Handle application closing"""
        if self.running_services:
            if messagebox.askokcancel("Quit", "Stop all OCR services before closing?"):
                self.stop_all_services()
                
        self.root.destroy()
        
    def run(self):
        """Run the launcher"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Auto-check dependencies on startup
        self.root.after(1000, self.check_dependencies)
        
        self.root.mainloop()


def main():
    """Main entry point"""
    # Handle command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--install-deps':
            print("🚀 Installing dependencies...")
            launcher = WARPOCRLauncher()
            launcher.install_all_dependencies()
            return
        elif sys.argv[1] == '--start-all':
            print("🎯 Starting all OCR services...")
            launcher = WARPOCRLauncher()
            launcher.start_all_services()
            return
            
    # Run GUI launcher
    try:
        launcher = WARPOCRLauncher()
        launcher.run()
    except KeyboardInterrupt:
        print("\n👋 WARP OCR Launcher stopped")
    except Exception as e:
        print(f"❌ Launcher error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()