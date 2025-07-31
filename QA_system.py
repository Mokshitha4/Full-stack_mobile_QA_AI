# In qa_agent.py

from typing import Dict, List, Tuple

# Import the base class from the Agent-S framework
from Agent_S.gui_agents.s2.agents.agent_s import AgentS2
# Import your custom VerifierAgent that uses the Agent-S architecture
from verifier_agent import VerifierAgent

class QAAgent(AgentS2):
    """
    The complete QA Orchestrator Agent.

    This class extends the AgentS2 framework by adding a Verifier to check
    the outcome of each step, creating a full Plan -> Execute -> Verify loop.
    """
    def __init__(self, *args, **kwargs):
        """
        Initializes the parent AgentS2 and the custom VerifierAgent.
        """
        # First, call the initializer of the parent AgentS2 class. This sets up
        # the Planner (Manager) and Executor (Worker) agents.
        super().__init__(*args, **kwargs)

        # Now, initialize your VerifierAgent, passing the necessary
        # engine_params and platform from the main agent to it.
        self.verifier = VerifierAgent(
            engine_params=self.engine_params,
            platform=self.platform
        )
        print("QAAgent initialized with a Verifier (Agent-S Architecture).")

    def predict(self, instruction: str, observation: Dict) -> Tuple[Dict, List[str]]:
        """
        Orchestrates the QA workflow for a single step.
        """
        # 1. PLAN & EXECUTE: Get the next action from the parent AgentS2 logic.
        # This single call runs the Planner (Manager) to create a plan (if needed)
        # and then runs the Executor (Worker) to decide the next action.
        info, actions = super().predict(instruction, observation)

        # 2. VERIFY: After the Executor proposes an action, verify the result.
        subtask = info.get("subtask")

        # Only verify if there's a subtask and the agent isn't finished.
        if subtask and actions and actions[0] != "DONE":
            is_verified, reason = self.verifier.verify(subtask, observation)

            # 3. REPLAN (if needed): If verification fails, trigger a replan.
            # This is the "dynamic replanning" required by the challenge.
            if not is_verified:
                print(f"VERIFIER: {reason}. Triggering a replan.")
                # These flags tell the parent AgentS2's internal loop
                # to call the Planner (Manager) again on the next turn.
                self.requires_replan = True
                self.failure_subtask = self.current_subtask

        return info, actions