#!/usr/bin/env python3
"""
Ollama Intelligent Prompt System for OCR Screenshare
Context-aware prompts, premade responses, and guided questions for enhanced AI analysis
"""

import json
import time
import requests
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
import re
import random


@dataclass
class PromptContext:
    """Context information for prompt generation"""
    current_text: str
    text_history: List[str]
    activity_type: str  # coding, research, presentation, etc.
    confidence_level: float
    time_context: str  # morning, afternoon, evening
    session_duration: float
    change_frequency: float
    keywords: List[str]
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class AnalysisResponse:
    """Structured response from AI analysis"""
    analysis_type: str
    confidence: float
    main_insight: str
    suggestions: List[str]
    questions: List[str]
    follow_up_prompts: List[str]
    context_tags: List[str]
    timestamp: float
    
    def to_dict(self) -> Dict:
        return asdict(self)


class OllamaPromptSystem:
    """Intelligent prompt system for enhanced OCR analysis"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = Path(config_file) if config_file else Path.cwd() / "ollama_prompts_config.json"
        self.config = self.load_config()
        self.session_context = {}
        self.response_history = []
        
        # Load prompt templates
        self.prompt_templates = self.load_prompt_templates()
        self.premade_responses = self.load_premade_responses()
        self.guided_questions = self.load_guided_questions()
        
    def load_config(self) -> Dict:
        """Load Ollama prompt system configuration"""
        default_config = {
            "ollama": {
                "base_url": "http://localhost:11434",
                "model": "llama3.2:3b",
                "timeout": 60,
                "temperature": 0.3,
                "max_tokens": 500,
                "max_retries": 3,
                "retry_delay": 2
            },
            "analysis": {
                "context_window_size": 5,
                "min_confidence_threshold": 0.6,
                "activity_detection_keywords": {
                    "coding": ["class", "function", "def", "import", "return", "if", "for", "while", "git", "commit", "python", "javascript", "html"],
                    "research": ["research", "study", "analysis", "paper", "journal", "article", "citation", "reference", "methodology"],
                    "presentation": ["slide", "presentation", "demo", "showcase", "audience", "screen share", "discord"],
                    "documentation": ["readme", "docs", "documentation", "guide", "tutorial", "manual", "wiki"],
                    "communication": ["email", "chat", "message", "discord", "slack", "teams", "meeting"],
                    "terminal": ["terminal", "command", "bash", "shell", "linux", "sudo", "apt", "install"]
                },
                "prompt_selection_strategy": "context_aware"  # random, sequential, context_aware
            },
            "responses": {
                "enable_premade_responses": True,
                "enable_guided_questions": True,
                "response_personalization": True,
                "max_suggestions": 3,
                "max_questions": 2
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
    
    def load_prompt_templates(self) -> Dict[str, Dict]:
        """Load context-aware prompt templates"""
        return {
            "coding": {
                "analysis": """You are analyzing a developer's screen during a coding session. 
Current screen content: "{current_text}"
Recent activity: {recent_activity}

Analyze the code and provide:
1. What programming task is being worked on
2. Code quality observations
3. Potential improvements or suggestions
4. Next logical steps

Be concise and focus on actionable insights.""",
                
                "debugging": """You are helping debug code shown on screen.
Code content: "{current_text}"
Context: {context}

Help identify:
1. Potential bugs or issues
2. Debugging approaches
3. Best practices being followed or missed
4. Testing suggestions

Provide specific, actionable debugging advice.""",
                
                "code_review": """Perform a code review of the displayed code:
Code: "{current_text}"
Session context: {context}

Review for:
1. Code structure and organization
2. Performance considerations  
3. Security implications
4. Maintainability

Give constructive feedback with specific examples."""
            },
            
            "research": {
                "analysis": """You are analyzing research content displayed on screen.
Content: "{current_text}"
Research context: {context}

Analyze:
1. Research methodology being used
2. Key findings or insights
3. Potential gaps or areas to explore
4. Suggestions for further investigation

