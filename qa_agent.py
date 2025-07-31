# In qa_agent.py

from typing import Dict, List, Tuple

# Import the base class from the Agent-S framework
from Agent_S.gui_agents.s2.agents.agent_s import AgentS2
# Import your custom VerifierAgent
from verifier_agent import VerifierAgent

class QAAgent(AgentS2):
    """
    The QA Orchestrator Agent that extends AgentS2 with a Verifier.
    """
    def __init__(self, *args, **kwargs):
        """
        Initializes the parent AgentS2 and the custom VerifierAgent.
        """
        super().__init__(*args, **kwargs)

        self.verifier = VerifierAgent(
            engine_params=self.engine_params,
            platform=self.platform
        )
        print("QAAgent initialized with a Verifier (Agent-S Architecture).")

    def predict_and_verify(self, instruction: str, observation: Dict) -> Tuple[Dict, List[str], Dict]:
        """
        Orchestrates the QA workflow for a single step: Plan, Execute, and Verify.
        """
        # 1. PLAN & EXECUTE: Get the next action from the parent AgentS2 logic.
        info, actions = super().predict(instruction, observation)

        # 2. VERIFY: After the Executor proposes an action, verify the result.
        subtask = info.get("subtask")
        verification_result = {'passed': True, 'reason': 'No verification performed.'}

        if subtask and actions and actions[0] != "DONE":
            is_verified, reason = self.verifier.verify(subtask, observation)
            verification_result = {'passed': is_verified, 'reason': reason}

            # 3. REPLAN (if needed): If verification fails, trigger a replan.
            if not is_verified:
                self.requires_replan = True
                self.failure_subtask = self.current_subtask
        
        return info, actions, verification_result
