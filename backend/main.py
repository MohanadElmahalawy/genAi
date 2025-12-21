"""
FastAPI Backend for Testing Agent
Main entry point with WebSocket communication
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
import json
import pathlib
from datetime import datetime

from agent.explorer import PageExplorer
from agent.designer import TestDesigner
from agent.generator import CodeGenerator
from agent.verifier import TestVerifier
from agent.llm_client import LLMClient, NoTokensError
from utils.browser import BrowserManager
from utils.metrics import MetricsTracker
from utils.langfuse_tracker import LangFuseTracker

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
        self.langfuse = LangFuseTracker()
        self.llm_client = LLMClient(langfuse_tracker=self.langfuse)
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
        # Flush LangFuse data
        self.langfuse.flush()
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


@app.get("/reports/verification")
async def get_verification_report():
    """Return latest verification report JSON if present."""
    report_path = pathlib.Path(__file__).resolve().parents[0] / "verification_with_screenshots.json"
    if report_path.exists():
        try:
            text = report_path.read_text(encoding="utf-8")
            return JSONResponse(content=json.loads(text))
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})
    return JSONResponse(status_code=404, content={"error": "report not found"})

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
            elif command == "refine":
                await handle_refine(websocket, payload)
            elif command == "refine_code":
                await handle_refine_code(websocket, payload)
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
        # If token exhaustion occurred, send a clear message
        if isinstance(e, NoTokensError):
            await websocket.send_json({
                "type": "error",
                "message": "No more tokens available from LLM provider. Please refill quota or reset the agent."
            })
        else:
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
    
    # Start LangFuse trace
    agent_state.langfuse.start_trace("page_exploration", user_id="user_session")
    
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
        
        # End LangFuse trace
        agent_state.langfuse.end_trace(output_data={
            "elements_found": len(page_knowledge.get("elements", []))
        })
        
        # Send completion
        await websocket.send_json({
            "type": "phase_complete",
            "phase": "exploration",
            "data": page_knowledge,
            "metrics": agent_state.metrics.get_phase("exploration")
        })
        
    except NoTokensError:
        agent_state.langfuse.end_trace(output_data={"error": "token_exhaustion"})
        await websocket.send_json({
            "type": "error",
            "phase": "exploration",
            "message": "No more tokens available from LLM provider. Please refill quota or reset the agent."
        })
    except Exception as e:
        agent_state.langfuse.end_trace(output_data={"error": str(e)})
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
    
    # Start LangFuse trace
    agent_state.langfuse.start_trace("test_design")
    
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
        
        # End LangFuse trace
        agent_state.langfuse.end_trace(output_data={
            "test_cases_count": len(test_cases.get("test_cases", []))
        })
        
        await websocket.send_json({
            "type": "phase_complete",
            "phase": "design",
            "data": test_cases,
            "metrics": agent_state.metrics.get_phase("design")
        })
        
    except Exception as e:
        agent_state.langfuse.end_trace(output_data={"error": str(e)})
        if isinstance(e, NoTokensError):
            await websocket.send_json({
                "type": "error",
                "phase": "design",
                "message": "No more tokens available from LLM provider. Please refill quota or reset the agent."
            })
        else:
            await websocket.send_json({
                "type": "error",
                "phase": "design",
                "message": str(e)
            })


async def handle_refine(websocket: WebSocket, payload: dict):
    """Refine existing test cases based on user feedback"""
    if not agent_state.test_cases:
        await websocket.send_json({"type": "error", "message": "No existing test cases to refine"})
        return

    feedback = payload.get("feedback", "")
    
    # Start LangFuse trace
    agent_state.langfuse.start_trace("test_design_refinement")

    await websocket.send_json({
        "type": "phase_start",
        "phase": "design_refinement",
        "message": "Refining test cases based on feedback..."
    })

    try:
        # Ensure designer exists
        if not agent_state.designer:
            agent_state.designer = TestDesigner(agent_state.llm_client, agent_state.metrics)

        agent_state.current_phase = "design_refinement"

        refined = await agent_state.designer.refine(agent_state.test_cases, feedback, websocket)
        # designer.refine returns dict with keys test_cases, coverage, timestamp
        agent_state.test_cases = {
            "test_cases": refined.get("test_cases", agent_state.test_cases.get("test_cases")),
            "coverage": refined.get("coverage", agent_state.test_cases.get("coverage")),
            "timestamp": refined.get("timestamp", agent_state.metrics.get_timestamp())
        }
        
        # End LangFuse trace
        agent_state.langfuse.end_trace(output_data={
            "feedback": feedback,
            "test_cases_count": len(agent_state.test_cases.get("test_cases", []))
        })

        await websocket.send_json({
            "type": "phase_complete",
            "phase": "design_refinement",
            "data": agent_state.test_cases,
            "metrics": agent_state.metrics.get_phase("design_refinement")
        })

    except Exception as e:
        agent_state.langfuse.end_trace(output_data={"error": str(e)})
        if isinstance(e, NoTokensError):
            await websocket.send_json({"type": "error", "phase": "design_refinement", "message": "No more tokens available from LLM provider. Please refill quota or reset the agent."})
        else:
            await websocket.send_json({"type": "error", "phase": "design_refinement", "message": str(e)})


async def handle_refine_code(websocket: WebSocket, payload: dict):
    """Refine generated test code based on reported issue"""
    if not agent_state.generated_code:
        await websocket.send_json({"type": "error", "message": "No generated code to refine"})
        return

    issue = payload.get("issue", "")
    
    # Start LangFuse trace
    agent_state.langfuse.start_trace("code_refinement")

    await websocket.send_json({
        "type": "phase_start",
        "phase": "generation_refinement",
        "message": "Refining generated code based on issue..."
    })

    try:
        # Ensure generator exists
        if not agent_state.generator:
            agent_state.generator = CodeGenerator(agent_state.llm_client, agent_state.metrics)

        agent_state.current_phase = "generation_refinement"

        refined_code = await agent_state.generator.refine_code(agent_state.generated_code, issue, websocket)
        agent_state.generated_code = refined_code
        
        # End LangFuse trace
        agent_state.langfuse.end_trace(output_data={
            "issue": issue,
            "code_length": len(refined_code)
        })

        await websocket.send_json({
            "type": "phase_complete",
            "phase": "generation_refinement",
            "data": {"code": agent_state.generated_code},
            "metrics": agent_state.metrics.get_phase("generation_refinement")
        })

    except Exception as e:
        agent_state.langfuse.end_trace(output_data={"error": str(e)})
        if isinstance(e, NoTokensError):
            await websocket.send_json({"type": "error", "phase": "generation_refinement", "message": "No more tokens available from LLM provider. Please refill quota or reset the agent."})
        else:
            await websocket.send_json({"type": "error", "phase": "generation_refinement", "message": str(e)})

async def handle_generate(websocket: WebSocket, payload: dict):
    """Phase 3: Generate test code"""
    if not agent_state.test_cases:
        await websocket.send_json({
            "type": "error",
            "message": "Must design test cases first"
        })
        return
    
    # Start LangFuse trace
    agent_state.langfuse.start_trace("code_generation")
    
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

        # Ensure verifier exists
        if not agent_state.verifier:
            agent_state.verifier = TestVerifier(agent_state.browser_manager, agent_state.metrics)

        agent_state.current_phase = "generation"

        # Generate initial code
        code = await agent_state.generator.generate(
            agent_state.page_knowledge,
            agent_state.test_cases,
            websocket
        )

        # Verify and refine automatically; returns dict {code, verification}
        vr = await agent_state.generator.verify_and_refine(code, agent_state.verifier, websocket)

        final_code = vr.get("code") if isinstance(vr, dict) else code
        verification = vr.get("verification") if isinstance(vr, dict) else None

        agent_state.generated_code = final_code
        
        # End LangFuse trace
        agent_state.langfuse.end_trace(output_data={
            "code_length": len(final_code),
            "verification": verification
        })

        await websocket.send_json({
            "type": "phase_complete",
            "phase": "generation",
            "data": {"code": final_code, "verification": verification},
            "metrics": agent_state.metrics.get_phase("generation")
        })
        
    except Exception as e:
        agent_state.langfuse.end_trace(output_data={"error": str(e)})
        if isinstance(e, NoTokensError):
            await websocket.send_json({
                "type": "error",
                "phase": "generation",
                "message": "No more tokens available from LLM provider. Please refill quota or reset the agent."
            })
        else:
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
    
    # Start LangFuse trace
    agent_state.langfuse.start_trace("test_verification")
    
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
        
        # End LangFuse trace
        agent_state.langfuse.end_trace(output_data={
            "passed": results.get("passed", 0),
            "failed": results.get("failed", 0),
            "success": results.get("success", False)
        })
        
        await websocket.send_json({
            "type": "phase_complete",
            "phase": "verification",
            "data": results,
            "metrics": agent_state.metrics.get_phase("verification")
        })
        
    except Exception as e:
        agent_state.langfuse.end_trace(output_data={"error": str(e)})
        if isinstance(e, NoTokensError):
            await websocket.send_json({
                "type": "error",
                "phase": "verification",
                "message": "No more tokens available from LLM provider. Please refill quota or reset the agent."
            })
        else:
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