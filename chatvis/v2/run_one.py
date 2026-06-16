"""ChatVis agent to run a single test case in the ChatVis benchmark.

Faithful port of upstream ``run_one.py``. Importing this module triggers the
shared bootstrap side effects (PATH mutation, FAISS build, MiniLM load) but
does not run the agent; the agent runs when this file is executed as a script
(``python -m chatvis.v2.run_one <test_case_path>``).
"""

import os
import subprocess
import sys
from pathlib import Path

from chatvis.v2.documents.retrieval import process_prompt
from chatvis.v2.env import PATH_TO_PVPYTHON
from chatvis.v2.llm_client import LLM_MODEL, client
from chatvis.v2.prompts.system_prompt import system_prompt
from chatvis.v2.utils import extract_error_messages, extract_python_code

# -----  Execute the agent on a single test case -----


def run_single_test_case(test_case_path):
    """
    Execute a single test case from the given path.

    Args:
        test_case_path (str): Path to the test case directory
    """

    python_file_name = "-full-prompt"
    # python_file_name = '-quick-prompt'

    cwd = Path.cwd()
    eval_folder = os.getenv("GEN_VIS_DIR")
    os.makedirs(eval_folder, exist_ok=True)
    print("generated visualizations will be in", eval_folder, "\n")

    # Validate the test case path
    if not os.path.exists(test_case_path):
        print(f"Error: Test case path does not exist: {test_case_path}")
        return

    if not os.path.isdir(test_case_path):
        print(f"Error: Path is not a directory: {test_case_path}")
        return

    task = os.path.basename(test_case_path)
    print("\ntask", task, "in folder", test_case_path, "\n")

    # Check if prompt file exists
    prompt_file = os.path.join(test_case_path, "full_prompt.txt")
    # prompt_file = os.path.join(test_case_path, "quick_prompt.txt")

    if not os.path.exists(prompt_file):
        print(f"Error: Prompt file not found: {prompt_file}")
        return

    with open(prompt_file, "r") as file:
        prompt = file.read()
        print(prompt)

    unique_ops = process_prompt(prompt)
    prompt_new = prompt + "Follow Example Operations \n{unique_ops}"

    # Set your LLM model here
    llm_model = LLM_MODEL

    # Call the LLM
    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt_new},
        ],
        model=llm_model,
    )
    script = chat_completion.choices[0].message.content

    # print("script:\n", script, "\n")
    # print("task+python_file_name:", task+python_file_name)

    file_path = extract_python_code(script, task + python_file_name)
    cfp = test_case_path
    if file_path:
        command = [PATH_TO_PVPYTHON + "/pvpython", file_path]

        result = subprocess.run(command, capture_output=True, text=True, cwd=cfp)
        errors = extract_error_messages(result.stderr)
        source_folder = cfp
        file_to_copy = task + "-screenshot.png"

        if not errors:
            subprocess.run(
                ["mv", os.path.join(source_folder, file_to_copy), eval_folder]
            )
        else:
            print("Error message is: ", result.stderr)
            print(errors)

        attempts = 0
        while errors and attempts < 5:
            attempts = attempts + 1

            followup_question = f"""
            I tried running the following Python script and encountered an error.

            **Error Message:**
            {errors}

            **Original Script:**
            {script}

            Can you help me fix the issue and provide a corrected version of the script?
            Please make sure the new script runs correctly without errors.
            """

            # Call the LLM again
            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": followup_question},
                ],
                model=llm_model,
            )

            # Assuming the AI provides new Python code in the response
            script = response.choices[0].message.content
            file_path = extract_python_code(script, task + python_file_name)

            # Execute the new script with pvpython
            result = subprocess.run(command, capture_output=True, text=True, cwd=cfp)

            # Extract errors from stderr, if any
            errors = extract_error_messages(result.stderr)
            if not errors:
                print("No more errors detected. Script executed successfully.")
                result = subprocess.run(
                    command, capture_output=True, text=True, cwd=cfp
                )
                print("Error message is: ", result.stderr)
                source_folder = cfp
                file_to_copy = task + "-screenshot.png"
                subprocess.run(
                    ["mv", os.path.join(source_folder, file_to_copy), eval_folder]
                )

                break
            else:
                print("Errors detected. Trying again...")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python run_one.py <test_case_path>")
        print(
            "Example: python run_one.py /path/to/ChatVis_benchmark/test_cases/task1/test_case_1"
        )
        sys.exit(1)

    test_case_path = sys.argv[1]
    run_single_test_case(test_case_path)
    print("completed run_single_test_case", flush=True)
