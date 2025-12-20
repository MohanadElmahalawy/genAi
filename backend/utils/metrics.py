"""
Metrics Tracker
Tracks response times and token usage
"""

import time
from datetime import datetime

class MetricsTracker:
    def __init__(self):
        self.iterations = []
        self.start_time = time.time()
    
    def add_iteration(self, data: dict):
        """Add iteration metrics"""
        self.iterations.append({
            **data,
            "timestamp": time.time()
        })
    
    def get_current(self) -> dict:
        """Get current metrics for latest phase"""
        if not self.iterations:
            return self._empty_metrics()
        
        # Get latest phase
        latest_phase = self.iterations[-1]["phase"]
        phase_iterations = [
            it for it in self.iterations 
            if it["phase"] == latest_phase
        ]
        
        total_tokens = sum(it["tokens"] for it in phase_iterations)
        total_time = sum(it["time"] for it in phase_iterations)
        avg_time = total_time / len(phase_iterations) if phase_iterations else 0
        
        return {
            "phase": latest_phase,
            "iterations": len(phase_iterations),
            "total_tokens": total_tokens,
            "total_time": round(total_time, 2),
            "avg_response_time": round(avg_time, 2),
            "tokens_per_iteration": round(total_tokens / len(phase_iterations), 0) if phase_iterations else 0
        }

    def get_phase(self, phase: str) -> dict:
        """Get aggregated metrics for a specific phase"""
        if not self.iterations:
            return self._empty_metrics()

        phase_iterations = [it for it in self.iterations if it.get("phase") == phase]
        if not phase_iterations:
            return self._empty_metrics()

        total_tokens = sum(it.get("tokens", 0) for it in phase_iterations)
        total_time = sum(it.get("time", 0) for it in phase_iterations)
        avg_time = total_time / len(phase_iterations) if phase_iterations else 0

        return {
            "phase": phase,
            "iterations": len(phase_iterations),
            "total_tokens": total_tokens,
            "total_time": round(total_time, 2),
            "avg_response_time": round(avg_time, 2),
            "tokens_per_iteration": round(total_tokens / len(phase_iterations), 0) if phase_iterations else 0
        }
    
    def get_summary(self) -> dict:
        """Get summary of all metrics"""
        if not self.iterations:
            return self._empty_metrics()
        
        phases = {}
        for it in self.iterations:
            phase = it["phase"]
            if phase not in phases:
                phases[phase] = {
                    "iterations": 0,
                    "total_tokens": 0,
                    "total_time": 0
                }
            
            phases[phase]["iterations"] += 1
            phases[phase]["total_tokens"] += it["tokens"]
            phases[phase]["total_time"] += it["time"]
        
        # Calculate averages
        for phase in phases:
            data = phases[phase]
            data["avg_response_time"] = round(
                data["total_time"] / data["iterations"], 2
            ) if data["iterations"] > 0 else 0
            data["total_time"] = round(data["total_time"], 2)
        
        return {
            "total_iterations": len(self.iterations),
            "total_tokens": sum(it["tokens"] for it in self.iterations),
            "total_time": round(time.time() - self.start_time, 2),
            "phases": phases
        }
    
    def reset(self):
        """Reset all metrics"""
        self.iterations = []
        self.start_time = time.time()
    
    def get_timestamp(self) -> str:
        """Get current timestamp"""
        return datetime.now().isoformat()
    
    def _empty_metrics(self) -> dict:
        return {
            "phase": None,
            "iterations": 0,
            "total_tokens": 0,
            "total_time": 0,
            "avg_response_time": 0,
            "tokens_per_iteration": 0
        }