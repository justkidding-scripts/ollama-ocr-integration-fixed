#!/usr/bin/env python3
"""
Ollama Interaction Interface for OCR Screenshare System
Bridge between OCR assistant and Ollama intelligent prompting
"""

import json
import time
import asyncio
import threading
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime
import logging
from dataclasses import asdict

from ollama_prompt_system import OllamaPromptSystem, AnalysisResponse, PromptContext


class OllamaInteractionInterface:
    """Interactive interface for Ollama analysis with the OCR system"""
    
    def __init__(self, ocr_bridge_callback: Optional[Callable] = None):
        self.prompt_system = OllamaPromptSystem()
        self.ocr_bridge_callback = ocr_bridge_callback
        self.session_data = {
            'start_time': time.time(),
            'total_queries': 0,
            'successful_analyses': 0,
            'text_history': [],
            'response_cache': {}
        }
        
        # Setup logging
        self.setup_logging()
        
        # Initialize GUI
        self.setup_gui()
        
        # Thread for background processing
        self.processing_thread = None
        self.is_processing = False
        
    def setup_logging(self):
        """Setup logging for the interaction interface"""
        log_dir = Path(__file__).parent / "logs"
        log_dir.mkdir(exist_ok=True)
        
        self.logger = logging.getLogger("OllamaInterface")
        self.logger.setLevel(logging.INFO)
        
        # Create file handler
        log_file = log_dir / f"ollama_interface_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        
    def setup_gui(self):
        """Setup the GUI interface"""
        self.root = tk.Tk()
        self.root.title("Ollama OCR Analysis Interface")
        self.root.geometry("1200x800")
        
        # Create main notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Analysis Tab
        self.setup_analysis_tab(notebook)
        
        # History Tab
        self.setup_history_tab(notebook)
        
        # Config Tab
        self.setup_config_tab(notebook)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready - Waiting for OCR input")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def setup_analysis_tab(self, notebook):
        """Setup the main analysis tab"""
        analysis_frame = ttk.Frame(notebook)
        notebook.add(analysis_frame, text="Live Analysis")
        
        # Current text display
        current_frame = ttk.LabelFrame(analysis_frame, text="Current Screen Content", padding=5)
        current_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.current_text = scrolledtext.ScrolledText(current_frame, height=8, wrap=tk.WORD, 
                                                     state=tk.DISABLED)
        self.current_text.pack(fill=tk.BOTH, expand=True)
        
        # Analysis controls
        controls_frame = ttk.Frame(analysis_frame)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.auto_analyze_var = tk.BooleanVar(value=True)
        auto_check = ttk.Checkbutton(controls_frame, text="Auto-analyze", 
                                   variable=self.auto_analyze_var)
        auto_check.pack(side=tk.LEFT)
        
        analyze_btn = ttk.Button(controls_frame, text="Analyze Now", 
                               command=self.manual_analyze)
        analyze_btn.pack(side=tk.LEFT, padx=5)
        
        clear_btn = ttk.Button(controls_frame, text="Clear History", 
                             command=self.clear_history)
        clear_btn.pack(side=tk.LEFT, padx=5)
        
        # Activity type display
        activity_frame = ttk.Frame(controls_frame)
        activity_frame.pack(side=tk.RIGHT)
        
        ttk.Label(activity_frame, text="Detected Activity:").pack(side=tk.LEFT)
        self.activity_var = tk.StringVar()
        activity_label = ttk.Label(activity_frame, textvariable=self.activity_var, 
                                 font=('Arial', 10, 'bold'))
        activity_label.pack(side=tk.LEFT, padx=5)
        
        # Analysis results
        results_frame = ttk.LabelFrame(analysis_frame, text="AI Analysis Results", padding=5)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create notebook for different result types
        results_notebook = ttk.Notebook(results_frame)
        results_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Main insight tab
        insight_frame = ttk.Frame(results_notebook)
        results_notebook.add(insight_frame, text="AI Insight")
        
        self.insight_text = scrolledtext.ScrolledText(insight_frame, height=6, wrap=tk.WORD, 
                                                     state=tk.DISABLED, background="#f8f8f8")
        self.insight_text.pack(fill=tk.BOTH, expand=True)
        
        # Suggestions tab
        suggestions_frame = ttk.Frame(results_notebook)
        results_notebook.add(suggestions_frame, text="Suggestions")
        
        self.suggestions_listbox = tk.Listbox(suggestions_frame, font=('Arial', 10))
        suggestions_scrollbar = ttk.Scrollbar(suggestions_frame, orient=tk.VERTICAL, 
                                            command=self.suggestions_listbox.yview)
        self.suggestions_listbox.configure(yscrollcommand=suggestions_scrollbar.set)
        
        self.suggestions_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        suggestions_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Questions tab
        questions_frame = ttk.Frame(results_notebook)
        results_notebook.add(questions_frame, text="Questions")
        
        self.questions_listbox = tk.Listbox(questions_frame, font=('Arial', 10))
        questions_scrollbar = ttk.Scrollbar(questions_frame, orient=tk.VERTICAL, 
                                          command=self.questions_listbox.yview)
        self.questions_listbox.configure(yscrollcommand=questions_scrollbar.set)
        
        self.questions_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        questions_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Follow-up prompts tab
        followup_frame = ttk.Frame(results_notebook)
        results_notebook.add(followup_frame, text="Follow-up")
        
        self.followup_listbox = tk.Listbox(followup_frame, font=('Arial', 10))
        followup_scrollbar = ttk.Scrollbar(followup_frame, orient=tk.VERTICAL, 
                                         command=self.followup_listbox.yview)
        self.followup_listbox.configure(yscrollcommand=followup_scrollbar.set)
        
        self.followup_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        followup_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
    def setup_history_tab(self, notebook):
        """Setup the analysis history tab"""
        history_frame = ttk.Frame(notebook)
        notebook.add(history_frame, text="Analysis History")
        
        # History controls
        controls_frame = ttk.Frame(history_frame)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(controls_frame, text="Filter by:").pack(side=tk.LEFT)
        
        self.filter_var = tk.StringVar(value="all")
        filter_combo = ttk.Combobox(controls_frame, textvariable=self.filter_var,
                                  values=["all", "coding", "research", "presentation", "general"])
        filter_combo.pack(side=tk.LEFT, padx=5)
        filter_combo.bind("<<ComboboxSelected>>", self.filter_history)
        
        export_btn = ttk.Button(controls_frame, text="Export History", 
                              command=self.export_history)
        export_btn.pack(side=tk.RIGHT)
        
        # History list
        history_list_frame = ttk.Frame(history_frame)
        history_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create treeview for history
        columns = ("Time", "Activity", "Confidence", "Type")
        self.history_tree = ttk.Treeview(history_list_frame, columns=columns, show='tree headings')
        
        for col in columns:
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=100)
        
        history_scrollbar = ttk.Scrollbar(history_list_frame, orient=tk.VERTICAL, 
                                        command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=history_scrollbar.set)
        
        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        history_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind selection event
        self.history_tree.bind("<<TreeviewSelect>>", self.on_history_select)
        
        # Details frame
        details_frame = ttk.LabelFrame(history_frame, text="Analysis Details", padding=5)
        details_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.history_details = scrolledtext.ScrolledText(details_frame, height=8, wrap=tk.WORD, 
                                                        state=tk.DISABLED)
        self.history_details.pack(fill=tk.BOTH, expand=True)
        
    def setup_config_tab(self, notebook):
        """Setup the configuration tab"""
        config_frame = ttk.Frame(notebook)
        notebook.add(config_frame, text="Configuration")
        
        # Ollama settings
        ollama_frame = ttk.LabelFrame(config_frame, text="Ollama Settings", padding=5)
        ollama_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Base URL
        ttk.Label(ollama_frame, text="Base URL:").grid(row=0, column=0, sticky=tk.W)
        self.base_url_var = tk.StringVar(value=self.prompt_system.config['ollama']['base_url'])
        url_entry = ttk.Entry(ollama_frame, textvariable=self.base_url_var, width=40)
        url_entry.grid(row=0, column=1, padx=5)
        
        # Model
        ttk.Label(ollama_frame, text="Model:").grid(row=1, column=0, sticky=tk.W)
        self.model_var = tk.StringVar(value=self.prompt_system.config['ollama']['model'])
        model_entry = ttk.Entry(ollama_frame, textvariable=self.model_var, width=40)
        model_entry.grid(row=1, column=1, padx=5)
        
        # Temperature
        ttk.Label(ollama_frame, text="Temperature:").grid(row=2, column=0, sticky=tk.W)
        self.temperature_var = tk.DoubleVar(value=self.prompt_system.config['ollama']['temperature'])
        temp_scale = ttk.Scale(ollama_frame, from_=0.0, to=1.0, variable=self.temperature_var, 
                             orient=tk.HORIZONTAL, length=200)
        temp_scale.grid(row=2, column=1, padx=5)
        
        temp_label = ttk.Label(ollama_frame, textvariable=self.temperature_var)
        temp_label.grid(row=2, column=2, padx=5)
        
        # Analysis settings
        analysis_frame = ttk.LabelFrame(config_frame, text="Analysis Settings", padding=5)
        analysis_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.enable_premade_var = tk.BooleanVar(
            value=self.prompt_system.config['responses']['enable_premade_responses'])
        ttk.Checkbutton(analysis_frame, text="Enable premade responses", 
                       variable=self.enable_premade_var).pack(anchor=tk.W)
        
        self.enable_questions_var = tk.BooleanVar(
            value=self.prompt_system.config['responses']['enable_guided_questions'])
        ttk.Checkbutton(analysis_frame, text="Enable guided questions", 
                       variable=self.enable_questions_var).pack(anchor=tk.W)
        
        # Max suggestions
        suggestions_frame = ttk.Frame(analysis_frame)
        suggestions_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(suggestions_frame, text="Max Suggestions:").pack(side=tk.LEFT)
        self.max_suggestions_var = tk.IntVar(
            value=self.prompt_system.config['responses']['max_suggestions'])
        suggestions_spin = ttk.Spinbox(suggestions_frame, from_=1, to=10, 
                                     textvariable=self.max_suggestions_var, width=10)
        suggestions_spin.pack(side=tk.LEFT, padx=5)
        
        # Buttons
        button_frame = ttk.Frame(config_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=10)
        
        save_btn = ttk.Button(button_frame, text="Save Configuration", 
                            command=self.save_config)
        save_btn.pack(side=tk.LEFT)
        
        reset_btn = ttk.Button(button_frame, text="Reset to Defaults", 
                             command=self.reset_config)
        reset_btn.pack(side=tk.LEFT, padx=5)
        
        test_btn = ttk.Button(button_frame, text="Test Connection", 
                            command=self.test_ollama_connection)
        test_btn.pack(side=tk.RIGHT)
        
        # Stats frame
        stats_frame = ttk.LabelFrame(config_frame, text="Session Statistics", padding=5)
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.stats_text = scrolledtext.ScrolledText(stats_frame, height=6, wrap=tk.WORD, 
                                                   state=tk.DISABLED)
        self.stats_text.pack(fill=tk.BOTH, expand=True)
        
        # Update stats every 5 seconds
        self.update_stats()
        
    def process_ocr_text(self, text: str, metadata: Dict = None):
        """Process OCR text input and trigger analysis"""
        if not text.strip():
            return
            
        self.logger.info(f"Processing OCR text: {text[:50]}...")
        
        # Update current text display
        self.current_text.config(state=tk.NORMAL)
        self.current_text.delete(1.0, tk.END)
        self.current_text.insert(1.0, text)
        self.current_text.config(state=tk.DISABLED)
        
        # Add to history
        self.session_data['text_history'].append(text)
        if len(self.session_data['text_history']) > 20:
            self.session_data['text_history'] = self.session_data['text_history'][-20:]
            
        # Trigger analysis if auto-analyze is enabled
        if self.auto_analyze_var.get() and not self.is_processing:
            self.analyze_text(text)
            
    def analyze_text(self, text: str):
        """Analyze text with Ollama"""
        if self.is_processing:
            return
            
        self.is_processing = True
        self.status_var.set("Analyzing...")
        
        # Start analysis in background thread
        if self.processing_thread and self.processing_thread.is_alive():
            return
            
        self.processing_thread = threading.Thread(
            target=self._analyze_text_background, 
            args=(text,), 
            daemon=True
        )
        self.processing_thread.start()
        
    def _analyze_text_background(self, text: str):
        """Background analysis thread"""
        try:
            # Calculate session stats
            session_stats = {
                'session_duration': (time.time() - self.session_data['start_time']) / 60,
                'total_queries': self.session_data['total_queries'],
                'frames_per_minute': len(self.session_data['text_history']) / 
                                   max((time.time() - self.session_data['start_time']) / 60, 1)
            }
            
            # Perform analysis
            result = self.prompt_system.analyze_content(
                text, 
                self.session_data['text_history'], 
                session_stats
            )
            
            # Update GUI in main thread
            self.root.after(0, self._update_analysis_results, result)
            
            self.session_data['total_queries'] += 1
            if result.analysis_type == "ai_generated":
                self.session_data['successful_analyses'] += 1
                
        except Exception as e:
            self.logger.error(f"Analysis error: {e}")
            self.root.after(0, self._show_analysis_error, str(e))
        finally:
            self.is_processing = False
            self.root.after(0, lambda: self.status_var.set("Ready"))
            
    def _update_analysis_results(self, result: AnalysisResponse):
        """Update GUI with analysis results"""
        # Update activity display
        if result.context_tags:
            self.activity_var.set(result.context_tags[0].title())
            
        # Update main insight
        self.insight_text.config(state=tk.NORMAL)
        self.insight_text.delete(1.0, tk.END)
        self.insight_text.insert(1.0, result.main_insight)
        self.insight_text.config(state=tk.DISABLED)
        
        # Update suggestions
        self.suggestions_listbox.delete(0, tk.END)
        for i, suggestion in enumerate(result.suggestions, 1):
            self.suggestions_listbox.insert(tk.END, f"{i}. {suggestion}")
            
        # Update questions
        self.questions_listbox.delete(0, tk.END)
        for i, question in enumerate(result.questions, 1):
            self.questions_listbox.insert(tk.END, f"{i}. {question}")
            
        # Update follow-up prompts
        self.followup_listbox.delete(0, tk.END)
        for i, prompt in enumerate(result.follow_up_prompts, 1):
            self.followup_listbox.insert(tk.END, f"{i}. {prompt}")
            
        # Add to history
        self._add_to_history(result)
        
    def _add_to_history(self, result: AnalysisResponse):
        """Add analysis result to history"""
        timestamp = datetime.fromtimestamp(result.timestamp).strftime("%H:%M:%S")
        activity = result.context_tags[0] if result.context_tags else "unknown"
        confidence = f"{result.confidence:.1%}"
        
        item = self.history_tree.insert("", 0, values=(timestamp, activity, confidence, result.analysis_type))
        
        # Store full result data
        self.history_tree.set(item, "data", json.dumps(asdict(result)))
        
        # Auto-scroll to top
        self.history_tree.selection_set(item)
        self.history_tree.focus(item)
        
    def _show_analysis_error(self, error: str):
        """Show analysis error"""
        messagebox.showerror("Analysis Error", f"Failed to analyze text:\n{error}")
        
    def manual_analyze(self):
        """Manually trigger analysis"""
        text = self.current_text.get(1.0, tk.END).strip()
        if text:
            self.analyze_text(text)
        else:
            messagebox.showwarning("No Text", "No text available for analysis")
            
    def clear_history(self):
        """Clear analysis history"""
        if messagebox.askyesno("Clear History", "Are you sure you want to clear the analysis history?"):
            self.session_data['text_history'].clear()
            self.prompt_system.response_history.clear()
            self.history_tree.delete(*self.history_tree.get_children())
            self.history_details.config(state=tk.NORMAL)
            self.history_details.delete(1.0, tk.END)
            self.history_details.config(state=tk.DISABLED)
            
    def filter_history(self, event=None):
        """Filter history by activity type"""
        filter_value = self.filter_var.get()
        
        # Clear current items
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
            
        # Re-add filtered items
        for result in self.prompt_system.response_history:
            activity = result.context_tags[0] if result.context_tags else "general"
            
            if filter_value == "all" or activity == filter_value:
                timestamp = datetime.fromtimestamp(result.timestamp).strftime("%H:%M:%S")
                confidence = f"{result.confidence:.1%}"
                
                item = self.history_tree.insert("", 0, values=(timestamp, activity, confidence, result.analysis_type))
                self.history_tree.set(item, "data", json.dumps(asdict(result)))
                
    def on_history_select(self, event):
        """Handle history item selection"""
        selection = self.history_tree.selection()
        if not selection:
            return
            
        item = selection[0]
        result_data = self.history_tree.set(item, "data")
        
        if result_data:
            result = json.loads(result_data)
            
            # Display details
            details = f"Analysis Type: {result['analysis_type']}\n"
            details += f"Confidence: {result['confidence']:.1%}\n"
            details += f"Context Tags: {', '.join(result['context_tags'])}\n"
            details += f"Timestamp: {datetime.fromtimestamp(result['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            details += f"Main Insight:\n{result['main_insight']}\n\n"
            
            if result['suggestions']:
                details += "Suggestions:\n"
                for i, suggestion in enumerate(result['suggestions'], 1):
                    details += f"{i}. {suggestion}\n"
                details += "\n"
                
            if result['questions']:
                details += "Questions:\n"
                for i, question in enumerate(result['questions'], 1):
                    details += f"{i}. {question}\n"
                details += "\n"
                
            if result['follow_up_prompts']:
                details += "Follow-up Prompts:\n"
                for i, prompt in enumerate(result['follow_up_prompts'], 1):
                    details += f"{i}. {prompt}\n"
                    
            self.history_details.config(state=tk.NORMAL)
            self.history_details.delete(1.0, tk.END)
            self.history_details.insert(1.0, details)
            self.history_details.config(state=tk.DISABLED)
            
    def save_config(self):
        """Save configuration changes"""
        # Update prompt system config
        self.prompt_system.config['ollama']['base_url'] = self.base_url_var.get()
        self.prompt_system.config['ollama']['model'] = self.model_var.get()
        self.prompt_system.config['ollama']['temperature'] = self.temperature_var.get()
        
        self.prompt_system.config['responses']['enable_premade_responses'] = self.enable_premade_var.get()
        self.prompt_system.config['responses']['enable_guided_questions'] = self.enable_questions_var.get()
        self.prompt_system.config['responses']['max_suggestions'] = self.max_suggestions_var.get()
        
        # Save to file
        self.prompt_system.save_config()
        
        messagebox.showinfo("Configuration", "Configuration saved successfully!")
        
    def reset_config(self):
        """Reset configuration to defaults"""
        if messagebox.askyesno("Reset Configuration", "Reset all settings to defaults?"):
            # Reinitialize with defaults
            self.prompt_system = OllamaPromptSystem()
            
            # Update GUI
            self.base_url_var.set(self.prompt_system.config['ollama']['base_url'])
            self.model_var.set(self.prompt_system.config['ollama']['model'])
            self.temperature_var.set(self.prompt_system.config['ollama']['temperature'])
            self.enable_premade_var.set(self.prompt_system.config['responses']['enable_premade_responses'])
            self.enable_questions_var.set(self.prompt_system.config['responses']['enable_guided_questions'])
            self.max_suggestions_var.set(self.prompt_system.config['responses']['max_suggestions'])
            
            messagebox.showinfo("Configuration", "Configuration reset to defaults!")
            
    def test_ollama_connection(self):
        """Test connection to Ollama"""
        self.status_var.set("Testing connection...")
        
        def test_connection():
            try:
                test_response = self.prompt_system.query_ollama("Test connection - respond with 'OK'")
                if test_response:
                    self.root.after(0, lambda: messagebox.showinfo("Connection Test", 
                                                                  "Connection successful!"))
                else:
                    self.root.after(0, lambda: messagebox.showerror("Connection Test", 
                                                                   "Connection failed!"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Connection Test", 
                                                               f"Connection error: {e}"))
            finally:
                self.root.after(0, lambda: self.status_var.set("Ready"))
                
        threading.Thread(target=test_connection, daemon=True).start()
        
    def update_stats(self):
        """Update session statistics"""
        try:
            if not self.root or not self.root.winfo_exists():
                return
                
            session_duration = (time.time() - self.session_data['start_time']) / 60
            
            stats = f"Session Duration: {session_duration:.1f} minutes\n"
            stats += f"Total Queries: {self.session_data['total_queries']}\n"
            stats += f"Successful Analyses: {self.session_data['successful_analyses']}\n"
            stats += f"Text History Size: {len(self.session_data['text_history'])}\n"
            
            if self.session_data['total_queries'] > 0:
                success_rate = (self.session_data['successful_analyses'] / self.session_data['total_queries']) * 100
                stats += f"Success Rate: {success_rate:.1f}%\n"
                
            # Get summary from prompt system
            summary = self.prompt_system.get_analysis_summary()
            if "message" not in summary:
                stats += f"\nAnalysis Summary:\n"
                stats += f"Recent Analyses: {summary.get('recent_analyses', 0)}\n"
                stats += f"Average Confidence: {summary.get('average_confidence', 0):.1%}\n"
                
                top_activities = summary.get('top_activities', [])
                if top_activities:
                    stats += f"Top Activities: {', '.join([f'{act[0]}({act[1]})' for act in top_activities[:3]])}\n"
                    
            if hasattr(self, 'stats_text') and self.stats_text.winfo_exists():
                self.stats_text.config(state=tk.NORMAL)
                self.stats_text.delete(1.0, tk.END)
                self.stats_text.insert(1.0, stats)
                self.stats_text.config(state=tk.DISABLED)
            
            # Schedule next update only if window still exists
            if self.root and self.root.winfo_exists():
                self.root.after(5000, self.update_stats)
                
        except tk.TclError:
            # Window has been destroyed, stop updating
            return
        except Exception as e:
            print(f"Error updating stats: {e}")
        
    def export_history(self):
        """Export analysis history to JSON"""
        from tkinter import filedialog
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                export_data = {
                    'session_data': self.session_data,
                    'analysis_history': [asdict(result) for result in self.prompt_system.response_history],
                    'export_timestamp': time.time()
                }
                
                with open(filename, 'w') as f:
                    json.dump(export_data, f, indent=2)
                    
                messagebox.showinfo("Export", f"History exported to {filename}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export history: {e}")
                
    def on_closing(self):
        """Handle application closing"""
        try:
            self.logger.info("Ollama Interaction Interface shutting down")
            
            # Stop any processing threads
            self.is_processing = False
            
            # Destroy window safely
            if self.root and self.root.winfo_exists():
                self.root.destroy()
                
        except (tk.TclError, AttributeError) as e:
            print(f"Window cleanup completed: {e}")
        except Exception as e:
            print(f"Error during shutdown: {e}")
    
    def run(self):
        """Start the GUI application"""
        self.logger.info("Starting Ollama Interaction Interface")
        
        # Setup close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.root.mainloop()


