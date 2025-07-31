# In verifier_agent.py

import json
from typing import Dict, Tuple

# Core imports from the Agent-S framework
from Agent_S.gui_agents.s2.core.module import BaseModule
from Agent_S.gui_agents.s2.utils.common_utils import call_llm_safe

# This is the prompt that will define the Verifier's behavior.
VERIFIER_PROMPT_TEMPLATE = """
You are a meticulous QA Verifier Agent. Your task is to determine if a given subgoal was successfully completed by analyzing the current state of the application's UI.

Based on the subgoal and the UI elements provided, you must conclude whether the action was a "PASS" or "FAIL".

**Subgoal to Verify:**
{subgoal}

**Current UI State:**
{ui_elements}

**Analysis and Verdict:**
Review the UI state and determine if it reflects the successful completion of the subgoal. For example, if the subgoal was "turn Wi-Fi off", the UI state should contain a Wi-Fi toggle switch that is in the "off" or "unchecked" state.

Respond ONLY with a JSON object in the following format:
{{
  "verdict": "PASS" or "FAIL",
  "reason": "A brief explanation of your reasoning."
}}
"""

class VerifierAgent(BaseModule):
    """
    An agent that uses an LLM to verify app behavior, built on the Agent-S BaseModule.
    """
    def __init__(self, engine_params: Dict, platform: str):
        """
        Initializes the VerifierAgent.
        """
        super().__init__(engine_params, platform)
        self.verification_agent = self._create_agent(system_prompt="")

    def verify(self, subgoal: str, observation: Dict) -> Tuple[bool, str]:
        """
        Uses the LLM to verify the current UI state against the intended subgoal.
        """
        print(f"VERIFIER: Asking LLM to check if '{subgoal}' was successful...")
        
        ui_elements_str = "\n".join([f"- {elem}" for elem in observation.get("ui_elements", [])])
        
        prompt = VERIFIER_PROMPT_TEMPLATE.format(subgoal=subgoal, ui_elements=ui_elements_str)
        self.verification_agent.add_message(prompt, role="user")

        try:
            response_text = call_llm_safe(self.verification_agent)
            json_response_text = response_text.strip().replace("```json", "").replace("```", "").strip()
            result = json.loads(json_response_text)
            verdict = result.get("verdict", "FAIL").upper()
            reason = result.get("reason", "No reason provided.")
            
            self.verification_agent.reset()
            return verdict == "PASS", reason

        except (Exception, json.JSONDecodeError) as e:
            print(f"VERIFIER: ERROR - Could not parse LLM response. Details: {e}")
            self.verification_agent.reset()
            return True, "Could not get a valid verdict from the LLM."
