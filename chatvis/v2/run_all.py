"""ChatVis agent to run all test cases in the ChatVis benchmark.

Faithful port of upstream ``run_all.py``. Importing this module executes the
agent (module-level side effects); shared bootstrap modules
(``chatvis.v2.env``, ``chatvis.v2.llm_client``, ``chatvis.v2.documents.*``,
``chatvis.v2.prompts.system_prompt``) are imported up-front so their import-time
side effects (PATH mutation, FAISS build, MiniLM load) run before the agent
loop.
"""

import os
import subprocess
from pathlib import Path

from chatvis.v2.documents.retrieval import process_prompt
from chatvis.v2.env import PATH_TO_PVPYTHON
from chatvis.v2.llm_client import LLM_MODEL, client
from chatvis.v2.prompts.system_prompt import system_prompt
from chatvis.v2.utils import extract_error_messages, extract_python_code

# -----  Execute the agent on all the test cases -----

python_file_name = "-full-prompt"
# python_file_name = '-quick-prompt'

cwd = Path.cwd()
eval_folder = os.getenv("GEN_VIS_DIR")
os.makedirs(eval_folder, exist_ok=True)
print("generated visualizations will be in", eval_folder, "\n")

folder_path = str(cwd.parent) + "/ChatVis_benchmark/test_cases/"

subfolders = [
    name
    for name in os.listdir(folder_path)
    if os.path.isdir(os.path.join(folder_path, name))
]

subfolder_paths = []
for folder in subfolders:
    subfolder_path = os.path.join(folder_path, folder)
    subfolder_paths.extend(
        os.path.join(subfolder_path, name)
        for name in os.listdir(subfolder_path)
        if os.path.isdir(os.path.join(subfolder_path, name))
    )

# print("subfolder_paths", subfolder_paths)

# Set your LLM model here
llm_model = LLM_MODEL

# Iterate thru all tasks
for folder in subfolder_paths:
    task = os.path.basename(folder)
    print("\ntask", task, "in folder", folder, "\n")

    prompt_file = folder + "/full_prompt.txt"
    # prompt_file = folder + "/quick_prompt.txt"
    with open(prompt_file, "r") as file:
        prompt = file.read()
        print(prompt)

    unique_ops = process_prompt(prompt)
    prompt_new = prompt + "Follow Example Operations \n{unique_ops}"

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
    cfp = folder
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
