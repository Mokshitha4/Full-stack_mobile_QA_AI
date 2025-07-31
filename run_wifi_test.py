# In run_wifi_test.py (NOW LOCATED INSIDE the android_world folder)

import sys
import os
import time
import json
import numpy as np
from PIL import Image
import io

# --- This block adds the 'Agent-S' folder to Python's path ---
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
agent_s_path = os.path.join(parent_dir, 'Agent-S')
sys.path.append(agent_s_path)
# -----------------------------------------------------------

from qa_agent import QAAgent
from supervisor_agent import SupervisorAgent
from android_world.android_world.env import env_launcher
from android_world.android_world.env.json_action import JSONAction
from absl import app

# --- Definitive Translation Layer for Agent-S and Android World ---
class EnvWrapper:
    """
    A wrapper that acts as a definitive translation layer between Agent-S function calls
    and the JSONAction format expected by the Android World environment.
    """
    def __init__(self, env):
        self._env = env
        self.notes = []
        self.ui_elements = [] # To store the latest UI elements

    def __getattr__(self, name):
        return getattr(self._env, name)

    def set_ui_elements(self, elements):
        """Receives the latest UI elements from the main loop."""
        self.ui_elements = elements

    def swipe(self, *args):
        """
        Translates an Agent-S swipe into an android_world scroll action.
        """
        print(f"WRAPPER: Translating swipe {args} into a scroll action.")
        
        if isinstance(args[0], str):
            start_location, direction = args[0], args[1]
        else:
            if len(args) == 4:
                start_x, start_y, end_x, end_y = args
            elif len(args) == 5:
                start_x, start_y, end_x, end_y, duration = args
            else:
                raise ValueError(f"Invalid number of arguments for swipe: {len(args)}")

            delta_x = end_x - start_x
            delta_y = end_y - start_y
            
            if abs(delta_y) > abs(delta_x):
                direction = "down" if delta_y > 0 else "up"
            else:
                direction = "right" if delta_x > 0 else "left"
        
        return {"action_type": "scroll", "direction": direction}

    def wait(self, seconds):
        print(f"WRAPPER: Translating wait...")
        return {"action_type": "wait"}

    def click(self, *args):
        """
        Handles both descriptive and coordinate-based clicks from Agent-S.
        """
        # Case 1: Descriptive click, e.g., click("Settings icon", 1)
        if isinstance(args[0], str):
            description = args[0].lower()
            print(f"WRAPPER: Translating descriptive click: '{description}'")
            
            search_keywords = description.split()

            for i, element in enumerate(self.ui_elements):
                # Combine all text attributes of the element for a robust search
                element_text_blob = ""
                if element.text:
                    element_text_blob += element.text.lower()
                if hasattr(element, 'content_description') and element.content_description:
                    element_text_blob += " " + element.content_description.lower()
                if element.resource_id:
                    element_text_blob += " " + element.resource_id.lower()

                # Check if all keywords from the agent's description are present
                if all(keyword in element_text_blob for keyword in search_keywords):
                    print(f"WRAPPER: Found element at index {i}. Returning click action.")
                    return {"action_type": "click", "index": i}
            
            print(f"WRAPPER: Could not find element for '{description}'. Defaulting to wait.")
            return {"action_type": "wait"}

        # Case 2: Coordinate-based click, e.g., click(100, 200)
        else:
            x, y = args[0], args[1]
            print(f"WRAPPER: Translating coordinate click({x}, {y})")
            return {"action_type": "click", "x": int(x), "y": int(y)}
    
    def type(self, text):
        print(f"WRAPPER: Translating type...")
        return {"action_type": "input_text", "text": text}

    def done(self):
        print("WRAPPER: Translating done()")
        return "DONE"

    def assign_coordinates(self, plan, obs):
        pass
# --------------------------------------------------------------------------------

def convert_to_png(pixels: np.ndarray) -> bytes:
    image = Image.fromarray(pixels)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()

def main(_):
    print("--- Starting Wi-Fi QA Test ---")
    high_level_goal = "Test turning Wi-Fi on and off"
    print(f"High-Level Goal: {high_level_goal}")

    try:
        env = env_launcher.load_and_setup_env(
            console_port=5554,
            emulator_setup=False,
            adb_path=r'C:\Users\moksh\AppData\Local\Android\Sdk\platform-tools\adb.exe'
        )
    except Exception as e:
        print(f"ERROR: Failed to launch environment: {e}")
        return

    wrapped_env = EnvWrapper(env)

    engine_params = { "engine_type": "openai", "model": "gpt-4-turbo", "api_key": os.getenv("OPENAI_API_KEY") }
    agent = QAAgent( engine_params=engine_params, grounding_agent=wrapped_env, platform='windows' )
    supervisor_engine_params = { "engine_type": "openai", "model": "gpt-4-vision-preview", "api_key": os.getenv("OPENAI_API_KEY") }
    supervisor = SupervisorAgent(engine_params=supervisor_engine_params, platform='windows')

    state = env.reset()
    observation = { 'screenshot': convert_to_png(state.pixels), 'ui_elements': state.ui_elements }
    wrapped_env.set_ui_elements(state.ui_elements) # Initial update
    
    is_done = False
    max_steps = 20
    test_logs = []
    screenshots = []

    for i in range(max_steps):
        print(f"\n--- Step {i+1} ---")

        info, actions, verification_result = agent.predict_and_verify(high_level_goal, observation)
        action_result = actions[0] if actions else "DONE"
        subtask = info.get('subtask')
        
        print(f"PLANNER/EXECUTOR: Subtask is '{subtask}'. Proposing action: {action_result}")
        print(f"VERIFIER: {verification_result['reason']}")

        if action_result == "DONE":
            is_done = True
            break
        
        try:
            converted_action = JSONAction(**action_result)
            new_state = env.execute_action(converted_action)
            
            if new_state is None:
                new_state = env.get_state()

            observation = { 'screenshot': convert_to_png(new_state.pixels), 'ui_elements': new_state.ui_elements }
            wrapped_env.set_ui_elements(new_state.ui_elements) # Update for next step
        except Exception as e:
            print(f"ERROR: Failed to execute action '{action_result}'. Details: {e}")
            break

        step_log = { "step": i + 1, "subtask": subtask, "proposed_action": str(action_result), "verification_passed": verification_result['passed'], "verification_reason": verification_result['reason'] }
        test_logs.append(step_log)
        screenshots.append(observation['screenshot'])
        
        time.sleep(2)

    if test_logs:
        report = supervisor.analyze_trace(high_level_goal, test_logs, screenshots)
        print("\n--- SUPERVISOR'S REPORT ---")
        print(json.dumps(report, indent=2))
        print("--------------------------")

    print(f'\n--- Test {"Successful" if is_done else "Failed"} ---')
    env.close()


if __name__ == '__main__':
    app.run(main)
