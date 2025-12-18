"""
FastAPI Backend for Testing Agent
Main entry point with WebSocket communication
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
import json
from datetime import datetime

from agent.explorer import PageExplorer
from agent.designer import TestDesigner
from agent.generator import CodeGenerator
from agent.verifier import TestVerifier
from agent.llm_client import LLMClient
from utils.browser import BrowserManager
from utils.metrics import MetricsTracker

app = FastAPI(title="Testing Agent API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state management
class AgentState:
    def __init__(self):
        self.browser_manager = None
        self.llm_client = LLMClient()
        self.explorer = None
        self.designer = None
        self.generator = None
        self.verifier = None
        self.metrics = MetricsTracker()
        self.current_phase = None
        self.page_knowledge = None
        self.test_cases = None
        self.generated_code = None
        
    def reset(self):
        """Reset agent to clean slate"""
        self.current_phase = None
        self.page_knowledge = None
        self.test_cases = None
        self.generated_code = None
        self.metrics.reset()
        if self.browser_manager:
            asyncio.create_task(self.browser_manager.close())
            self.browser_manager = None

agent_state = AgentState()

@app.get("/")
async def root():
    return {"message": "Testing Agent API is running"}

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "phase": agent_state.current_phase,
        "metrics": agent_state.metrics.get_summary()
    }

@app.post("/reset")
async def reset_agent():
    """Reset the agent to initial state"""
    agent_state.reset()
    return {"message": "Agent reset successfully"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connected")
    
    try:
        while True:
            # Receive message from frontend
            data = await websocket.receive_text()
            message = json.loads(data)
            
            command = message.get("command")
            payload = message.get("payload", {})
            
            # Route to appropriate handler
            if command == "explore":
                await handle_explore(websocket, payload)
            elif command == "design":
                await handle_design(websocket, payload)
            elif command == "generate":
                await handle_generate(websocket, payload)
            elif command == "verify":
                await handle_verify(websocket, payload)
            elif command == "chat":
                await handle_chat(websocket, payload)
            elif command == "reset":
                agent_state.reset()
                await websocket.send_json({
                    "type": "info",
                    "message": "Agent reset successfully"
                })
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown command: {command}"
                })
                
    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })

async def handle_explore(websocket: WebSocket, payload: dict):
    """Phase 1: Explore the page"""
    url = payload.get("url")
    if not url:
        await websocket.send_json({"type": "error", "message": "URL is required"})
        return
    
    await websocket.send_json({
        "type": "phase_start",
        "phase": "exploration",
        "message": f"Starting exploration of {url}..."
    })
    
    try:
        # Initialize browser if needed
        if not agent_state.browser_manager:
            agent_state.browser_manager = BrowserManager()
            await agent_state.browser_manager.launch(headless=False)
        
        # Initialize explorer
        agent_state.explorer = PageExplorer(
            agent_state.llm_client,
            agent_state.browser_manager,
            agent_state.metrics
        )
        
        # Perform exploration
        agent_state.current_phase = "exploration"
        page_knowledge = await agent_state.explorer.explore(url, websocket)
        agent_state.page_knowledge = page_knowledge
        
        # Send completion
        await websocket.send_json({
            "type": "phase_complete",
            "phase": "exploration",
            "data": page_knowledge,
            "metrics": agent_state.metrics.get_current()
        })
        
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "phase": "exploration",
            "message": str(e)
        })

async def handle_design(websocket: WebSocket, payload: dict):
    """Phase 2: Design test cases"""
    if not agent_state.page_knowledge:
        await websocket.send_json({
            "type": "error",
            "message": "Must explore page first"
        })
        return
    
    await websocket.send_json({
        "type": "phase_start",
        "phase": "design",
        "message": "Designing test cases..."
    })
    
    try:
        agent_state.designer = TestDesigner(
            agent_state.llm_client,
            agent_state.metrics
        )
        
        agent_state.current_phase = "design"
        test_cases = await agent_state.designer.design(
            agent_state.page_knowledge,
            websocket
        )
        agent_state.test_cases = test_cases
        
        await websocket.send_json({
            "type": "phase_complete",
            "phase": "design",
            "data": test_cases,
            "metrics": agent_state.metrics.get_current()
        })
        
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "phase": "design",
            "message": str(e)
        })

async def handle_generate(websocket: WebSocket, payload: dict):
    """Phase 3: Generate test code"""
    if not agent_state.test_cases:
        await websocket.send_json({
            "type": "error",
            "message": "Must design test cases first"
        })
        return
    
    await websocket.send_json({
        "type": "phase_start",
        "phase": "generation",
        "message": "Generating test code..."
    })
    
    try:
        agent_state.generator = CodeGenerator(
            agent_state.llm_client,
            agent_state.metrics
        )
        
        agent_state.current_phase = "generation"
        code = await agent_state.generator.generate(
            agent_state.page_knowledge,
            agent_state.test_cases,
            websocket
        )
        agent_state.generated_code = code
        
        await websocket.send_json({
            "type": "phase_complete",
            "phase": "generation",
            "data": {"code": code},
            "metrics": agent_state.metrics.get_current()
        })
        
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "phase": "generation",
            "message": str(e)
        })

async def handle_verify(websocket: WebSocket, payload: dict):
    """Phase 4: Verify tests"""
    if not agent_state.generated_code:
        await websocket.send_json({
            "type": "error",
            "message": "Must generate code first"
        })
        return
    
    await websocket.send_json({
        "type": "phase_start",
        "phase": "verification",
        "message": "Verifying tests..."
    })
    
    try:
        agent_state.verifier = TestVerifier(
            agent_state.browser_manager,
            agent_state.metrics
        )
        
        agent_state.current_phase = "verification"
        results = await agent_state.verifier.verify(
            agent_state.generated_code,
            websocket
        )
        
        await websocket.send_json({
            "type": "phase_complete",
            "phase": "verification",
            "data": results,
            "metrics": agent_state.metrics.get_current()
        })
        
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "phase": "verification",
            "message": str(e)
        })

async def handle_chat(websocket: WebSocket, payload: dict):
    """Handle general chat interactions"""
    message = payload.get("message", "")
    
    # Simple chat response
    await websocket.send_json({
        "type": "chat_response",
        "message": f"Received: {message}. How can I help you test your application?"
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")