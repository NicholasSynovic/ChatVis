from string import Template

import pandas as pd
from pydantic import BaseModel

from chatvis.code_examples import CODE_EXAMPLES_DF
from chatvis.utils import pydantic_to_dataframe

PGP_SYSTEM_PROMPT: str = """
You are a prompt generator.
Do not provide any other text than the prompt.
"""


class PromptExample(BaseModel):
    name: str
    input_prompt: str
    generated_prompt: str


class PromptGenerationPrompt(BaseModel):
    name: str
    system_prompt: str = PGP_SYSTEM_PROMPT
    user_prompt: Template


class CodeGenerationPrompt(BaseModel):
    name: str
    system_prompt: str
    user_prompt: str = ""


PROMPT_EXAMPLES: list[PromptExample] = [
    PromptExample(
        name="ml_dvr",
        input_prompt="""
I would like to use ParaView to visualize a dataset.
Please generate a ParaView Python script for the following operations.
Read in the file named '<input_path>'.
Trace streamlines of the V data array seeded from a default point cloud.
Render the streamlines with tubes. Add cone glyphs to the streamlines.
Color the streamlines and glyphs by the Temp data array.
View the result in the +X direction.
Save a screenshot of the result in the filename '<output_path>'.
The rendered view and saved screenshot should be 1920 x 1080 pixels.
""",
        generated_prompt="""
This script uses ParaView to visualize streamlines of the V data array from the '<input_path>' file.
Operations include reading the file, tracing streamlines, rendering with tubes, adding cone glyphs, coloring by the Temp data array, and viewing from the +X direction.

Requirements:
- Read the file '<input_path>'.
- Trace streamlines of the V data array seeded from a default point cloud.
- Render the streamlines with tubes for better visibility.
- Add cone glyphs to the streamlines to indicate direction.
- Color both the streamlines and glyphs using the Temp data array.
- Orient the view to look from the +X direction.
- Save a screenshot of the view at 1920 x 1080 pixels resolution to '<output_path>'.
""",
    ),
    PromptExample(
        name="ml_iso",
        input_prompt="""
I would like to use ParaView to visualize a dataset.
Please generate a ParaView Python script for the following operations.
Read in the file named '<input_path>'.
Trace streamlines of the V data array seeded from a default point cloud.
Render the streamlines with tubes.
Add cone glyphs to the streamlines.
Color the streamlines and glyphs by the Temp data array.
View the result in the +X direction.
Save a screenshot of the result in the filename '<output_path>'.
The rendered view and saved screenshot should be 1920 x 1080 pixels.
""",
        generated_prompt="""
Generate a Python script using ParaView for performing visualization tasks based on the provided steps.
This script uses ParaView to visualize streamlines of the V data array from the '<input_path>' file.
Operations include reading the file, tracing streamlines, rendering with tubes, adding cone glyphs,
coloring by the Temp data array, and viewing from the +X direction.

Requirements step-by-step:
- Read the file '<input_path>'.
- Trace streamlines of the V data array seeded from a default point cloud.
- Render the streamlines with tubes for better visibility.
- Add cone glyphs to the streamlines to indicate direction.
- Color both the streamlines and glyphs using the Temp data array.
- Orient the view to look from the +X direction.
- Save a screenshot of the view at 1920 x 1080 pixels resolution to '<ouput_path>'.
""",
    ),
    PromptExample(
        name="ml_slice_iso",
        input_prompt="""
I would like to use ParaView to visualize a dataset.
Please generate a ParaView Python script for the following operations.
Read in the file named '<input_path>'.
Trace streamlines of the V data array seeded from a default point cloud.
Render the streamlines with tubes.
Add cone glyphs to the streamlines.
Color the streamlines and glyphs by the Temp data array.
View the result in the +X direction.
Save a screenshot of the result in the filename '<output_path>'.
The rendered view and saved screenshot should be 1920 x 1080 pixels.
""",
        generated_prompt="""
This script uses ParaView to visualize streamlines of the V data array from the '<input_path>' file.
Operations include reading the file, tracing streamlines, rendering with tubes, adding cone glyphs,
coloring by the Temp data array, and viewing from the +X direction.

Requirements:
- Read the file '<input_file>'.
- Trace streamlines of the V data array seeded from a default point cloud.
- Render the streamlines with tubes for better visibility.
- Add cone glyphs to the streamlines to indicate direction.
- Color both the streamlines and glyphs using the Temp data array.
- Orient the view to look from the +X direction.
- Save a screenshot of the view at 1920 x 1080 pixels resolution to '<output_file>'.
""",
    ),
    PromptExample(
        name="points_surf_clip",
        input_prompt="""
I would like to use ParaView to visualize a dataset.
Please generate a ParaView Python script for the following operations.
Read in the file named '<input_path>'.
Generate an 3d Delaunay triangulation of the dataset.
Clip the data with a y-z plane at x=0, keeping the -x half of the data and removing the +x half.
Render the image as a wireframe. Save a screenshot of the result in the filename '<output_path>'.
The rendered view and saved screenshot should be 1920 x 1080 pixels.
""",
        generated_prompt="",
    ),
    PromptExample(
        name="stream_glyph",
        input_prompt="""
I would like to use ParaView to visualize a dataset.
Please generate a ParaView Python script for the following operations.
Read in the file named '<input_path>'.
Trace streamlines of the V data array seeded from a default point cloud.
Render the streamlines with tubes.
Add cone glyphs to the streamlines.
Color the streamlines and glyphs by the Temp data array.
View the result in the +X direction.
Save a screenshot of the result in the filename '<output_path>'.
The rendered view and saved screenshot should be 1920 x 1080 pixels.
""",
        generated_prompt="""
This script uses ParaView to visualize streamlines of the V data array from the '<input_path>' file.
Operations include reading the file, tracing streamlines, rendering with tubes, adding cone glyphs,
coloring by the Temp data array, and viewing from the +X direction.

Requirements:
- Read the file '<input_path>'.
- Trace streamlines of the V data array seeded from a default point cloud.
- Render the streamlines with tubes for better visibility.
- Add cone glyphs to the streamlines to indicate direction.
- Color both the streamlines and glyphs using the Temp data array.
- Orient the view to look from the +X direction.
- Save a screenshot of the view at 1920 x 1080 pixels resolution to '<output_path>'.
""",
    ),
]