def create_bridge_integration():
    """Create a bridge function for OCR integration"""
    interface = None
    
    def ocr_callback(text: str, metadata: Dict = None):
        """Callback function for OCR bridge"""
        nonlocal interface
        if interface:
            interface.process_ocr_text(text, metadata)
    
    def start_interface():
        """Start the interface"""
        nonlocal interface
        interface = OllamaInteractionInterface(ocr_callback)
        interface.run()
        
    return start_interface, ocr_callback


def main():
    """Test the interface standalone"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Ollama Interaction Interface")
    parser.add_argument("--test", action="store_true", help="Run with test data")
    
    args = parser.parse_args()
    
    interface = OllamaInteractionInterface()
    
    if args.test:
        # Add some test data
        test_texts = [
            "def calculate_fibonacci(n): return n if n <= 1 else calculate_fibonacci(n-1) + calculate_fibonacci(n-2)",
            "Research shows that machine learning algorithms perform better with larger datasets",
            "Welcome to our presentation on AI-assisted coding tools",
            "sudo apt install python3-pip && pip install ollama"
        ]
        
        # Process test texts with delay
        def add_test_data():
            for i, text in enumerate(test_texts):
                interface.root.after(i * 3000, lambda t=text: interface.process_ocr_text(t))
                
        interface.root.after(1000, add_test_data)
        
    interface.run()


if __name__ == "__main__":
    main()