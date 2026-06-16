"""OpenAI client + model selection.

Side effects on import: reads ``OPENAI_API_KEY`` / ``LLM_MODEL`` from the
environment and constructs a module-level ``openai.OpenAI`` client. Faithful
port of the OpenAI bootstrap from ``run_all.py``/``run_one.py``.
"""

import os

import openai

# OpenAI key, set through environment variable
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI(
    api_key=OPENAI_API_KEY,
)

# LLM model
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")
