"""
Phase 2: Test Designer
Creates test cases based on page knowledge
"""

import json

class TestDesigner:
    def __init__(self, llm_client, metrics):
        self.llm = llm_client
        self.metrics = metrics
    
    async def design(self, page_knowledge: dict, websocket) -> dict:
        """
        Design comprehensive test cases
        """
        await websocket.send_json({
            "type": "progress",
            "message": "Analyzing page for test scenarios..."
        })
        
        # Generate test cases using LLM
        test_cases = await self._generate_test_cases(page_knowledge)
        
        self.metrics.add_iteration({
            "phase": "design",
            "tokens": test_cases["tokens"],
            "time": test_cases["time"]
        })
        
        await websocket.send_json({
            "type": "progress",
            "message": f"Generated {len(test_cases['json']['test_cases']) if test_cases['json'] else 0} test cases"
        })
        
        return {
            "test_cases": test_cases["json"]["test_cases"] if test_cases["json"] else [],
            "coverage": test_cases["json"]["coverage"] if test_cases["json"] else {},
            "timestamp": self.metrics.get_timestamp()
        }
    
    async def _generate_test_cases(self, knowledge: dict) -> dict:
        """Use LLM to generate test cases"""
        
        prompt = f"""
Based on this page knowledge, design comprehensive test cases.

URL: {knowledge['url']}
Purpose: {knowledge['structure'].get('purpose', 'Unknown')}

Available Elements:
{json.dumps(knowledge['elements'][:15], indent=2)}

Possible Interactions:
{json.dumps(knowledge['interactions'][:10], indent=2)}

Create a JSON response with:

1. "test_cases": Array of test cases, each with:
   - id: unique test ID (e.g., "TC001")
   - name: descriptive test name
   - priority: high/medium/low
   - steps: array of steps with:
     * action: what to do
     * target: element to interact with
     * data: test data if needed
     * expected: expected result
   - category: UI/Functional/Integration/Negative

2. "coverage": Test coverage analysis:
   - elements_covered: count of elements tested
   - interaction_types: types of interactions covered
   - edge_cases: list of edge cases identified

Focus on:
- Happy path scenarios (basic functionality)
- Edge cases (empty inputs, invalid data)
- User workflows (multi-step processes)
- Negative testing (error handling)

Ensure test cases are specific, executable, and provide good coverage.
"""
        
        return await self.llm.generate_json(prompt)
    
    async def refine(self, current_cases: dict, feedback: str, websocket) -> dict:
        """Refine test cases based on user feedback"""
        
        await websocket.send_json({
            "type": "progress",
            "message": "Refining test cases based on your feedback..."
        })
        
        prompt = f"""
Current test cases:
{json.dumps(current_cases, indent=2)}

User feedback: {feedback}

Update the test cases to address the feedback. Return the same JSON structure with improvements.
"""
        
        refined = await self.llm.generate_json(prompt)
        
        self.metrics.add_iteration({
            "phase": "design_refinement",
            "tokens": refined["tokens"],
            "time": refined["time"]
        })
        
        return {
            "test_cases": refined["json"]["test_cases"] if refined["json"] else current_cases["test_cases"],
            "coverage": refined["json"]["coverage"] if refined["json"] else current_cases["coverage"],
            "timestamp": self.metrics.get_timestamp()
        }