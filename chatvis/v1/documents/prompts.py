from enum import StrEnum

# Shared base block used across multiple generated outputs to prevent repetition
_STREAM_REQUIREMENTS = """Requirements:
- Read the file '{input_placeholder}'.
- Trace streamlines of the V data array seeded from a default point cloud.
- Render the streamlines with tubes for better visibility.
- Add cone glyphs to the streamlines to indicate direction.
- Color both the streamlines and glyphs using the Temp data array.
- Orient the view to look from the +X direction.
- Save a screenshot of the view at 1920 x 1080 pixels resolution to '{output_placeholder}'."""


class InputPrompt(StrEnum):
    """Source of truth for unique user input requests."""

    STREAM_TRACE = """
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
"""

    DELAUNAY_CLIP = """
I would like to use ParaView to visualize a dataset.
Please generate a ParaView Python script for the following operations.
Read in the file named '<input_path>'.
Generate an 3d Delaunay triangulation of the dataset.
Clip the data with a y-z plane at x=0, keeping the -x half of the data and removing the +x half.
Render the image as a wireframe. Save a screenshot of the result in the filename '<output_path>'.
The rendered view and saved screenshot should be 1920 x 1080 pixels.
"""


class GeneratedOutput(StrEnum):
    """Source of truth for LLM-generated prompt responses, accounting for variations."""

    STREAM_GLYPH_AND_DVR = f"""
This script uses ParaView to visualize streamlines of the V data array from the '<input_path>' file.
Operations include reading the file, tracing streamlines, rendering with tubes, adding cone glyphs, coloring by the Temp data array, and viewing from the +X direction.

{_STREAM_REQUIREMENTS.format(input_placeholder="<input_path>", output_placeholder="<output_path>")}
"""

    ML_ISO = f"""
Generate a Python script using ParaView for performing visualization tasks based on the provided steps.
This script uses ParaView to visualize streamlines of the V data array from the '<input_path>' file.
Operations include reading the file, tracing streamlines, rendering with tubes, adding cone glyphs,
coloring by the Temp data array, and viewing from the +X direction.

Requirements step-by-step:
{-_STREAM_REQUIREMENTS.format(input_placeholder="<input_path>", output_placeholder="<output_path>").replace("Requirements:", "")}
"""

    ML_SLICE_ISO = f"""
This script uses ParaView to visualize streamlines of the V data array from the '<input_path>' file.
Operations include reading the file, tracing streamlines, rendering with tubes, adding cone glyphs,
coloring by the Temp data array, and viewing from the +X direction.

{_STREAM_REQUIREMENTS.format(input_placeholder="<input_file>", output_placeholder="<output_file>")}
"""