PROMPT_EXAMPLES_DF: pd.DataFrame = pydantic_to_dataframe(models=PROMPT_EXAMPLES)


LLM_PROMPTS: list[PromptGenerationPrompt] = [
    PromptGenerationPrompt(
        name="ml_dvr",
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
    ${example_user_prompt}

Here is an example generated prompt for the example user prompt:
    ${example_generated_user_prompt}

List out the operations to perform step by step.
"""
        ),
    ),
    PromptGenerationPrompt(
        name="ml_iso",
        user_prompt=Template(
            template="""
Generate the most effective prompt for the user input:

    Please generate a ParaView Python script for the following operations.
    Read in the file named '${input_path}'.
    Generate an isosurface of the variable var0 at value 0.5.
    Save a screenshot of the result in the filename '${output_path}'.
    The rendered view and saved screenshot should be 1920 x 1080 pixels.

Here is an example user prompt:
    ${example_user_prompt}

Here is an example generated prompt for the example user prompt:
    ${example_generated_user_prompt}

List out the operations to perform step by step.
"""
        ),
    ),
    PromptGenerationPrompt(
        name="ml_slice_iso",
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
    ${example_user_prompt}

Here is an example generated prompt for the example user prompt:
    ${example_generated_user_prompt}

List out the operations to perform step by step.
"""
        ),
    ),
    PromptGenerationPrompt(
        name="points_surf_clip",
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
    ${example_user_prompt}

Here is an example generated prompt for the example user prompt:
    ${example_generated_user_prompt}

List out the operations to perform step by step.
"""
        ),
    ),
    PromptGenerationPrompt(
        name="stream_glyph",
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
    ${example_user_prompt}

Here is an example generated prompt for the example user prompt:
    ${example_generated_user_prompt}

List out the operations to perform step by step.
"""
        ),
    ),
]

LLM_PROMPTS_DF: pd.DataFrame = pydantic_to_dataframe(models=LLM_PROMPTS)


CODE_GENERATION_PROMPTS: list[CodeGenerationPrompt] = [
    CodeGenerationPrompt(
        name="ml_dvr",
        system_prompt="""
You are a code assistant.
Please read the user prompt line by line and process it step by step.
Some operations are provided as examples:

{code_to_read}

{code_to_slice}\n

{code_to_contour} \n

{code_to_clip}

Use

\n{code_to_opacity_transfer_function}\n

and

{code_to_color_transfer_function}.

Use the examples

\n{code_to_render_view}

\n {code_to_render_view_direction}

\n {code_to_isometric_view}

and

\n{code_to_contour1Display}\n

and change the render view as the user is specifying.
Please use the example to write the correct code for the user.
Please use this code

\n{code_to_create_layout}\n

in all generated code snippets.
Do not use `clip1.InsideOut`.

Save the screenshot using

\n{code_to_save}."},
""",
    )
]
