# In supervisor_agent.py

import os
import json
from typing import Dict, List, Any

# Core imports from the Agent-S framework
from Agent_S.gui_agents.s2.core.module import BaseModule
from Agent_S.gui_agents.s2.utils.common_utils import call_llm_safe

# This is the detailed prompt that defines the Supervisor's role and tasks.
SUPERVISOR_PROMPT_TEMPLATE = """
You are an expert QA Supervisor Agent. Your task is to analyze a completed test run, including the step-by-step logs and the corresponding UI screenshots.

Based on the full test trace, you will provide a comprehensive evaluation report.

**High-Level Goal of the Test:**
{goal}

**Full Test Log:**
{log_trace}

**Analysis Instructions:**
Review the entire test trace from start to finish. Pay attention to the following:
1.  **Efficiency:** Was the plan logical and direct? Were there any unnecessary or repeated steps?
2.  **Errors & Recovery:** Did the agent encounter any errors? If so, how well did it recover? Was the Verifier's verdict accurate?
3.  **Overall Success:** Did the agent successfully complete the high-level goal?

**Report Generation:**
Based on your analysis, generate a report in the following JSON format. Provide actionable and specific feedback.

{{
  "overall_outcome": "SUCCESS" or "FAILURE",
  "summary": "A brief, one-sentence summary of the test run.",
  "prompt_improvements": "Suggest a better or more specific high-level goal prompt to make the test more effective or less ambiguous.",
  "failure_analysis": "If the test failed or had issues, explain the root cause. For example, 'The agent failed to find the correct button on step 4 because the UI was slow to load.'",
  "coverage_expansion": "Suggest a new, related test case to expand the test coverage. For example, 'Test that Wi-Fi automatically reconnects after being toggled off and on.'"
}}
"""

class SupervisorAgent(BaseModule):
    """
    Analyzes a complete test episode (logs and screenshots) and proposes improvements.
    """
    def __init__(self, engine_params: Dict, platform: str):
        """
        Initializes the SupervisorAgent.
        """
        super().__init__(engine_params, platform)
        self.analysis_agent = self._create_agent(system_prompt="")

    def analyze_trace(self, goal: str, logs: List[Dict[str, Any]], screenshots: List[Any]) -> Dict[str, Any]:
        """
        Analyzes the full test trace and generates an evaluation report.
        """
        print("\n--- SUPERVISOR: Analyzing full test trace... ---")

        log_trace_str = "\n".join([f"Step {i+1}: {log}" for i, log in enumerate(logs)])
        prompt = SUPERVISOR_PROMPT_TEMPLATE.format(goal=goal, log_trace=log_trace_str)
        
        self.analysis_agent.add_message(prompt, image_content=screenshots, role="user")

        try:
            response_text = call_llm_safe(self.analysis_agent)
            json_response_text = response_text.strip().replace("```json", "").replace("```", "").strip()
            report = json.loads(json_response_text)
            print("--- SUPERVISOR: Analysis complete. ---")
            return report

        except (Exception, json.JSONDecodeError) as e:
            print(f"SUPERVISOR: ERROR - Could not generate report. Details: {e}")
            return {"error": "Failed to generate a valid report from the LLM."}
