from pydantic import BaseModel


class PythonCode(BaseModel):
    name: str
    code: str


class GeneratedPrompts(BaseModel):
    name: str
    input_prompt: str
    generated_prompt: str


CODE_SOURCES: list[PythonCode] = [
    PythonCode(
        name="code_to_read",
        code="""
from paraview.simple import *
# read the input data
ml100vtk = LegacyVTKReader(FileNames=<input_path>)
        """,
    ),
    PythonCode(
        name="code_to_slice",
        code="""
from paraview.simple import *
# create a new slice
slice1 = Slice(registrationName='Slice1', Input=ml100vtk)
slice1.SliceType = 'Plane'
slice1.HyperTreeGridSlicer = 'Plane'
slice1.SliceOffsetValues = [0.0]
slice1.PointMergeMethod = 'Uniform Binning'
""",
    ),
    PythonCode(
        name="code_to_contour",
        code="""
from paraview.simple import *
# create a new contour
contour1 = Contour(registrationName='Contour1', Input=ml100vtk)
contour1.ContourBy = ['POINTS', 'var0']
contour1.Isosurfaces = [0.5]
contour1.PointMergeMethod = 'Uniform Binning'
""",
    ),
    PythonCode(
        name="code_to_clip",
        code="""
from paraview.simple import *
# create a new clip filter
clip = Clip(registrationName='Clip', Input=delaunay3D)
clip.ClipType = 'Plane'
clip.ClipType.Origin = [0.0, 0.0, 0.0]
clip.ClipType.Normal = [1.0, 0.0, 0.0]
""",
    ),
    PythonCode(
        name="code_to_color_transfer_function",
        code="""
from paraview.simple import *
# get color transfer function/color map for 'var0'
var0LUT = GetColorTransferFunction('var0')
var0LUT.RGBPoints = [min, 0.0, 0.0, 0.75, (min + max) / 2.0, 0.75, 0.75, 0.75, max, 0.75, 0.0, 0.0]
""",
    ),
    PythonCode(
        name="code_to_opacity_transfer_function",
        code="""
from paraview.simple import *
# get opacity transfer function/opacity map for 'var0'
var0PWF = GetOpacityTransferFunction('var0')
var0PWF.Points = [min, 0.0, 0.5, 0.0, (min + max) / 2.0, 0.5, 0.5, 0.0, max, 1.0, 0.5, 0.0]
""",
    ),
    PythonCode(
        name="code_to_create_layout",
        code="""
from paraview.simple import *
# create new layout object
layout = CreateLayout(name='Layout')
layout.AssignView(0, renderView)
""",
    ),
    PythonCode(
        name="code_to_contour1Display",
        code="""
from paraview.simple import *
# show data
contour1Display = Show(contour1, renderView)
contour1Display.ColorArrayName = ['POINTS', '']
contour1Display.DiffuseColor = [1.0, 0.0, 0.0]
""",
    ),
    PythonCode(
        name="code_to_render_view",
        code="""
from paraview.simple import *
# create view
renderView = CreateView('RenderView')
renderView.ViewSize = [1920, 1080]
""",
    ),
    PythonCode(
        name="code_to_render_view_direction",
        code="""
from paraview.simple import *
# set render view direction
renderView.ResetActiveCameraToPositiveX()
renderView.ResetCamera()
""",
    ),
    PythonCode(
        name="code_to_isometric_view",
        code="""
from paraview.simple import *
# set render view direction
renderView.ApplyIsometricView()
renderView.ResetCamera()
""",
    ),
    PythonCode(
        name="code_to_save",
        code="""
from paraview.simple import *
# Save a screenshot of the render view
SaveScreenshot(
    '<output_path>',
    renderView,
    ImageResolution=[1920, 1080],
    OverrideColorPalette='WhiteBackground',
)
""",
    ),
    PythonCode(
        name="code_to_stream_tracer",
        code="""
from paraview.simple import *
# create a new stream tacer
streamTracer = StreamTracer(
    registrationName='StreamTracer1',
    Input=velocity,
    SeedType='Point Cloud',
)
""",
    ),
    PythonCode(
        name="code_to_glyph",
        code="""
from paraview.simple import *
# create a new glyph
glyph = Glyph(registrationName='Glyph1', Input=streamTracer, GlyphType='Cone')
glyph.OrientationArray = ['POINTS', 'V']
glyph.ScaleArray = ['POINTS', 'V']
glyph.ScaleFactor = 0.05
""",
    ),
    PythonCode(
        name="code_to_tube",
        code="""
from paraview.simple import *
# create a new tube
tube = Tube(registrationName='Tube1', Input=streamTracer)
tube.Radius = 0.075
""",
    ),
    PythonCode(
        name="code_to_color_tube_glyphs_Temp_variable",
        code="""
from paraview.simple import *
# color tubes and glyphs by Temp variable
ColorBy(tubeDisplay, ('POINTS', 'Temp'))
ColorBy(glyphDisplay, ('POINTS', 'Temp'))
tubeDisplay.RescaleTransferFunctionToDataRange(True)
glyphDisplay.RescaleTransferFunctionToDataRange(True)
""",
    ),
]

GENERATED_SOURCES: list[GeneratedPrompts] = [
    GeneratedPrompts(
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
    GeneratedPrompts(
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
    GeneratedPrompts(
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
    GeneratedPrompts(
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
    GeneratedPrompts(
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
