from enum import StrEnum


class UserPrompts(StrEnum):
    """
    Use `input_path` and `output_path` when formatting strings.
    """

    ML_ISO = """
Please generate a ParaView Python script for the following operations.
Read in the file named {input_path}.
Generate an isosurface of the variable var0 at value 0.5.
Save a screenshot of the result in the filename {output_path}.
The rendered view and saved screenshot should be 1920 x 1080 pixels.
"""

    ML_SLICE_ISO = """
Please generate a ParaView Python script for the following operations. \
Read in the file named {input_path}.
Slice the volume in a plane parallel to the y-z plane at x=0.
Take a contour through the slice at the value 0.5.
Color the contour red.
Rotate the view to look at the +x direction.
Save a screenshot of the result in the filename {output_path}.
The rendered view and saved screenshot should be 1920 x 1080 pixels.
"""

    ML_DVR = """
Please generate a ParaView Python script for the following operations.
Read in the file named {input_path}.
Generate a volume rendering using the default transfer function.
Rotate the view to an isometric direction.
Save a screenshot of the result in the filename {output_path}.
The rendered view and saved screenshot should be 1920 x 1080 pixels.
"""

    POINTS_SURF_CLIP = """
Please generate a ParaView Python script for the following operations.
Read in the file named {input_path}.
Generate a 3d Delaunay triangulation of the dataset.
Clip the data with a y-z plane at x=0, keeping the -x half of the data and removing the +x half.
Render the image as a wireframe.
View the result in an isometric view.
Save a screenshot of the result in the filename {output_path}.
The rendered view and saved screenshot should be 1920 x 1080 pixels.
"""

    STREAM_GLYPH = """
Please generate a ParaView Python script for the following operations.
Read in the file named {input_path}.
Trace streamlines of the V data array seeded from a default point cloud.
Render the streamlines with tubes.
Add cone glyphs to the streamlines.
Color the streamlines and glyphs by the Temp data array.
View the result in the +X direction.
Save a screenshot of the result in the filename {output_path}.
The rendered view and saved screenshot should be 1920 x 1080 pixels.
"""