Focus on academic rigor and research quality.""",
                
                "summarization": """Summarize the research content shown:
Content: "{current_text}"
Previous context: {recent_activity}

Provide:
1. Main research themes
2. Key methodologies mentioned
3. Important findings or conclusions
4. Research gaps identified

Keep summary academic and precise.""",
                
                "critique": """Critically analyze the research displayed:
Research content: "{current_text}"
Context: {context}

Evaluate:
1. Methodology strengths/weaknesses
2. Evidence quality and sources
3. Logical consistency
4. Potential biases or limitations

Provide balanced, scholarly critique."""
            },
            
            "presentation": {
                "audience_engagement": """You're helping improve a presentation being shared.
Current slide/content: "{current_text}"
Presentation context: {context}

Suggest improvements for:
1. Audience engagement
2. Content clarity
3. Visual presentation
4. Flow and structure

Focus on making content more compelling.""",
                
                "technical_explanation": """Help explain technical content to audience:
Technical content: "{current_text}"
Context: {context}

Provide:
1. Simplified explanations for complex concepts
2. Analogies or examples
3. Key takeaways for audience
4. Q&A preparation suggestions

Make technical content accessible.""",
                
                "demo_guidance": """Provide guidance for live demonstration:
Demo content: "{current_text}"
Session info: {context}

Suggest:
1. Key points to highlight
2. Potential audience questions
3. Common demo pitfalls to avoid
4. Ways to keep audience engaged

Focus on smooth demo execution."""
            },
            
            "general": {
                "context_analysis": """Analyze the current screen content and provide insights:
Content: "{current_text}"
Recent activity: {recent_activity}
Session context: {context}

Provide:
1. Activity identification
2. Progress assessment
3. Helpful suggestions
4. Relevant questions

Be helpful and context-aware.""",
                
                "productivity": """Help improve productivity based on screen activity:
Current activity: "{current_text}"
Context: {context}

Suggest:
1. Productivity improvements
2. Workflow optimizations
3. Tools or techniques
4. Time management tips

