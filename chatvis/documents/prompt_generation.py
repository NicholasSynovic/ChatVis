from string import Template

from pydantic import BaseModel, ConfigDict

from chatvis.documents.prompt_generation_examples import (
    PROMPT_GENERATION_EXAMPLES,
    PromptGenerationExample,
)


class PromptGenerationPrompt(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    system_prompt: str = """
You are a prompt generator.
Do not provide any other text than the prompt.
"""
    user_prompt: Template
    example_prompt: PromptGenerationExample


PROMPT_GENERATION_PROMPTS: dict[str, PromptGenerationPrompt] = {
    "ml-dvr": PromptGenerationPrompt(
        example_prompt=PROMPT_GENERATION_EXAMPLES["ml-dvr"],
        user_prompt=Template(
            template="""
Generate the most effective prompt for the user input:

    I would like to use ParaView to visualize a dataset.
    Please generate a ParaView Python script for the following operations.
    Read in the file named '${input_path}'.
    Generate a volume rendering using the default transfer function.
    Rotate the view to an isometric direction.
    Save a screenshot of the result in the filename '${output_path}'.
    The rendered view and saved screenshot should be 1920 x 1080 pixels.

Here is an example user prompt:
    ${input_prompt}

Here is an example generated prompt for the example user prompt:
    ${generated_prompt}

List out the operations to perform step by step.
"""
        ),
    ),
    "ml-iso": PromptGenerationPrompt(
        example_prompt=PROMPT_GENERATION_EXAMPLES["ml-iso"],
        user_prompt=Template(
            template="""
Generate the most effective prompt for the user input:

    Please generate a ParaView Python script for the following operations.
    Read in the file named '${input_path}'.
    Generate an isosurface of the variable var0 at value 0.5.
    Save a screenshot of the result in the filename '${output_path}'.
    The rendered view and saved screenshot should be 1920 x 1080 pixels.

Here is an example user prompt:
    ${input_prompt}

Here is an example generated prompt for the example user prompt:
    ${generated_prompt}

List out the operations to perform step by step.
"""
        ),
    ),
    "ml-slice-iso": PromptGenerationPrompt(
        example_prompt=PROMPT_GENERATION_EXAMPLES["ml-slice-iso"],
        user_prompt=Template(
            template="""
Generate the most effective prompt for the user input:

    Please generate a ParaView Python script for the following operations.
    Read in the file named '${input_path}'.
    Slice the volume in a plane parallel to the y-z plane at x=0.
    Take a contour through the slice at the value 0.5.
    Color the contour red.
    Rotate the view to look at the +x direction.
    Save a screenshot of the result in the filename '${output_path}'.
    The rendered view and saved screenshot should be 1920 x 1080 pixels.

Here is an example user prompt:
    ${input_prompt}

Here is an example generated prompt for the example user prompt:
    ${generated_prompt}

List out the operations to perform step by step.
"""
        ),
    ),
    "points-surf-clip": PromptGenerationPrompt(
        example_prompt=PROMPT_GENERATION_EXAMPLES["points-surf-clip"],
        user_prompt=Template(
            template="""
Generate the most effective prompt for the user input:

    I would like to use ParaView to visualize a dataset.
    Please generate a ParaView Python script for the following operations.
    Read in the file named '${input_path}'.
    Generate an 3d Delaunay triangulation of the dataset.
    Clip the data with a y-z plane at x=0, keeping the -x half of the data and removing the +x half.
    Render the image as a wireframe.
    Save a screenshot of the result in the filename '${output_path}'.
    The rendered view and saved screenshot should be 1920 x 1080 pixels.

Here is an example user prompt:
    ${input_prompt}

Here is an example generated prompt for the example user prompt:
    ${generated_prompt}

List out the operations to perform step by step.
"""
        ),
    ),
    "stream-glyph": PromptGenerationPrompt(
        example_prompt=PROMPT_GENERATION_EXAMPLES["stream-glyph"],
        user_prompt=Template(
            template="""
Generate the most effective prompt for the user input:

    I would like to use ParaView to visualize a dataset.
    Please generate a ParaView Python script for the following operations.
    Read in the file named '${input_path}'.
    Trace streamlines of the V data array seeded from a default point cloud.
    Render the streamlines with tubes.
    Add cone glyphs to the streamlines.
    Color the streamlines and glyphs by the Temp data array.
    View the result in the +X direction.
    Save a screenshot of the result in the filename '${output_path}'.
    The rendered view and saved screenshot should be 1920 x 1080 pixels.

Here is an example user prompt:
    ${input_prompt}

Here is an example generated prompt for the example user prompt:
    ${generated_prompt}

List out the operations to perform step by step.
"""
        ),
    ),
}
