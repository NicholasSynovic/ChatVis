# Output

How the script writes its result to disk. Most requests want a screenshot; some
want exported data, an animation, or a 3D scene. Substitute `<output_path>` with
the path the user named (or a sensible default like `screenshot.png`).

## Contents

- [Save a screenshot](#save-a-screenshot)
- [Save data](#save-data)
- [Save an animation](#save-an-animation)
- [Export / import a scene](#export--import-a-scene)

## Save a screenshot

The usual final step. `Render()` first, then `SaveScreenshot`. This must come
_after_ the camera-framing call (see `rendering-and-camera.md`) or the image will
be blank.

```python
Render()
SaveScreenshot(
    '<output_path>',
    renderView,
    ImageResolution=[1920, 1080],
)
```

Save a multi-view layout (for side-by-side comparisons) by passing the layout
instead of a single view:

```python
SaveScreenshot('<output_path>', layout1, ImageResolution=[1800, 1400])
```

Force a white background in the saved image:

```python
SaveScreenshot('<output_path>', renderView, OverrideColorPalette='WhiteBackground')
```

## Save data

Write filtered geometry to a file. Format is inferred from the extension
(`.csv`, `.ply`, `.vtm`, etc.).

```python
SaveData('<output_path>', proxy=contour1)              # e.g. contour.ply / .vtm
SaveData('<output_path>', proxy=contour1, EnableColoring=1)   # PLY with color
```

Time-series subset to a `.vtm` file series:

```python
SaveData('<output_path>', proxy=slice1,
         Writetimestepsasfileseries=1,
         Firsttimestep=10, Lasttimestep=20, Timestepstride=3,
         Filenamesuffix='_%d')
```

## Save an animation

For time-varying data, advance the animation and write a movie.

```python
animationScene = GetAnimationScene()
animationScene.UpdateAnimationUsingDataTimeSteps()
SaveAnimation('<output_path>', layout1)                # e.g. movie.avi
```

## Export / import a scene

Export the current render view as a 3D scene (e.g. GLTF):

```python
ExportView('<output_path>', view=renderView1)          # e.g. scene.gltf
```

Import a GLTF/GLB scene into a view:

```python
ImportView('<input_path>', view=renderView1)
```
