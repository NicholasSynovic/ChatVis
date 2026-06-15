"""Example code snippets used for code generation and improvement"""

from enum import StrEnum


class CodeSnippet(StrEnum):
    READ = """
from paraview.simple import *
# read the input data
ml100vtk = LegacyVTKReader(FileNames=<input_path>)
"""

    SLICE = """
from paraview.simple import *
# create a new slice
slice1 = Slice(registrationName='Slice1', Input=ml100vtk)
slice1.SliceType = 'Plane'
slice1.HyperTreeGridSlicer = 'Plane'
slice1.SliceOffsetValues = [0.0]
slice1.PointMergeMethod = 'Uniform Binning'
"""

    CONTOUR = """
from paraview.simple import *
# create a new contour
contour1 = Contour(registrationName='Contour1', Input=ml100vtk)
contour1.ContourBy = ['POINTS', 'var0']
contour1.Isosurfaces = [0.5]
contour1.PointMergeMethod = 'Uniform Binning'
"""

    CLIP = """
from paraview.simple import *
# create a new clip filter
clip = Clip(registrationName='Clip', Input=delaunay3D)
clip.ClipType = 'Plane'
clip.ClipType.Origin = [0.0, 0.0, 0.0]
clip.ClipType.Normal = [1.0, 0.0, 0.0]
"""

    COLOR_TRANSFER_FUNCTION = """
from paraview.simple import *
# get color transfer function/color map for 'var0'
var0LUT = GetColorTransferFunction('var0')
var0LUT.RGBPoints = [min, 0.0, 0.0, 0.75, (min + max) / 2.0, 0.75, 0.75, 0.75, max, 0.75, 0.0, 0.0]
"""

    OPACITY_TRANSFER_FUNCTION = """
from paraview.simple import *
# get opacity transfer function/opacity map for 'var0'
var0PWF = GetOpacityTransferFunction('var0')
var0PWF.Points = [min, 0.0, 0.5, 0.0, (min + max) / 2.0, 0.5, 0.5, 0.0, max, 1.0, 0.5, 0.0]
"""

    CREATE_LAYOUT = """
from paraview.simple import *
# create new layout object
layout = CreateLayout(name='Layout')
layout.AssignView(0, renderView)
"""

    CONTOUR1_DISPLAY = """
from paraview.simple import *
# show data
contour1Display = Show(contour1, renderView)
contour1Display.ColorArrayName = ['POINTS', '']
contour1Display.DiffuseColor = [1.0, 0.0, 0.0]
"""

    RENDER_VIEW = """
from paraview.simple import *
# create view
renderView = CreateView('RenderView')
renderView.ViewSize = [1920, 1080]
"""

    RENDER_VIEW_DIRECTION = """
from paraview.simple import *
# set render view direction
renderView.ResetActiveCameraToPositiveX()
renderView.ResetCamera()
"""

    ISOMETRIC_VIEW = """
from paraview.simple import *
# set render view direction
renderView.ApplyIsometricView()
renderView.ResetCamera()
"""

    SAVE = """
from paraview.simple import *
# Save a screenshot of the render view
SaveScreenshot(
    '<output_path>',
    renderView,
    ImageResolution=[1920, 1080],
    OverrideColorPalette='WhiteBackground',
)
"""

    STREAM_TRACER = """
from paraview.simple import *
# create a new stream tacer
streamTracer = StreamTracer(
    registrationName='StreamTracer1',
    Input=velocity,
    SeedType='Point Cloud',
)
"""

    GLYPH = """
from paraview.simple import *
# create a new glyph
glyph = Glyph(registrationName='Glyph1', Input=streamTracer, GlyphType='Cone')
glyph.OrientationArray = ['POINTS', 'V']
glyph.ScaleArray = ['POINTS', 'V']
glyph.ScaleFactor = 0.05
"""

    TUBE = """
from paraview.simple import *
# create a new tube
tube = Tube(registrationName='Tube1', Input=streamTracer)
tube.Radius = 0.075
"""

    COLOR_TUBE_GLYPHS_TEMP_VARIABLE = """
from paraview.simple import *
# color tubes and glyphs by Temp variable
ColorBy(tubeDisplay, ('POINTS', 'Temp'))
ColorBy(glyphDisplay, ('POINTS', 'Temp'))
tubeDisplay.RescaleTransferFunctionToDataRange(True)
glyphDisplay.RescaleTransferFunctionToDataRange(True)
"""
