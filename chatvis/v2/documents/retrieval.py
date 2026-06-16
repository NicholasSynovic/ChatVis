"""Prompt-driven retrieval over the FAISS-backed operations index."""

from chatvis.v2.documents.embeddings import search_similar_operation


# Process prompt
def process_prompt(prompt: str):
    """
    Process a text prompt by splitting into lines, searching for similar operations,
    and returning unique operations by name.

    Args:
        prompt (str): The input prompt string.

    Returns:
        dict: A dictionary of unique operations keyed by name.
    """
    # Split prompt into non-empty lines
    prompt_lines = [line.strip() for line in prompt.strip().split("\n") if line.strip()]

    # Collect results
    all_results = []
    for line in prompt_lines:
        result = search_similar_operation(line)
        all_results.append(result)

    # Flatten list of lists
    flat_list = [item for sublist in all_results for item in sublist]

    # Deduplicate by name
    unique_ops = {}
    for op in flat_list:
        name = op["name"]
        if name not in unique_ops:
            unique_ops[name] = op  # Keep the first occurrence

    return unique_ops
