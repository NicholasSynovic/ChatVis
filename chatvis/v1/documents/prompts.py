from enum import StrEnum

_COMMON_INPUT = """
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

_COMMON_OUTPUT = """
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
"""


class GeneratedPrompt(StrEnum):
    ML_DVR_INPUT = _COMMON_INPUT
    ML_DVR_OUTPUT = _COMMON_OUTPUT

    ML_ISO_INPUT = _COMMON_INPUT
    ML_ISO_OUTPUT = _COMMON_OUTPUT

    ML_SLICE_ISO_INPUT = _COMMON_INPUT
    ML_SLICE_ISO_OUTPUT = _COMMON_OUTPUT

    STREAM_GLYPH_INPUT = _COMMON_INPUT
    STREAM_GLYPH_OUTPUT = _COMMON_OUTPUT

    POINTS_SURF_CLIP_INPUT = """
I would like to use ParaView to visualize a dataset.
Please generate a ParaView Python script for the following operations.
Read in the file named '<input_path>'.
Generate an 3d Delaunay triangulation of the dataset.
Clip the data with a y-z plane at x=0, keeping the -x half of the data and removing the +x half.
Render the image as a wireframe. Save a screenshot of the result in the filename '<output_path>'.
The rendered view and saved screenshot should be 1920 x 1080 pixels.
"""

    POINTS_SURF_CLIP_OUTPUT = """
This script uses ParaView to visualize a 3D Delaunay triangulation of a point dataset from '<input_path>, with clipping and wireframe rendering.
Operations include reading the file, generating a Delaunay triangulation, clipping the data, rendering as wireframe, and saving a screenshot.

Requirements:

- Read the file '<input_path>'.
- Generate a 3D Delaunay triangulation of the dataset.
- Clip the resulting triangulation with a plane normal to the X-axis (a Y-Z plane) positioned at x=0, keeping the -X half of the data and removing the +X half.
- Render the clipped result using a wireframe representation.
- Set the render view size to 1920 x 1080 pixels.
- Save a screenshot of the result to '<output_path>' at 1920 x 1080 pixels resolution.
"""
