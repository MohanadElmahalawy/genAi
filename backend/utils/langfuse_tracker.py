"""
LangFuse Observability Integration - Simplified
"""

import os
from dotenv import load_dotenv

load_dotenv()

try:
    from langfuse import Langfuse
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    print("Warning: Langfuse not installed. Install with: pip install langfuse")

class LangFuseTracker:
    def __init__(self):
        self.enabled = False
        self.langfuse = None
        self.current_trace_id = None
        
        if not LANGFUSE_AVAILABLE:
            print("LangFuse tracking disabled - package not installed")
            return
        
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        
        if not public_key or not secret_key:
            print("LangFuse tracking disabled - API keys not found in .env")
            return
        
        try:
            self.langfuse = Langfuse(
                public_key=public_key,
                secret_key=secret_key,
                host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
            )
            self.enabled = True
            print("LangFuse tracking enabled")
        except Exception as e:
            print(f"LangFuse initialization failed: {e}")
    
    def start_trace(self, name: str, user_id: str = "default"):
        """Start a new trace for a workflow"""
        if not self.enabled:
            return None
        
        try:
            self.current_trace_id = f"{name}_{user_id}_{int(os.times().elapsed * 1000)}"
            return self.current_trace_id
        except Exception as e:
            print(f"Failed to start trace: {e}")
            return None
    
    def start_span(self, name: str, input_data: dict = None):
        """Start a span within current trace"""
        # Simplified - just log it
        if self.enabled:
            print(f"[LangFuse] Span: {name}")
        return None
    
    def end_span(self, output_data: dict = None, metadata: dict = None):
        """End current span"""
        pass
    
    def log_generation(self, name: str, prompt: str, completion: str, 
                       model: str, tokens: int, time: float):
        """Log an LLM generation"""
        if not self.enabled or not self.langfuse:
            return
        
        try:
            self.langfuse.generation(
                name=name,
                model=model,
                input=prompt[:500],  # Truncate for safety
                output=completion[:500],
                metadata={
                    "tokens": tokens,
                    "response_time": time,
                    "trace_id": self.current_trace_id
                }
            )
        except Exception as e:
            print(f"Failed to log generation: {e}")
    
    def end_trace(self, output_data: dict = None):
        """End current trace"""
        if self.enabled:
            print(f"[LangFuse] Trace ended: {self.current_trace_id}")
        self.current_trace_id = None
    
    def flush(self):
        """Flush all pending data"""
        if self.enabled and self.langfuse:
            try:
                self.langfuse.flush()
            except Exception as e:
                print(f"Failed to flush LangFuse: {e}")