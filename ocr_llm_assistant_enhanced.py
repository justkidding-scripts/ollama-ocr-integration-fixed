#!/usr/bin/env python3
"""
Enhanced OCR LLM Assistant with Ollama Intelligent Prompting
Integrates context-aware analysis with the existing OCR screenshare system
"""

import json
import time
import threading
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
import tkinter as tk
from tkinter import ttk, scrolledtext
from datetime import datetime
import logging

# Import the Ollama prompt system
from ollama_prompt_system import OllamaPromptSystem, AnalysisResponse
from ollama_interaction import OllamaInteractionInterface


class EnhancedOCRAssistant:
    """Enhanced OCR assistant with intelligent Ollama prompting"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = Path(config_file) if config_file else Path.cwd() / "enhanced_ocr_config.json"
        self.config = self.load_config()
        
        # Initialize Ollama systems
        self.prompt_system = OllamaPromptSystem()
        self.ollama_interface = None  # Will be initialized when GUI starts
        
        # Data tracking
        self.ocr_history = []
        self.current_text = ""
        self.last_analysis_time = 0
        self.analysis_cache = {}
        
        # Setup logging
        self.setup_logging()
        
        # GUI components
        self.root = None
        self.setup_complete = False
        
        # Background processing
        self.analysis_queue = []
        self.processing_active = False
        
    def load_config(self) -> Dict:
        """Load enhanced OCR assistant configuration"""
        default_config = {
            "ocr_assistant": {
                "auto_analysis_delay": 2.0,  # seconds
                "min_text_length": 10,
                "max_history_size": 100,
                "enable_caching": True,
                "cache_expiry": 300  # seconds
            },
            "gui": {
                "window_width": 1400,
                "window_height": 900,
                "font_family": "Arial",
                "font_size": 10,
                "theme": "default"
            },
            "integration": {
                "enable_ollama_interface": True,
                "auto_start_ollama": True,
                "sync_with_overlay": True,
                "background_processing": True
            },
            "notifications": {
                "show_analysis_complete": True,
                "show_errors": True,
                "sound_enabled": False,
                "desktop_notifications": True
            }
        }
        
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    loaded = json.load(f)
                # Merge configurations
                for key, value in default_config.items():
                    if key in loaded and isinstance(value, dict):
                        default_config[key].update(loaded[key])
                    elif key in loaded:
                        default_config[key] = loaded[key]
        except Exception as e:
            print(f"Warning: Error loading config: {e}, using defaults")
            
        return default_config
    
    def save_config(self):
        """Save current configuration"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def setup_logging(self):
        """Setup logging for the enhanced assistant"""
        log_dir = Path(__file__).parent / "logs"
        log_dir.mkdir(exist_ok=True)
        
        self.logger = logging.getLogger("EnhancedOCRAssistant")
        self.logger.setLevel(logging.INFO)
        
        # Create file handler
        log_file = log_dir / f"enhanced_ocr_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
    
    def setup_gui(self):
        """Setup the enhanced GUI interface"""
        self.root = tk.Tk()
        self.root.title("Enhanced OCR Assistant with Ollama")
        self.root.geometry(f"{self.config['gui']['window_width']}x{self.config['gui']['window_height']}")
        
        # Create main paned window
        main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel - OCR content and controls
        left_frame = ttk.Frame(main_pane)
        main_pane.add(left_frame, weight=1)
        
        self.setup_ocr_panel(left_frame)
        
        # Right panel - Analysis results
        right_frame = ttk.Frame(main_pane)
        main_pane.add(right_frame, weight=1)
        
        self.setup_analysis_panel(right_frame)
        
        # Bottom panel - Status and controls
        bottom_frame = ttk.Frame(self.root)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        
        self.setup_status_panel(bottom_frame)
        
        # Menu bar
        self.setup_menu()
        
        # Initialize Ollama interface if enabled
        if self.config['integration']['enable_ollama_interface']:
            self.init_ollama_interface()
            
        self.setup_complete = True
        self.logger.info("Enhanced OCR Assistant GUI setup complete")
        
    def setup_ocr_panel(self, parent):
        """Setup the OCR content panel"""
        # Current OCR text
        ocr_frame = ttk.LabelFrame(parent, text="Current OCR Content", padding=5)
        ocr_frame.pack(fill=tk.BOTH, expand=True)
        
        # Text display with better formatting
        self.ocr_text = scrolledtext.ScrolledText(
            ocr_frame, 
            height=12, 
            wrap=tk.WORD,
            font=(self.config['gui']['font_family'], self.config['gui']['font_size']),
            state=tk.DISABLED,
            background="#f9f9f9"
        )
        self.ocr_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Controls frame
        controls_frame = ttk.Frame(ocr_frame)
        controls_frame.pack(fill=tk.X, pady=5)
        
        # Auto-analysis toggle
        self.auto_analysis_var = tk.BooleanVar(value=True)
        auto_check = ttk.Checkbutton(
            controls_frame, 
            text="Auto-analyze", 
            variable=self.auto_analysis_var
        )
        auto_check.pack(side=tk.LEFT)
        
        # Manual analysis button
        analyze_btn = ttk.Button(
            controls_frame, 
            text="Analyze Now", 
            command=self.trigger_manual_analysis
        )
        analyze_btn.pack(side=tk.LEFT, padx=5)
        
        # Clear button
        clear_btn = ttk.Button(
            controls_frame, 
            text="Clear", 
            command=self.clear_ocr_text
        )
        clear_btn.pack(side=tk.LEFT, padx=5)
        
        # Settings button
        settings_btn = ttk.Button(
            controls_frame, 
            text="Settings", 
            command=self.show_settings
        )
        settings_btn.pack(side=tk.RIGHT)
        
        # History frame
        history_frame = ttk.LabelFrame(parent, text="OCR History", padding=5)
        history_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # History listbox
        self.history_listbox = tk.Listbox(
            history_frame, 
            font=(self.config['gui']['font_family'], self.config['gui']['font_size'] - 1)
        )
        history_scrollbar = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=self.history_listbox.yview)
        self.history_listbox.configure(yscrollcommand=history_scrollbar.set)
        
        self.history_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        history_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind history selection
        self.history_listbox.bind("<<ListboxSelect>>", self.on_history_select)
        
    def setup_analysis_panel(self, parent):
        """Setup the analysis results panel"""
        # Analysis notebook
        analysis_notebook = ttk.Notebook(parent)
        analysis_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Quick Analysis tab
        quick_tab = ttk.Frame(analysis_notebook)
        analysis_notebook.add(quick_tab, text="Quick Analysis")
        
        self.setup_quick_analysis_tab(quick_tab)
        
        # Detailed Analysis tab
        detailed_tab = ttk.Frame(analysis_notebook)
        analysis_notebook.add(detailed_tab, text="Detailed Analysis")
        
        self.setup_detailed_analysis_tab(detailed_tab)
        
        # Context tab
        context_tab = ttk.Frame(analysis_notebook)
        analysis_notebook.add(context_tab, text="Context & History")
        
        self.setup_context_tab(context_tab)
        
    def setup_quick_analysis_tab(self, parent):
        """Setup quick analysis tab"""
        # Activity detection
        activity_frame = ttk.LabelFrame(parent, text="Detected Activity", padding=5)
        activity_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.activity_label = ttk.Label(
            activity_frame, 
            text="No activity detected", 
            font=(self.config['gui']['font_family'], self.config['gui']['font_size'] + 2, 'bold')
        )
        self.activity_label.pack()
        
        self.confidence_label = ttk.Label(activity_frame, text="Confidence: 0%")
        self.confidence_label.pack()
        
        # Main insight
        insight_frame = ttk.LabelFrame(parent, text="AI Insight", padding=5)
        insight_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.insight_text = scrolledtext.ScrolledText(
            insight_frame, 
            height=8, 
            wrap=tk.WORD,
            font=(self.config['gui']['font_family'], self.config['gui']['font_size']),
            state=tk.DISABLED,
            background="#e8f4fd"
        )
        self.insight_text.pack(fill=tk.BOTH, expand=True)
        
        # Quick actions
        actions_frame = ttk.LabelFrame(parent, text="Quick Actions", padding=5)
        actions_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.suggestion_buttons = []  # Will be populated dynamically
        
    def setup_detailed_analysis_tab(self, parent):
        """Setup detailed analysis tab"""
        # Analysis results notebook
        details_notebook = ttk.Notebook(parent)
        details_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Suggestions tab
        suggestions_tab = ttk.Frame(details_notebook)
        details_notebook.add(suggestions_tab, text="Suggestions")
        
        self.suggestions_tree = ttk.Treeview(
            suggestions_tab, 
            columns=("Priority", "Type", "Description"), 
            show='tree headings'
        )
        self.suggestions_tree.heading("#0", text="ID")
        self.suggestions_tree.heading("Priority", text="Priority")
        self.suggestions_tree.heading("Type", text="Type")
        self.suggestions_tree.heading("Description", text="Description")
        
        self.suggestions_tree.column("#0", width=50)
        self.suggestions_tree.column("Priority", width=80)
        self.suggestions_tree.column("Type", width=100)
        
        self.suggestions_tree.pack(fill=tk.BOTH, expand=True)
        
        # Questions tab
        questions_tab = ttk.Frame(details_notebook)
        details_notebook.add(questions_tab, text="Questions")
        
        self.questions_listbox = tk.Listbox(
            questions_tab, 
            font=(self.config['gui']['font_family'], self.config['gui']['font_size'])
        )
        questions_scrollbar = ttk.Scrollbar(questions_tab, orient=tk.VERTICAL, command=self.questions_listbox.yview)
        self.questions_listbox.configure(yscrollcommand=questions_scrollbar.set)
        
        self.questions_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        questions_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Follow-up prompts tab
        followup_tab = ttk.Frame(details_notebook)
        details_notebook.add(followup_tab, text="Follow-up")
        
        self.followup_text = scrolledtext.ScrolledText(
            followup_tab, 
            height=10, 
            wrap=tk.WORD,
            font=(self.config['gui']['font_family'], self.config['gui']['font_size']),
            state=tk.DISABLED
        )
        self.followup_text.pack(fill=tk.BOTH, expand=True)
        
    def setup_context_tab(self, parent):
        """Setup context and history tab"""
        # Session stats
        stats_frame = ttk.LabelFrame(parent, text="Session Statistics", padding=5)
        stats_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.stats_text = tk.Text(
            stats_frame, 
            height=6, 
            wrap=tk.WORD,
            font=(self.config['gui']['font_family'], self.config['gui']['font_size']),
            state=tk.DISABLED
        )
        self.stats_text.pack(fill=tk.BOTH, expand=True)
        
        # Context timeline
        timeline_frame = ttk.LabelFrame(parent, text="Activity Timeline", padding=5)
        timeline_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.timeline_tree = ttk.Treeview(
            timeline_frame,
            columns=("Time", "Activity", "Confidence", "Text Preview"),
            show='tree headings'
        )
        
        for col in ("Time", "Activity", "Confidence", "Text Preview"):
            self.timeline_tree.heading(col, text=col)
            
        self.timeline_tree.column("Time", width=80)
        self.timeline_tree.column("Activity", width=100)
        self.timeline_tree.column("Confidence", width=80)
        
        timeline_scrollbar = ttk.Scrollbar(timeline_frame, orient=tk.VERTICAL, command=self.timeline_tree.yview)
        self.timeline_tree.configure(yscrollcommand=timeline_scrollbar.set)
        
        self.timeline_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        timeline_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
    def setup_status_panel(self, parent):
        """Setup status and control panel"""
        # Status bar
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill=tk.X)
        
        self.status_var = tk.StringVar()
        self.status_var.set("Ready - Waiting for OCR input")
        status_label = ttk.Label(status_frame, textvariable=self.status_var)
        status_label.pack(side=tk.LEFT)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            status_frame, 
            variable=self.progress_var, 
            mode='indeterminate',
            length=200
        )
        self.progress_bar.pack(side=tk.RIGHT, padx=5)
        
    def setup_menu(self):
        """Setup application menu"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Export Analysis...", command=self.export_analysis)
        file_menu.add_command(label="Import Settings...", command=self.import_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Open Ollama Interface", command=self.open_ollama_interface)
        tools_menu.add_command(label="Test Ollama Connection", command=self.test_ollama_connection)
        tools_menu.add_separator()
        tools_menu.add_command(label="Clear Cache", command=self.clear_cache)
        tools_menu.add_command(label="Reset Session", command=self.reset_session)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        
    def init_ollama_interface(self):
        """Initialize the Ollama interface"""
        try:
            if not self.ollama_interface:
                self.ollama_interface = OllamaInteractionInterface()
                self.logger.info("Ollama interface initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize Ollama interface: {e}")
            
    def process_ocr_update(self, text: str, metadata: Dict = None):
        """Process OCR text update"""
        if not text or len(text.strip()) < self.config['ocr_assistant']['min_text_length']:
            return
            
        self.logger.info(f"Processing OCR update: {text[:50]}...")
        
        # Update current text
        self.current_text = text
        
        # Update GUI
        self.update_ocr_display(text)
        
        # Add to history
        self.add_to_history(text, metadata)
        
        # Trigger analysis if auto-analysis is enabled
        if self.auto_analysis_var.get() if hasattr(self, 'auto_analysis_var') else True:
            self.schedule_analysis(text, metadata)
            
        # Send to Ollama interface if available
        if self.ollama_interface:
            try:
                self.ollama_interface.process_ocr_text(text, metadata)
            except Exception as e:
                self.logger.error(f"Error sending to Ollama interface: {e}")
                
    def update_ocr_display(self, text: str):
        """Update the OCR text display"""
        if hasattr(self, 'ocr_text'):
            self.ocr_text.config(state=tk.NORMAL)
            self.ocr_text.delete(1.0, tk.END)
            self.ocr_text.insert(1.0, text)
            self.ocr_text.config(state=tk.DISABLED)
            
    def add_to_history(self, text: str, metadata: Dict = None):
        """Add text to history"""
        timestamp = time.time()
        history_entry = {
            'timestamp': timestamp,
            'text': text,
            'metadata': metadata or {},
            'preview': text[:50] + "..." if len(text) > 50 else text
        }
        
        self.ocr_history.append(history_entry)
        
        # Limit history size
        max_history = self.config['ocr_assistant']['max_history_size']
        if len(self.ocr_history) > max_history:
            self.ocr_history = self.ocr_history[-max_history:]
            
        # Update history display
        if hasattr(self, 'history_listbox'):
            time_str = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")
            display_text = f"{time_str} - {history_entry['preview']}"
            
            self.history_listbox.insert(0, display_text)
            if self.history_listbox.size() > max_history:
                self.history_listbox.delete(max_history)
                
    def schedule_analysis(self, text: str, metadata: Dict = None):
        """Schedule analysis with delay to avoid too frequent updates"""
        current_time = time.time()
        delay = self.config['ocr_assistant']['auto_analysis_delay']
        
        if current_time - self.last_analysis_time < delay:
            # Schedule delayed analysis
            if hasattr(self, 'root') and self.root:
                self.root.after(int(delay * 1000), lambda: self.perform_analysis(text, metadata))
        else:
            # Perform immediate analysis
            self.perform_analysis(text, metadata)
            
    def perform_analysis(self, text: str, metadata: Dict = None):
        """Perform analysis of the text"""
        if not text.strip():
            return
            
        # Check cache first
        cache_key = hash(text)
        if (self.config['ocr_assistant']['enable_caching'] and 
            cache_key in self.analysis_cache):
            
            cache_entry = self.analysis_cache[cache_key]
            cache_age = time.time() - cache_entry['timestamp']
            
            if cache_age < self.config['ocr_assistant']['cache_expiry']:
                self.update_analysis_display(cache_entry['result'])
                return
                
        self.last_analysis_time = time.time()
        
        # Start analysis in background
        if self.config['integration']['background_processing']:
            threading.Thread(
                target=self._analyze_background,
                args=(text, metadata),
                daemon=True
            ).start()
        else:
            self._analyze_background(text, metadata)
            
    def _analyze_background(self, text: str, metadata: Dict = None):
        """Background analysis thread"""
        try:
            if hasattr(self, 'status_var'):
                self.root.after(0, lambda: self.status_var.set("Analyzing..."))
                self.root.after(0, lambda: self.progress_bar.start())
                
            # Calculate session stats
            session_stats = {
                'session_duration': (time.time() - (self.ocr_history[0]['timestamp'] if self.ocr_history else time.time())) / 60,
                'total_entries': len(self.ocr_history),
                'current_activity': self.detect_current_activity()
            }
            
            # Perform analysis with prompt system
            result = self.prompt_system.analyze_content(
                text,
                [entry['text'] for entry in self.ocr_history[-10:]],  # Recent history
                session_stats
            )
            
            # Cache result
            if self.config['ocr_assistant']['enable_caching']:
                cache_key = hash(text)
                self.analysis_cache[cache_key] = {
                    'result': result,
                    'timestamp': time.time()
                }
                
            # Update GUI in main thread
            if hasattr(self, 'root') and self.root:
                self.root.after(0, lambda: self.update_analysis_display(result))
                
        except Exception as e:
            self.logger.error(f"Analysis error: {e}")
            if hasattr(self, 'root') and self.root:
                self.root.after(0, lambda: self.status_var.set(f"Analysis error: {e}"))
                
        finally:
            if hasattr(self, 'root') and self.root:
                self.root.after(0, lambda: self.progress_bar.stop())
                self.root.after(0, lambda: self.status_var.set("Ready"))
                
    def detect_current_activity(self) -> str:
        """Detect current activity from recent history"""
        if not self.ocr_history:
            return "unknown"
            
        recent_texts = [entry['text'] for entry in self.ocr_history[-5:]]
        combined_text = " ".join(recent_texts)
        
        return self.prompt_system.detect_activity_type(combined_text)
        
    def update_analysis_display(self, result: AnalysisResponse):
        """Update the analysis display with results"""
        if not hasattr(self, 'activity_label'):
            return
            
        # Update activity detection
        activity = result.context_tags[0] if result.context_tags else "Unknown"
        self.activity_label.config(text=activity.title())
        self.confidence_label.config(text=f"Confidence: {result.confidence:.1%}")
        
        # Update main insight
        self.insight_text.config(state=tk.NORMAL)
        self.insight_text.delete(1.0, tk.END)
        self.insight_text.insert(1.0, result.main_insight)
        self.insight_text.config(state=tk.DISABLED)
        
        # Update suggestions
        self.suggestions_tree.delete(*self.suggestions_tree.get_children())
        for i, suggestion in enumerate(result.suggestions, 1):
            priority = "High" if i <= 2 else "Medium"
            suggestion_type = "Action" if any(word in suggestion.lower() for word in ['consider', 'try', 'add']) else "Info"
            
            self.suggestions_tree.insert("", tk.END, 
                                       values=(priority, suggestion_type, suggestion))
            
        # Update questions
        self.questions_listbox.delete(0, tk.END)
        for question in result.questions:
            self.questions_listbox.insert(tk.END, question)
            
        # Update follow-up prompts
        self.followup_text.config(state=tk.NORMAL)
        self.followup_text.delete(1.0, tk.END)
        followup_content = "\n\n".join(f"• {prompt}" for prompt in result.follow_up_prompts)
        self.followup_text.insert(1.0, followup_content)
        self.followup_text.config(state=tk.DISABLED)
        
        # Add to timeline
        timestamp = datetime.fromtimestamp(result.timestamp).strftime("%H:%M:%S")
        text_preview = self.current_text[:30] + "..." if len(self.current_text) > 30 else self.current_text
        
        self.timeline_tree.insert("", 0, values=(
            timestamp, 
            activity, 
            f"{result.confidence:.1%}", 
            text_preview
        ))
        
        # Update session stats
        self.update_session_stats()
        
        self.logger.info(f"Analysis display updated for {activity} activity")
        
    def update_session_stats(self):
        """Update session statistics display"""
        if not hasattr(self, 'stats_text'):
            return
            
        stats = f"Session Duration: {(time.time() - (self.ocr_history[0]['timestamp'] if self.ocr_history else time.time())) / 60:.1f} minutes\n"
        stats += f"OCR Updates: {len(self.ocr_history)}\n"
        stats += f"Analyses Performed: {len(self.prompt_system.response_history)}\n"
        stats += f"Cache Entries: {len(self.analysis_cache)}\n"
        
        if self.prompt_system.response_history:
            avg_confidence = sum(r.confidence for r in self.prompt_system.response_history) / len(self.prompt_system.response_history)
            stats += f"Average Confidence: {avg_confidence:.1%}\n"
            
        # Activity breakdown
        activities = {}
        for result in self.prompt_system.response_history[-20:]:  # Recent 20 analyses
            activity = result.context_tags[0] if result.context_tags else "unknown"
            activities[activity] = activities.get(activity, 0) + 1
            
        if activities:
            stats += "\nRecent Activity Breakdown:\n"
            for activity, count in sorted(activities.items(), key=lambda x: x[1], reverse=True):
                stats += f"  {activity.title()}: {count}\n"
                
        self.stats_text.config(state=tk.NORMAL)
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(1.0, stats)
        self.stats_text.config(state=tk.DISABLED)
        
    # Event handlers and commands
    def trigger_manual_analysis(self):
        """Trigger manual analysis of current text"""
        if self.current_text:
            self.perform_analysis(self.current_text)
        else:
            if hasattr(self, 'status_var'):
                self.status_var.set("No text available for analysis")
                
    def clear_ocr_text(self):
        """Clear current OCR text"""
        self.current_text = ""
        if hasattr(self, 'ocr_text'):
            self.ocr_text.config(state=tk.NORMAL)
            self.ocr_text.delete(1.0, tk.END)
            self.ocr_text.config(state=tk.DISABLED)
            
    def on_history_select(self, event):
        """Handle history item selection"""
        selection = self.history_listbox.curselection()
        if selection:
            index = selection[0]
            if index < len(self.ocr_history):
                entry = self.ocr_history[-(index + 1)]  # Reverse order
                self.update_ocr_display(entry['text'])
                self.current_text = entry['text']
                
    def clear_cache(self):
        """Clear analysis cache"""
        self.analysis_cache.clear()
        if hasattr(self, 'status_var'):
            self.status_var.set("Cache cleared")
        self.logger.info("Analysis cache cleared")
        
    def reset_session(self):
        """Reset session data"""
        self.ocr_history.clear()
        self.analysis_cache.clear()
        self.prompt_system.response_history.clear()
        self.current_text = ""
        
        # Clear GUI displays
        if hasattr(self, 'history_listbox'):
            self.history_listbox.delete(0, tk.END)
        if hasattr(self, 'timeline_tree'):
            self.timeline_tree.delete(*self.timeline_tree.get_children())
            
        self.logger.info("Session reset")
        
    def test_ollama_connection(self):
        """Test connection to Ollama"""
        def test_connection():
            try:
                response = self.prompt_system.query_ollama("Test connection")
                if response:
                    self.root.after(0, lambda: self.status_var.set("Ollama connection successful"))
                else:
                    self.root.after(0, lambda: self.status_var.set("Ollama connection failed"))
            except Exception as e:
                self.root.after(0, lambda: self.status_var.set(f"Ollama error: {e}"))
                
        threading.Thread(target=test_connection, daemon=True).start()
        
    def open_ollama_interface(self):
        """Open the Ollama interface window"""
        if not self.ollama_interface:
            self.init_ollama_interface()
            
        if self.ollama_interface:
            # Create new window for Ollama interface
            interface_window = tk.Toplevel(self.root)
            interface_window.title("Ollama Analysis Interface")
            interface_window.geometry("1000x700")
            
            # Move the Ollama interface to the new window
            # Note: This is a simplified approach - in practice, you might want to
            # create a separate interface or modify the existing one
            
    def show_settings(self):
        """Show settings dialog"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Enhanced OCR Assistant Settings")
        settings_window.geometry("500x400")
        settings_window.grab_set()
        
        # Settings notebook
        settings_notebook = ttk.Notebook(settings_window)
        settings_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # General settings
        general_frame = ttk.Frame(settings_notebook)
        settings_notebook.add(general_frame, text="General")
        
        ttk.Label(general_frame, text="Auto-analysis delay (seconds):").pack(anchor=tk.W)
        delay_var = tk.DoubleVar(value=self.config['ocr_assistant']['auto_analysis_delay'])
        ttk.Scale(general_frame, from_=0.5, to=5.0, variable=delay_var, orient=tk.HORIZONTAL).pack(fill=tk.X)
        
        ttk.Label(general_frame, text="Minimum text length:").pack(anchor=tk.W, pady=(10, 0))
        min_length_var = tk.IntVar(value=self.config['ocr_assistant']['min_text_length'])
        ttk.Spinbox(general_frame, from_=1, to=100, textvariable=min_length_var).pack(anchor=tk.W)
        
        # Integration settings
        integration_frame = ttk.Frame(settings_notebook)
        settings_notebook.add(integration_frame, text="Integration")
        
        auto_ollama_var = tk.BooleanVar(value=self.config['integration']['auto_start_ollama'])
        ttk.Checkbutton(integration_frame, text="Auto-start Ollama interface", 
                       variable=auto_ollama_var).pack(anchor=tk.W)
        
        background_var = tk.BooleanVar(value=self.config['integration']['background_processing'])
        ttk.Checkbutton(integration_frame, text="Background processing", 
                       variable=background_var).pack(anchor=tk.W)
        
        # Save button
        def save_settings():
            self.config['ocr_assistant']['auto_analysis_delay'] = delay_var.get()
            self.config['ocr_assistant']['min_text_length'] = min_length_var.get()
            self.config['integration']['auto_start_ollama'] = auto_ollama_var.get()
            self.config['integration']['background_processing'] = background_var.get()
            
            self.save_config()
            settings_window.destroy()
            
        ttk.Button(settings_window, text="Save", command=save_settings).pack(pady=10)
        
    def export_analysis(self):
        """Export analysis data"""
        from tkinter import filedialog
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            export_data = {
                'session_info': {
                    'start_time': self.ocr_history[0]['timestamp'] if self.ocr_history else time.time(),
                    'export_time': time.time(),
                    'total_entries': len(self.ocr_history)
                },
                'ocr_history': self.ocr_history,
                'analysis_results': [result.__dict__ for result in self.prompt_system.response_history],
                'config': self.config
            }
            
            try:
                with open(filename, 'w') as f:
                    json.dump(export_data, f, indent=2, default=str)
                self.status_var.set(f"Analysis exported to {filename}")
            except Exception as e:
                self.status_var.set(f"Export failed: {e}")
                
    def import_settings(self):
        """Import settings from file"""
        from tkinter import filedialog
        
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'r') as f:
                    imported_config = json.load(f)
                    
                if 'config' in imported_config:
                    self.config.update(imported_config['config'])
                    self.save_config()
                    self.status_var.set("Settings imported successfully")
                else:
                    self.status_var.set("Invalid settings file")
            except Exception as e:
                self.status_var.set(f"Import failed: {e}")
                
    def show_about(self):
        """Show about dialog"""
        about_text = """Enhanced OCR Assistant with Ollama Integration

Features:
• Intelligent context-aware analysis
• Real-time OCR text processing
• Advanced prompting with Ollama
• Activity detection and classification
• Analysis history and caching
• Customizable settings and themes

Built for advanced productivity and AI-assisted analysis.
"""
        
        from tkinter import messagebox
        messagebox.showinfo("About Enhanced OCR Assistant", about_text)
        
    def on_closing(self):
        """Handle application closing"""
        try:
            self.save_config()
            self.logger.info("Enhanced OCR Assistant shutting down")
            
            # Stop any background threads
            self.processing_active = False
            
            # Clean up Ollama interface
            if self.ollama_interface and hasattr(self.ollama_interface, 'root'):
                try:
                    if self.ollama_interface.root.winfo_exists():
                        self.ollama_interface.root.destroy()
                except (tk.TclError, AttributeError):
                    pass
                    
            # Destroy main window
            if self.root and self.root.winfo_exists():
                self.root.destroy()
                
        except (tk.TclError, AttributeError) as e:
            # Window already destroyed
            print(f"Window cleanup completed: {e}")
        except Exception as e:
            print(f"Error during shutdown: {e}")
        
    def run(self):
        """Start the enhanced OCR assistant"""
        self.setup_gui()
        
        # Setup close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Update stats periodically
        def update_stats():
            try:
                if self.root and self.root.winfo_exists():
                    self.update_session_stats()
                    self.root.after(5000, update_stats)  # Update every 5 seconds
            except tk.TclError:
                # Window destroyed, stop updates
                return
            except Exception as e:
                print(f"Error in stats update: {e}")
                
        self.root.after(1000, update_stats)
        
        self.logger.info("Starting Enhanced OCR Assistant")
        self.root.mainloop()


def main():
    """Main function to run the enhanced OCR assistant"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced OCR Assistant with Ollama")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--test", action="store_true", help="Run with test data")
    
    args = parser.parse_args()
    
    assistant = EnhancedOCRAssistant(args.config)
    
    if args.test:
        # Add test data after a delay
        def add_test_data():
            test_texts = [
                "def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)",
                "Research methodology involves systematic investigation using scientific methods",
                "Welcome to our presentation on machine learning applications in healthcare",
                "sudo apt update && sudo apt install python3-opencv pytesseract"
            ]
            
            for i, text in enumerate(test_texts):
                assistant.root.after((i + 1) * 3000, lambda t=text: assistant.process_ocr_update(t))
                
        assistant.root.after(2000, add_test_data)
    
    assistant.run()


if __name__ == "__main__":
    main()