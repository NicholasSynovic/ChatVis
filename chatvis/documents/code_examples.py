from pydantic import BaseModel


class CodeExample(BaseModel):
    code: str


CODE_EXAMPLES: dict[str, CodeExample] = {
    "code_to_read": CodeExample(
        code="""
from paraview.simple import *
# read the input data
ml100vtk = LegacyVTKReader(FileNames=<input_path>)
""",
    ),
    "code_to_slice": CodeExample(
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
    "code_to_contour": CodeExample(
        code="""
from paraview.simple import *
# create a new contour
contour1 = Contour(registrationName='Contour1', Input=ml100vtk)
contour1.ContourBy = ['POINTS', 'var0']
contour1.Isosurfaces = [0.5]
contour1.PointMergeMethod = 'Uniform Binning'
""",
    ),
    "code_to_clip": CodeExample(
        code="""
from paraview.simple import *
# create a new clip filter
clip = Clip(registrationName='Clip', Input=delaunay3D)
clip.ClipType = 'Plane'
clip.ClipType.Origin = [0.0, 0.0, 0.0]
clip.ClipType.Normal = [1.0, 0.0, 0.0]
""",
    ),
    "code_to_color_transfer_function": CodeExample(
        code="""
from paraview.simple import *
# get color transfer function/color map for 'var0'
var0LUT = GetColorTransferFunction('var0')
var0LUT.RGBPoints = [min, 0.0, 0.0, 0.75, (min + max) / 2.0, 0.75, 0.75, 0.75, max, 0.75, 0.0, 0.0]
""",
    ),
    "code_to_opacity_transfer_function": CodeExample(
        code="""
from paraview.simple import *
# get opacity transfer function/opacity map for 'var0'
var0PWF = GetOpacityTransferFunction('var0')
var0PWF.Points = [min, 0.0, 0.5, 0.0, (min + max) / 2.0, 0.5, 0.5, 0.0, max, 1.0, 0.5, 0.0]
""",
    ),
    "code_to_create_layout": CodeExample(
        code="""
from paraview.simple import *
# create new layout object
layout = CreateLayout(name='Layout')
layout.AssignView(0, renderView)
""",
    ),
    "code_to_contour1Display": CodeExample(
        code="""
from paraview.simple import *
# show data
contour1Display = Show(contour1, renderView)
contour1Display.ColorArrayName = ['POINTS', '']
contour1Display.DiffuseColor = [1.0, 0.0, 0.0]
""",
    ),
    "code_to_render_view": CodeExample(
        code="""
from paraview.simple import *
# create view
renderView = CreateView('RenderView')
renderView.ViewSize = [1920, 1080]
""",
    ),
    CodeExample(
        name="code_to_render_view_direction",
        code="""
from paraview.simple import *
# set render view direction
renderView.ResetActiveCameraToPositiveX()
renderView.ResetCamera()
""",
    ),
    "code_to_isometric_view": CodeExample(
        code="""
from paraview.simple import *
# set render view direction
renderView.ApplyIsometricView()
renderView.ResetCamera()
""",
    ),
    "code_to_save": CodeExample(
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
    "code_to_stream_tracer": CodeExample(
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
    "code_to_glyph": CodeExample(
        code="""
from paraview.simple import *
# create a new glyph
glyph = Glyph(registrationName='Glyph1', Input=streamTracer, GlyphType='Cone')
glyph.OrientationArray = ['POINTS', 'V']
glyph.ScaleArray = ['POINTS', 'V']
glyph.ScaleFactor = 0.05
""",
    ),
    "code_to_tube": CodeExample(
        code="""
from paraview.simple import *
# create a new tube
tube = Tube(registrationName='Tube1', Input=streamTracer)
tube.Radius = 0.075
""",
    ),
    "code_to_color_tube_glyphs_Temp_variable": CodeExample(
        code="""
from paraview.simple import *
# color tubes and glyphs by Temp variable
ColorBy(tubeDisplay, ('POINTS', 'Temp'))
ColorBy(glyphDisplay, ('POINTS', 'Temp'))
tubeDisplay.RescaleTransferFunctionToDataRange(True)
glyphDisplay.RescaleTransferFunctionToDataRange(True)
""",
    ),
}
