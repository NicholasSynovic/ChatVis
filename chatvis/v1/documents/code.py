"""Example code snippets used for code generation and improvement"""

from enum import StrEnum


class CodeSnippet(StrEnum):
    READ = """
from paraview.simple import *
# read a VTK (.vtk) input file
ml100vtk = LegacyVTKReader(registrationName='input', FileNames=['<input_path>'])
"""

    READ_IOSS = """
from paraview.simple import *
# read an Exodus / IOSS (.ex2) input file
reader = IOSSReader(registrationName='input', FileName=['<input_path>'])
"""

    DATA_RANGE = """
from paraview.simple import *
# get the min/max of the first point-data array on the reader.
# Required ONLY before configuring transfer functions that reference
# `min` and `max` as locals (e.g. volume rendering). Reference the
# reader explicitly (do not rely on `GetActiveSource()`, which is unreliable
# under pvpython) and call `UpdatePipeline()` first so the data
# information is populated.
ml100vtk.UpdatePipeline()
pd = ml100vtk.PointData
min, max = pd.GetArray(0).GetRange()
"""

    DATA_BOUNDS = """
from paraview.simple import *
# get the spatial bounds of the dataset.
# Call UpdatePipeline() first so the bounds are populated.
reader.UpdatePipeline()
bounds = reader.GetDataInformation().GetBounds()
length = [bounds[1] - bounds[0], bounds[3] - bounds[2], bounds[5] - bounds[4]]
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
# create a new contour.
# Use the isosurface value from the user prompt verbatim; if the user does
# not specify one, derive the isosurface from `(min + max) / 2` or from the
# DATA_RANGE snippet.
contour1 = Contour(registrationName='Contour1', Input=ml100vtk)
contour1.ContourBy = ['POINTS', 'var0']
contour1.Isosurfaces = [0.5]
contour1.PointMergeMethod = 'Uniform Binning'
"""

    DELAUNAY3D = """
from paraview.simple import *
# create a 3D Delaunay triangulation
delaunay3D = Delaunay3D(registrationName='Delaunay3D', Input=points)
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
# get color transfer function/color map for 'var0'.
# `min` and `max` must be in scope (see DATA_RANGE snippet).
var0LUT = GetColorTransferFunction('var0')
var0LUT.RGBPoints = [min, 0.0, 0.0, 0.75, (min + max) / 2.0, 0.75, 0.75, 0.75, max, 0.75, 0.0, 0.0]
"""

    OPACITY_TRANSFER_FUNCTION = """
from paraview.simple import *
# get opacity transfer function/opacity map for 'var0'.
# `min` and `max` must be in scope (see DATA_RANGE snippet).
var0PWF = GetOpacityTransferFunction('var0')
var0PWF.Points = [min, 0.0, 0.5, 0.0, (min + max) / 2.0, 0.5, 0.5, 0.0, max, 1.0, 0.5, 0.0]
"""

    CREATE_LAYOUT = """
from paraview.simple import *
# create new layout object
layout = CreateLayout(name='Layout')
layout.AssignView(0, renderView)
"""

    DEFAULT_DISPLAY = """
from paraview.simple import *
# show data with the default representation
display = Show(source, renderView)
"""

    CONTOUR_RED_DISPLAY = """
from paraview.simple import *
# show a contour and color it solid red
contour1Display = Show(contour1, renderView)
contour1Display.ColorArrayName = ['POINTS', '']
contour1Display.DiffuseColor = [1.0, 0.0, 0.0]
"""

    WIREFRAME_DISPLAY = """
from paraview.simple import *
# show data as a wireframe
clipDisplay = Show(clip, renderView)
clipDisplay.Representation = 'Wireframe'
"""

    VOLUME_DISPLAY = """
from paraview.simple import *
# show data as a volume rendering using the configured transfer functions
ml100vtkDisplay = Show(ml100vtk, renderView)
ml100vtkDisplay.Representation = 'Volume'
ml100vtkDisplay.ColorArrayName = ['POINTS', 'var0']
ml100vtkDisplay.LookupTable = var0LUT
ml100vtkDisplay.ScalarOpacityFunction = var0PWF
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
renderView.ResetCamera()
renderView.ResetActiveCameraToPositiveX()
"""

    ISOMETRIC_VIEW = """
from paraview.simple import *
# set render view direction
renderView.ApplyIsometricView()
renderView.ResetCamera()
"""

    CAMERA_POSITION = """
from paraview.simple import *
# place the camera explicitly when ResetCamera / ApplyIsometricView are not
# enough. Useful when the camera should be derived from `bounds`/`length`
# (see DATA_BOUNDS snippet).
renderView.CameraPosition = [3.86, 3.86, 3.86]
renderView.CameraFocalPoint = [0.0, 0.0, 0.0]
renderView.CameraViewUp = [-0.408, 0.816, -0.408]
"""

    SAVE = """
from paraview.simple import *
# Save a screenshot of the render view
Render()
SaveScreenshot(
    '<output_path>',
    renderView,
    ImageResolution=[1920, 1080],
)
"""

    STREAM_TRACER = """
from paraview.simple import *
# create a new stream tracer with a Point Cloud seed.
# Set Vectors to the vector array on the input and tune seed Center/Radius
# from the dataset bounds (see DATA_BOUNDS snippet).
streamTracer = StreamTracer(
    registrationName='StreamTracer1',
    Input=velocity,
    SeedType='Point Cloud',
)
streamTracer.Vectors = ['POINTS', 'V']
streamTracer.MaximumStreamlineLength = 20.0
streamTracer.SeedType.Center = [0.0, 0.0, 0.0]
streamTracer.SeedType.Radius = 2.0
"""

    GLYPH = """
from paraview.simple import *
# create a new glyph
glyph = Glyph(registrationName='Glyph1', Input=streamTracer, GlyphType='Cone')
glyph.OrientationArray = ['POINTS', 'V']
glyph.ScaleArray = ['POINTS', 'V']
glyph.ScaleFactor = 0.05
glyph.GlyphTransform = 'Transform2'
"""

    TUBE = """
from paraview.simple import *
# create a new tube around streamlines
tube = Tube(registrationName='Tube1', Input=streamTracer)
tube.Scalars = ['POINTS', 'AngularVelocity']
tube.Vectors = ['POINTS', 'Normals']
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
