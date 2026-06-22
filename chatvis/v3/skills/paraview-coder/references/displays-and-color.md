# Displays & color

After creating a source/filter, `Show(...)` it, pick a representation, and color
it if asked. Replace `'var0'` with the real array name throughout.

## Contents

- [Showing data & representations](#showing-data--representations)
- [Coloring by an array](#coloring-by-an-array)
- [Transfer functions & presets](#transfer-functions--presets)
- [Volume rendering (atomic)](#volume-rendering-atomic)
- [Scalar bars (legends)](#scalar-bars-legends)
- [Multi-block / block coloring](#multi-block--block-coloring)

## Showing data & representations

Default representation:

```python
display = Show(source, renderView)
```

Surface, wireframe, surface-with-edges, outline, points:

```python
display.Representation = 'Surface'            # or 'Wireframe', 'Surface With Edges',
                                              # 'Outline', 'Points', 'Volume'
display.SetRepresentationType('Surface')      # equivalent setter
```

Contour shown as solid red (no scalar coloring):

```python
contour1Display = Show(contour1, renderView)
contour1Display.ColorArrayName = ['POINTS', '']
contour1Display.DiffuseColor = [1.0, 0.0, 0.0]
```

## Coloring by an array

`ColorBy` selects the array and field association; rescale to the data range and
show the legend.

```python
ColorBy(display, ('POINTS', 'var0'))          # or ('CELLS', ...), ('FIELD', ...)
display.RescaleTransferFunctionToDataRange(True)
display.SetScalarBarVisibility(renderView, True)
```

Color tubes and glyphs together by the same variable:

```python
ColorBy(tubeDisplay, ('POINTS', 'Temp'))
ColorBy(glyphDisplay, ('POINTS', 'Temp'))
tubeDisplay.RescaleTransferFunctionToDataRange(True)
glyphDisplay.RescaleTransferFunctionToDataRange(True)
```

## Transfer functions & presets

Get the color/opacity transfer functions by array name and apply a named preset:

```python
var0LUT = GetColorTransferFunction('var0')
var0LUT.ApplyPreset('Cool to Warm', True)     # or 'Viridis (matplotlib)', etc.
```

Set an explicit color ramp (requires `min`/`max` in scope — see `readers.md`):

```python
var0LUT = GetColorTransferFunction('var0')
var0LUT.RGBPoints = [min, 0.0, 0.0, 0.75,
                     (min + max) / 2.0, 0.75, 0.75, 0.75,
                     max, 0.75, 0.0, 0.0]
```

Opacity ramp:

```python
var0PWF = GetOpacityTransferFunction('var0')
var0PWF.Points = [min, 0.0, 0.5, 0.0,
                  (min + max) / 2.0, 0.5, 0.5, 0.0,
                  max, 1.0, 0.5, 0.0]
```

## Volume rendering (atomic)

Volume rendering must be emitted as a complete unit, in this order:

1. scalar range (`min`/`max`) — see `readers.md`,
2. color transfer function,
3. opacity transfer function,
4. the volume display with **both** `LookupTable` and `ScalarOpacityFunction` set.

Omitting the opacity function or the lookup table renders a solid-black cube.
Keep the array name identical everywhere (range, both transfer functions,
`ColorArrayName`).

```python
ml100vtkDisplay = Show(ml100vtk, renderView)
ml100vtkDisplay.Representation = 'Volume'
ml100vtkDisplay.ColorArrayName = ['POINTS', 'var0']
ml100vtkDisplay.LookupTable = var0LUT
ml100vtkDisplay.ScalarOpacityFunction = var0PWF
```

"Default transfer function" means "use the color/opacity ramps above", not "omit
them".

## Scalar bars (legends)

```python
var0LUTColorBar = GetScalarBar(var0LUT, renderView)
var0LUTColorBar.Title = 'var0'
var0LUTColorBar.ComponentTitle = 'Magnitude'
var0LUTColorBar.Visibility = 1
```

`UpdateScalarBars()` refreshes all bars; `display.SetScalarBarVisibility(view, True)`
toggles one.

## Multi-block / block coloring

For Exodus/IOSS multi-block data you can color, rescale, and legend a specific
block by its selector path:

```python
ColorBlocksBy(display, ['/IOSS/element_blocks/block_2'], ('POINTS', 'ACCL', 'X'))
display.RescaleBlocksTransferFunctionToDataRange(['/IOSS/element_blocks/block_2'], False, True)
blockACCLLUT = GetBlockColorTransferFunction('/IOSS/element_blocks/block_2', 'ACCL')
blockACCLLUT.ApplyPreset('Cool to Warm', True)
display.SetBlocksScalarBarVisibility(renderView, ['/IOSS/element_blocks/block_2'], True)
```

To color by block id (categorical):

```python
ColorBy(display, ('FIELD', 'vtkBlockColors'))
```
