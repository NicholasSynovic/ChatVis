# Filters

Filters transform the output of a reader or another filter. Chain each filter's
`Input=` to the _previous_ stage in the pipeline (e.g. a contour after a slice
takes `Input=slice1`), not always back to the original reader. Replace `'var0'`
with the real scalar array name from the request.

## Contents

- [Slice](#slice)
- [Contour / isosurface](#contour--isosurface)
- [IsoVolume](#isovolume)
- [Clip](#clip)
- [Delaunay 3D](#delaunay-3d)
- [Stream tracer](#stream-tracer)
- [Tube](#tube)
- [Glyph](#glyph)
- [Calculator](#calculator)
- [Cell Data to Point Data](#cell-data-to-point-data)
- [Plot Over Line](#plot-over-line)
- [Temporal Interpolator](#temporal-interpolator)
- [Shrink / Extract Edges](#shrink--extract-edges)
- [Time-series statistics](#time-series-statistics)

## Slice

Use to cut a planar cross-section. Output is polydata.

```python
slice1 = Slice(registrationName='Slice1', Input=ml100vtk)
slice1.SliceType = 'Plane'
slice1.HyperTreeGridSlicer = 'Plane'
slice1.SliceOffsetValues = [0.0]
slice1.PointMergeMethod = 'Uniform Binning'
```

## Contour / isosurface

Use to compute isolines/isosurfaces from a point-centered scalar. Use the
isosurface value from the request verbatim; if none is given, derive it from
`(min + max) / 2` (see data inspection in `readers.md`). **Replace `'var0'`** with
the real array name — a leftover `'var0'` logs `Contour array is null` and renders
nothing. When the contour follows another filter, set `Input=` to that filter.

```python
contour1 = Contour(registrationName='Contour1', Input=ml100vtk)
contour1.ContourBy = ['POINTS', 'var0']
contour1.Isosurfaces = [0.5]
contour1.PointMergeMethod = 'Uniform Binning'
```

If the user named no array, inspect first and use the real name:

```python
ml100vtk.UpdatePipeline()
array_name = ml100vtk.PointData.GetArray(0).GetName()
contour1.ContourBy = ['POINTS', array_name]
```

## IsoVolume

Use to extract the region where a scalar falls within a threshold range
(a "filled" isosurface rather than a shell).

```python
isoVolume1 = IsoVolume(registrationName='IsoVolume1', Input=predictionvtr)
isoVolume1.InputScalars = ['POINTS', 'Intensity']
isoVolume1.ThresholdRange = [0.2, 1.0]
```

## Clip

Use to cut away part of the dataset with an implicit plane. Output is an
unstructured grid. Configure `Origin`/`Normal` to choose the kept side — **do not
rely on `InsideOut`**.

```python
clip = Clip(registrationName='Clip', Input=delaunay3D)
clip.ClipType = 'Plane'
clip.ClipType.Origin = [0.0, 0.0, 0.0]
clip.ClipType.Normal = [1.0, 0.0, 0.0]
```

## Delaunay 3D

Use to build a 3D Delaunay triangulation (unstructured grid) from a point set —
e.g. to give a points-only dataset a surface to clip or display.

```python
delaunay3D = Delaunay3D(registrationName='Delaunay3D', Input=points)
```

## Stream tracer

Use to trace streamlines through a vector field from a seed. Set `Vectors` to
the vector array on the input; tune seed `Center`/`Radius` from the dataset
bounds (see `readers.md`).

```python
streamTracer = StreamTracer(
    registrationName='StreamTracer1',
    Input=velocity,
    SeedType='Point Cloud',
)
streamTracer.Vectors = ['POINTS', 'V']
streamTracer.MaximumStreamlineLength = 20.0
streamTracer.SeedType.Center = [0.0, 0.0, 0.0]
streamTracer.SeedType.Radius = 2.0
```

## Tube

Use to thicken streamlines (or any polylines) into renderable tubes.

```python
tube = Tube(registrationName='Tube1', Input=streamTracer)
tube.Scalars = ['POINTS', 'AngularVelocity']
tube.Vectors = ['POINTS', 'Normals']
tube.Radius = 0.075
```

## Glyph

Use to place oriented/scaled glyphs (cones, arrows, etc.) at points — e.g. to
show flow direction along streamlines. Orient and scale by a vector array.

```python
glyph = Glyph(registrationName='Glyph1', Input=streamTracer, GlyphType='Cone')
glyph.OrientationArray = ['POINTS', 'V']
glyph.ScaleArray = ['POINTS', 'V']
glyph.ScaleFactor = 0.05
glyph.GlyphTransform = 'Transform2'
```

Tuning the cone shape (optional):

```python
glyph.GlyphType.Resolution = 10
glyph.GlyphType.Radius = 0.15
glyph.GlyphType.Height = 0.5
```

## Calculator

Use to compute a derived field from existing arrays via an expression. Reference
components as `velocity_X`, coordinates as `coordsX`, and build vectors with
`iHat`/`jHat`/`kHat`.

```python
calculator1 = Calculator(registrationName='Calculator1', Input=mpasvtp)
calculator1.Function = '(-velocity_X*sin(coordsX*0.0174533) + velocity_Y*cos(coordsX*0.0174533)) * iHat + 0*jHat + 0*kHat'
```

## Cell Data to Point Data

Use when a filter needs point-centered data but the arrays are cell-centered
(e.g. before contouring cell data). Averages surrounding cell values onto points.

```python
cellToPoint = CellDatatoPointData(registrationName='CellDatatoPointData1', Input=reader)
cellToPoint.CellDataArraytoprocess = ['Intensity', 'Phase']
```

## Plot Over Line

Use to sample point-centered variables along a line for an XY plot or CSV export.

```python
plotOverLine1 = PlotOverLine(registrationName='PlotOverLine1', Input=wavelet1)
plotOverLine1.Point1 = [0, 0, 0]
plotOverLine1.Point2 = [0, 0, 10]
```

Display it in a chart view (see `layout-and-views.md`) or write it to CSV:

```python
writer = CreateWriter('<output_path>', plotOverLine1)  # e.g. line-plot.csv
writer.UpdatePipeline()
```

## Temporal Interpolator

Use to interpolate a time-varying dataset between timesteps (e.g. for smoother
animations or side-by-side comparison with the raw data).

```python
temporalInterpolator = TemporalInterpolator(Input=data)
```

## Shrink / Extract Edges

`Shrink` pulls each cell toward its centroid (factor in `[0, 1]`); `ExtractEdges`
produces a wireframe of the input.

```python
shrink = Shrink(Input=sphere)
shrink.ShrinkFactor = 0.5
wireframe = ExtractEdges(Input=sphere)
```

## Time-series statistics

Use to compute statistics across timesteps. Iterate timesteps by calling
`UpdatePipeline(t)` and fetching the data; `print()` the results so they appear
in stdout.

```python
import numpy as np
from vtkmodules.numpy_interface import dataset_adapter as dsa

timesteps = data.TimestepValues
sum_all = 0.0
num_all = 0
for t in timesteps:
    data.UpdatePipeline(t)
    mb = dsa.WrapDataObject(FetchData(data)[0])
    eqps = mb.CellData['EQPS'].GetArrays()[0]
    sum_all += np.sum(eqps)
    num_all += eqps.GetNumberOfTuples()
mean_all = sum_all / num_all
print('Average EQPS over all time steps:', mean_all)
```