Focus on actionable productivity advice."""
            }
        }
    
    def load_premade_responses(self) -> Dict[str, List[str]]:
        """Load premade responses for common scenarios"""
        return {
            "coding_encouragement": [
                "Great progress on the code structure! The modular approach looks solid.",
                "Nice implementation! Consider adding error handling for robustness.",
                "The code organization is clean. Documentation would enhance maintainability.",
                "Good use of design patterns. Unit tests could strengthen this further.",
                "Excellent progress! The logic flow is easy to follow."
            ],
            
            "debugging_help": [
                "Try adding print statements to trace variable values at key points.",
                "Check for off-by-one errors in loop conditions and array indexing.",
                "Verify input validation and edge case handling.",
                "Use a debugger to step through the problematic section line by line.",
                "Consider rubber duck debugging - explain the code out loud."
            ],
            
            "research_insights": [
                "This methodology aligns well with established research practices.",
                "Consider expanding the literature review to include recent studies.",
                "The data collection approach looks comprehensive.",
                "Statistical significance testing would strengthen these findings.",
                "Cross-validation with additional datasets could enhance reliability."
            ],
            
            "presentation_tips": [
                "Great visual layout! Consider adding more white space for clarity.",
                "The content flow is logical. A summary slide would help retention.",
                "Engaging introduction! Interactive elements could boost audience participation.",
                "Clear technical explanation. Examples would make it more relatable.",
                "Strong conclusion! Q&A preparation will handle follow-up questions well."
            ],
            
            "productivity_boosters": [
                "Consider using keyboard shortcuts to speed up repetitive tasks.",
                "Breaking this into smaller subtasks might improve focus.",
                "A quick break could help maintain concentration levels.",
                "Documentation as you go will save time later.",
                "Version control commits at logical points preserve progress."
            ],
            
            "learning_support": [
                "You're grasping complex concepts well! Practice will build confidence.",
                "This is a challenging topic - your systematic approach is smart.",
                "Great questions! Curiosity drives effective learning.",
                "Building on fundamentals like this creates strong foundations.",
                "Hands-on practice with examples accelerates understanding."
            ]
        }
    
    def load_guided_questions(self) -> Dict[str, List[str]]:
        """Load guided questions to prompt user thinking"""
        return {
            "coding": [
                "What edge cases should this code handle?",
                "How would you test this function?",
                "Are there any performance bottlenecks here?",
                "What happens if the input is malformed?",
                "How could this code be made more maintainable?",
                "What security considerations apply here?",
                "How would you document this for other developers?"
            ],
            
            "research": [
                "What are the limitations of this methodology?",
                "How does this relate to existing literature?",
                "What additional data would strengthen this analysis?",
                "Are there alternative explanations for these results?",
                "How generalizable are these findings?",
                "What ethical considerations apply to this research?",
                "What would be the next logical research step?"
            ],
            
            "presentation": [
                "What questions might the audience ask about this?",
                "How can you make this more engaging?",
                "What's the key takeaway for your audience?",
                "Are there any confusing technical terms to explain?",
                "How does this connect to your main thesis?",
                "What examples would clarify this concept?",
                "How will you handle challenging questions?"
            ],
            
            "general": [
                "What's the most important aspect of what you're working on?",
                "What challenges are you facing with this task?",
                "How does this fit into your bigger goals?",
                "What would success look like here?",
                "What resources might be helpful?",
                "What's your next step after this?",
                "How confident are you in your current approach?"
            ]
        }
    
    def detect_activity_type(self, text: str, context_history: List[str] = None) -> str:
        """Detect the type of activity based on screen content"""
        text_lower = text.lower()
        context_text = " ".join(context_history or []).lower()
        combined_text = f"{text_lower} {context_text}"
        
        activity_scores = {}
        
        for activity, keywords in self.config['analysis']['activity_detection_keywords'].items():
            score = sum(1 for keyword in keywords if keyword in combined_text)
            # Weight current text more heavily than history
            current_score = sum(1 for keyword in keywords if keyword in text_lower) * 2
            activity_scores[activity] = score + current_score
        
        if not activity_scores or max(activity_scores.values()) == 0:
            return "general"
            
        return max(activity_scores.items(), key=lambda x: x[1])[0]
    
    def build_context(self, current_text: str, text_history: List[str], 
                     session_stats: Dict) -> PromptContext:
        """Build comprehensive context for prompt generation"""
        activity_type = self.detect_activity_type(current_text, text_history)
        
        # Extract keywords
        words = re.findall(r'\b\w+\b', current_text.lower())
        keywords = [w for w in words if len(w) > 3 and w not in 
                   ['this', 'that', 'with', 'from', 'they', 'have', 'will', 'been']][:10]
        
        # Determine time context
        hour = datetime.now().hour
        if 6 <= hour < 12:
            time_context = "morning"
        elif 12 <= hour < 18:
            time_context = "afternoon" 
        else:
            time_context = "evening"
            
        # Calculate confidence based on text quality
        confidence = min(1.0, len(current_text) / 100 * 0.8 + 0.2)
        
        # Calculate change frequency
        recent_history = text_history[-5:] if text_history else []
        unique_texts = len(set(recent_history))
        change_freq = unique_texts / len(recent_history) if recent_history else 0
        
        return PromptContext(
            current_text=current_text,
            text_history=text_history[-10:],  # Keep last 10
            activity_type=activity_type,
            confidence_level=confidence,
            time_context=time_context,
            session_duration=session_stats.get('session_duration', 0),
            change_frequency=change_freq,
            keywords=keywords
        )
    
    def select_prompt_template(self, context: PromptContext) -> str:
        """Select appropriate prompt template based on context"""
        activity_templates = self.prompt_templates.get(context.activity_type, 
                                                     self.prompt_templates['general'])
        
        # Context-aware template selection
        if context.activity_type == "coding":
            if any(word in context.keywords for word in ['error', 'bug', 'debug', 'exception']):
                return activity_templates.get('debugging', activity_templates['analysis'])
            elif any(word in context.keywords for word in ['review', 'pull', 'merge']):
                return activity_templates.get('code_review', activity_templates['analysis'])
            else:
                return activity_templates['analysis']
                
        elif context.activity_type == "research":
            if any(word in context.keywords for word in ['summary', 'conclusion', 'abstract']):
                return activity_templates.get('summarization', activity_templates['analysis'])
            elif any(word in context.keywords for word in ['critique', 'evaluation', 'assessment']):
                return activity_templates.get('critique', activity_templates['analysis'])
            else:
                return activity_templates['analysis']
                
        elif context.activity_type == "presentation":
            if any(word in context.keywords for word in ['demo', 'demonstration', 'live']):
                return activity_templates.get('demo_guidance', activity_templates['audience_engagement'])
            elif any(word in context.keywords for word in ['technical', 'complex', 'explain']):
                return activity_templates.get('technical_explanation', activity_templates['audience_engagement'])
            else:
                return activity_templates['audience_engagement']
        
        # Default to general analysis
        return self.prompt_templates['general']['context_analysis']
    
    def get_premade_response(self, context: PromptContext) -> Optional[str]:
        """Get relevant premade response if applicable"""
        if not self.config['responses']['enable_premade_responses']:
            return None
            
        # Select response category based on context
        if context.activity_type == "coding" and context.confidence_level > 0.7:
            if any(word in context.keywords for word in ['error', 'bug', 'debug']):
                responses = self.premade_responses['debugging_help']
            else:
                responses = self.premade_responses['coding_encouragement']
        elif context.activity_type == "research":
            responses = self.premade_responses['research_insights']
        elif context.activity_type == "presentation":
            responses = self.premade_responses['presentation_tips']
        elif context.change_frequency < 0.3:  # Low activity
            responses = self.premade_responses['productivity_boosters']
        else:
            responses = self.premade_responses['learning_support']
        
        return random.choice(responses) if responses else None
    
    def get_guided_questions(self, context: PromptContext) -> List[str]:
        """Get relevant guided questions based on context"""
        if not self.config['responses']['enable_guided_questions']:
            return []
            
        question_pool = self.guided_questions.get(context.activity_type, 
                                                self.guided_questions['general'])
        
        # Select relevant questions based on keywords and context
        relevant_questions = []
        
        # Filter questions based on current context
        for question in question_pool:
            question_words = set(question.lower().split())
            context_words = set(context.keywords)
            
            # Simple relevance scoring
            relevance = len(question_words.intersection(context_words))
            if relevance > 0 or len(relevant_questions) < 2:
                relevant_questions.append((question, relevance))
        
        # Sort by relevance and return top questions
        relevant_questions.sort(key=lambda x: x[1], reverse=True)
        max_questions = self.config['responses']['max_questions']
        
        return [q[0] for q in relevant_questions[:max_questions]]
    
    def format_prompt(self, template: str, context: PromptContext) -> str:
        """Format prompt template with context data"""
        recent_activity = " -> ".join(context.text_history[-3:]) if context.text_history else "No recent activity"
        
        context_info = {
            "activity_type": context.activity_type,
            "time_context": context.time_context,
            "session_duration": f"{context.session_duration:.1f} minutes",
            "confidence": f"{context.confidence_level:.1%}",
            "keywords": ", ".join(context.keywords[:5])
        }
        
        return template.format(
            current_text=context.current_text,
            recent_activity=recent_activity,
            context=context_info
        )
    
    def query_ollama(self, prompt: str) -> Optional[Dict]:
        """Send prompt to Ollama with retry logic and better error handling"""
        max_retries = self.config['ollama'].get('max_retries', 3)
        retry_delay = self.config['ollama'].get('retry_delay', 2)
        
        for attempt in range(max_retries):
            try:
                # Check if Ollama is available before making request
                health_check = requests.get(
                    f"{self.config['ollama']['base_url']}/api/version",
                    timeout=5
                )
                if health_check.status_code != 200:
                    raise requests.exceptions.ConnectionError("Ollama service not available")
                
                payload = {
                    "model": self.config['ollama']['model'],
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": self.config['ollama']['temperature'],
                        "num_predict": self.config['ollama']['max_tokens']
                    }
                }
                
                response = requests.post(
                    f"{self.config['ollama']['base_url']}/api/generate",
                    json=payload,
                    timeout=self.config['ollama']['timeout']
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    print(f"Ollama API error: {response.status_code} - {response.text}")
                    if attempt < max_retries - 1:
                        print(f"Retrying in {retry_delay} seconds... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(retry_delay)
                        continue
                    return None
                    
            except requests.exceptions.Timeout:
                print(f"Ollama request timed out (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                return None
                
            except requests.exceptions.ConnectionError as e:
                print(f"Ollama connection error: {e} (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                return None
                
            except Exception as e:
                print(f"Error querying Ollama: {e} (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                return None
                
        return None
    
    def analyze_content(self, current_text: str, text_history: List[str] = None,
                       session_stats: Dict = None) -> AnalysisResponse:
        """Comprehensive content analysis with intelligent prompting"""
        # Build context
        context = self.build_context(current_text, text_history or [], session_stats or {})
        
        # Check for premade response first
        premade_response = self.get_premade_response(context)
        if premade_response and context.confidence_level < 0.6:
            # Use premade response for low-confidence scenarios
            questions = self.get_guided_questions(context)
            return AnalysisResponse(
                analysis_type="premade",
                confidence=0.8,
                main_insight=premade_response,
                suggestions=[],
                questions=questions,
                follow_up_prompts=[],
                context_tags=[context.activity_type, context.time_context],
                timestamp=time.time()
            )
        
        # Select and format prompt template
        template = self.select_prompt_template(context)
        formatted_prompt = self.format_prompt(template, context)
        
        # Query Ollama
        ollama_response = self.query_ollama(formatted_prompt)
        
        if not ollama_response:
            # Fallback to premade response
            questions = self.get_guided_questions(context)
            fallback_response = premade_response or "Unable to analyze content at this time."
            
            return AnalysisResponse(
                analysis_type="fallback",
                confidence=0.5,
                main_insight=fallback_response,
                suggestions=[],
                questions=questions,
                follow_up_prompts=[],
                context_tags=[context.activity_type],
                timestamp=time.time()
            )
        
        # Parse Ollama response
        ai_text = ollama_response.get('response', '').strip()
        
        # Extract structured information from AI response
        suggestions = self.extract_suggestions(ai_text)
        questions = self.get_guided_questions(context)
        follow_up_prompts = self.generate_follow_up_prompts(context, ai_text)
        
        response = AnalysisResponse(
            analysis_type="ai_generated",
            confidence=context.confidence_level,
            main_insight=ai_text,
            suggestions=suggestions,
            questions=questions,
            follow_up_prompts=follow_up_prompts,
            context_tags=[context.activity_type, context.time_context] + context.keywords[:3],
            timestamp=time.time()
        )
        
        # Store response in history
        self.response_history.append(response)
        if len(self.response_history) > 50:  # Keep last 50 responses
            self.response_history = self.response_history[-50:]
        
        return response
    
    def extract_suggestions(self, ai_text: str) -> List[str]:
        """Extract actionable suggestions from AI response"""
        suggestions = []
        lines = ai_text.split('\n')
        
        for line in lines:
            line = line.strip()
            # Look for numbered suggestions or bullet points
            if (re.match(r'^\d+\.', line) or 
                line.startswith('- ') or 
                line.startswith('• ') or
                'suggest' in line.lower() or
                'recommend' in line.lower() or
                'consider' in line.lower()):
                
                # Clean up the suggestion
                suggestion = re.sub(r'^\d+\.\s*', '', line)
                suggestion = re.sub(r'^[-•]\s*', '', suggestion)
                if len(suggestion) > 10 and len(suggestion) < 200:
                    suggestions.append(suggestion)
        
        return suggestions[:self.config['responses']['max_suggestions']]
    
    def generate_follow_up_prompts(self, context: PromptContext, ai_response: str) -> List[str]:
        """Generate follow-up prompts based on context and AI response"""
        follow_ups = []
        
        # Activity-specific follow-ups
        if context.activity_type == "coding":
            follow_ups.extend([
                "How would you improve the code structure?",
                "What testing strategy would you recommend?",
                "Are there any security considerations?"
            ])
        elif context.activity_type == "research":
            follow_ups.extend([
                "What are the key limitations of this approach?",
                "How does this compare to alternative methods?",
                "What additional data would be valuable?"
            ])
        elif context.activity_type == "presentation":
            follow_ups.extend([
                "How can we make this more engaging for the audience?",
                "What questions should we prepare for?",
                "Are there better ways to visualize this?"
            ])
        
        # Context-based follow-ups
        if context.confidence_level < 0.7:
            follow_ups.append("Can you provide more details about what you're working on?")
            
        if context.change_frequency > 0.7:
            follow_ups.append("You seem to be switching between tasks - need help prioritizing?")
        
        return follow_ups[:3]  # Return top 3 follow-ups
    
    def get_analysis_summary(self) -> Dict:
        """Get summary of analysis session"""
        if not self.response_history:
            return {"message": "No analysis performed yet"}
        
        recent_responses = self.response_history[-10:]
        
        activity_counts = {}
        for response in recent_responses:
            for tag in response.context_tags:
                activity_counts[tag] = activity_counts.get(tag, 0) + 1
        
        avg_confidence = sum(r.confidence for r in recent_responses) / len(recent_responses)
        
        return {
            "total_analyses": len(self.response_history),
            "recent_analyses": len(recent_responses),
            "average_confidence": avg_confidence,
            "top_activities": sorted(activity_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            "analysis_types": [r.analysis_type for r in recent_responses]
        }


def main():
    """Test the Ollama prompt system"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Ollama Intelligent Prompt System")
    parser.add_argument("--test", action="store_true", help="Run test analysis")
    parser.add_argument("--text", help="Text to analyze")
    parser.add_argument("--config", help="Configuration file path")
    
    args = parser.parse_args()
    
    # Create prompt system
    system = OllamaPromptSystem(args.config)
    
    if args.test or args.text:
        test_text = args.text or "def calculate_fibonacci(n): return n if n <= 1 else calculate_fibonacci(n-1) + calculate_fibonacci(n-2)"
        test_history = ["Working on algorithms", "Implementing recursive functions", "Testing fibonacci implementation"]
        test_stats = {"session_duration": 15.5, "frames_per_minute": 2.3}
        
        print("🧠 Testing Ollama Prompt System")
        print("=" * 50)
        print(f"Text: {test_text[:100]}...")
        print()
        
        result = system.analyze_content(test_text, test_history, test_stats)
        
        print("📊 Analysis Result:")
        print(f"Type: {result.analysis_type}")
        print(f"Confidence: {result.confidence:.1%}")
        print(f"Context Tags: {', '.join(result.context_tags)}")
        print()
        print("🤖 AI Insight:")
        print(result.main_insight)
        print()
        
        if result.suggestions:
            print("💡 Suggestions:")
            for i, suggestion in enumerate(result.suggestions, 1):
                print(f"{i}. {suggestion}")
            print()
        
        if result.questions:
            print("❓ Guided Questions:")
            for i, question in enumerate(result.questions, 1):
                print(f"{i}. {question}")
            print()
        
        if result.follow_up_prompts:
            print("🔄 Follow-up Prompts:")
            for i, prompt in enumerate(result.follow_up_prompts, 1):
                print(f"{i}. {prompt}")
        
        print("\n📈 Session Summary:")
        summary = system.get_analysis_summary()
        for key, value in summary.items():
            print(f"{key}: {value}")
    
    else:
        print("Ollama Intelligent Prompt System initialized")
        print("Use --test to run a test analysis")
        print("Use --text 'your text' to analyze specific content")


if __name__ == "__main__":
    main()