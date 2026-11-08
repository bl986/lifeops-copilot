import time
from typing import Dict, Any, Callable

class AgentHarness:
    """A lightweight evaluation and execution harness for tracking agent lifecycle and guardrails."""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name

    def execute(self, user_message: str, agent_logic: Callable[[], str]) -> Dict[str, Any]:
        start_time = time.time()
        print(f"[Harness: {self.agent_name}] Evaluating input: '{user_message}'")
        
        try:
            # Run the core agent generation logic
            output_text = agent_logic()
            
            # Simple guardrail check: Ensure response is not empty
            if not output_text or len(output_text.strip()) == 0:
                output_text = "Error: Agent generated an empty response."
                
            duration = round(time.time() - start_time, 3)
            print(f"[Harness: {self.agent_name}] Success in {duration}s")
            
            return {
                "status": "success",
                "response": output_text,
                "latency_seconds": duration
            }
        except Exception as e:
            duration = round(time.time() - start_time, 3)
            print(f"[Harness: {self.agent_name}] Error intercepted after {duration}s: {str(e)}")
            return {
                "status": "error",
                "response": f"Harness Error: {str(e)}",
                "latency_seconds": duration
            }
