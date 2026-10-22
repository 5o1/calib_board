# Camera calibration

All commands run from the repository root after activating `.venv`.

## Intrinsics

### Capture

Use the accepted printed board. Keep resolution, optical zoom, and focus fixed
at the settings you will use for data collection. Disable autofocus after
focusing at the working distance. Capture roughly 15–30 sharp views with the
board at varied distances and tilts. Cover the center, image edges, and corners;
allowing partial views is useful if at least six non-collinear corners remain.
Do not use only fronto-parallel views or repeated photographs of one pose.

The ten-view default is an input count requirement, not a guarantee of adequate
pose diversity or accuracy. `--min-views` can change it, with an absolute minimum
of three. Small datasets are suitable for software checks, not precision claims.

### Solve

```bash
python -m calib_board.intrinsics captures/intrinsics \
  --output build/intrinsics.json --overlay-dir build/intrinsics_overlays

# Explicit files or a quoted glob are also accepted.
python -m calib_board.intrinsics 'captures/intrinsics/*.png' \
  --output build/intrinsics.yaml
```

Directories include immediate image files, sorted by name; they are not scanned
recursively. Supported directory extensions: PNG, JPG/JPEG, BMP, TIF/TIFF. Do not
put overlays or unrelated photos in the capture directory. Duplicate paths,
unreadable files, and mixed image resolutions are errors. Insufficient or
collinear detections are reported as skipped, including filenames and reasons;
if too few usable views remain, no calibration is written. The solver does not
remove points or views based on fitted error.

Detection uses `CharucoDetector` without K/D, `minMarkers=2`, marker refinement
`CORNER_REFINE_NONE`, and `tryRefineMarkers=False`. OpenCV internally refines
ChArUco corners. Correspondences are passed to `calibrateCameraExtended` with
flags=0: a pinhole camera with `D=[k1,k2,p1,p2,k3]`. This does not implement a
fisheye model or estimate a rational eight-coefficient model.

### Output and validation

The JSON/YAML includes:

- `width`, `height`, `K` (3 × 3), `D`, and `distortion_model=plumb_bob`, directly
  consumable by this repository's detection and extrinsic tools.
- Aggregate RMS, median, and P95 reprojection error in pixels; each used view's
  RMS/median/P95, corner count, and IDs.
- Total input/used counts, skipped-image reasons, and normalized corner bounds.
- OpenCV's intrinsic standard deviations with an explicit coefficient order.

Inspect overlays and individual view errors. Corner bounds describe the detected
extent only; they do not prove uniform coverage or tilt diversity. A low fitting
error alone does not establish correct intrinsics. To validate separately,
capture unused views at new poses, run `calib_board.detect` using the fitted
intrinsics, and inspect their residuals. Compare K/D from two independently
captured, diverse datasets. These checks test repeatability and generalization;
physical accuracy still needs an independent geometric reference.

Existing parameters can be loaded from K/D JSON/YAML or ROS `camera_info` with
`camera_matrix.data` and `distortion_coefficients.data`. The detector also accepts
`rational_polynomial` parameters from an external calibration. Fisheye/equidistant
inputs are rejected. Intrinsics are never automatically rescaled.

## Extrinsics

### Frames and placement measurements

The result is a fixed camera's pose in a chosen world frame. `T_A_B` maps B-frame
points into A. The camera uses ROS optical axes: X right, Y down, Z forward.
There is no automatic optical-to-camera_link rotation.

For a standalone tabletop world, set the origin at the intersection of the back
and left table edges: X goes from back to front, Y left to right, Z up; table
surface Z=0. A face-up board's Z points down. If connecting to an existing world,
measure the back-left table corner in that frame and set `world_back_left_m`.
Its axes must follow the same table directions; for a rotated world frame,
supply a full `T_world_board` instead of an origin offset alone.
Table height, camera height, and the world origin are separate quantities.

For each placement, measure the **centers** of two distinct labeled holes to the
back and left table edges, then measure the printed surface height above the
table. Do not use the paper corners or hole rims. Example only:

```json
{
  "hole_measurements": [
    {"id": "H1", "from_back_edge_mm": 100, "from_left_edge_mm": 200},
    {"id": "H2", "from_back_edge_mm": 500, "from_left_edge_mm": 200}
  ],
  "board_surface_above_table_mm": 5,
  "world_back_left_m": [0, 0, 0],
  "distance_tolerance_mm": 2
}
```

See [placement_holes.json](../examples/placement_holes.json). The default 2 mm
hole-distance consistency tolerance catches inconsistent input; it is not a
measurement-accuracy certificate. Two holes assume a flat, horizontal board;
they cannot observe tilt, warping, or a non-horizontal table. For tilted or
vertical boards, supply a separately measured full transform:

```json
{"T_world_board": [[1,0,0,0], [0,-1,0,0], [0,0,-1,0.005], [0,0,0,1]]}
```

Translations in full transforms are **meters**, and rotations must be proper
right-handed rotations. This example describes a face-up board; it is not a
measurement for your setup.

For hole measurements, the solver forms world XY positions from the two edge
distances and adds the back-left world offset. With db the board-plane hole
baseline and dw the world-plane baseline, theta=atan2(dw.y,dw.x)+atan2(db.y,db.x).
The rotation columns are (cos(theta),sin(theta),0), (sin(theta),−cos(theta),0), and
(0,0,−1). Translation is the mean of `p_world - R @ p_board` for the two holes.

### Capture and manifest

Keep the camera, focus, and resolution fixed. Any number of placements is
accepted, including a single image. Three or more separated locations, for example
center/left/right, are recommended. Measure **each** placement.
Never reuse an earlier measurement for a board that has moved. Use meaningful
spatial separation; numeric distinctness alone does not guarantee good geometry.

Create a JSON or YAML manifest like [the example](../examples/extrinsics_manifest.json):

```json
{
  "intrinsics": "../intrinsics.json",
  "observations": [
    {"image": "center.png", "placement": "center_placement.json"},
    {"image": "left.png", "placement": "left_placement.json"},
    {"image": "right.png", "placement": "right_placement.json"}
  ]
}
```

Image, placement, and manifest-intrinsics paths are relative to the manifest.
An explicit `--intrinsics` override is relative to the working directory.

```bash
python -m calib_board.calibrate_extrinsics captures/extrinsics/manifest.json \
  --intrinsics build/intrinsics.json --output build/extrinsics.yaml \
  --diagnostics-dir build/extrinsics_views
```

This command detects each image, maps its board corners through the matching
`T_world_board`, and jointly fits all world/image points using `solvePnP`
ITERATIVE followed by `solvePnPRefineLM`. All corners have equal weight; there is
no outlier rejection or averaging of per-image poses. Resolution and K/D must
match. No failed image is silently skipped.

Any number of distinct measured transforms is accepted. With one placement the
result is `single_position`; with fewer than three it carries
`below_recommended_placements: true`, a warning is printed, and leave-one-out
uncertainty is unavailable for a single image. Two transforms count as equal when all matrix entries agree within 1e-6 (zero
relative tolerance). Repeated image paths are rejected by the photo entry point.
This checks the supplied data; it cannot establish that the camera was fixed or
that the measurements describe the physical placements correctly.

### Output

`T_world_camera_optical` maps optical-frame coordinates to world coordinates.
`pose_xyz_qw_qx_qy_qz` is `[x,y,z,qw,qx,qy,qz]`, with meters, a unit quaternion,
and qw >= 0. The output records `calibration_mode`, distinct placement count,
reprojection median/P95, and leave-one-image-out jackknife standard deviations.
The photo entry point also records the supplied placement transforms and image
sources. `physical_accuracy_verified` remains false: passing input checks does
not validate real-world accuracy.

For one image, `T_world_camera_optical = T_world_board @ inv(T_camera_optical_board)`.
Joint fitting uses all corners instead of averaging this expression across views.
Jackknife uncertainty measures sensitivity to removing whole images; it excludes
intrinsic, print, flatness, and placement systematic errors. A single image has
null jackknife standard deviations.

### Detection files and quick checks

The lower-level interface remains available for inspecting detections or reusing
saved observations:

```bash
python -m calib_board.detect center.png --intrinsics build/intrinsics.json \
  --output build/center_detection.json --overlay build/center_overlay.png

python -m calib_board.extrinsics build/center_detection.json build/left_detection.json build/right_detection.json \
  --placements center_placement.json left_placement.json right_placement.json \
  --output build/extrinsics.json

# A single placement is accepted (warning: below the recommended three).
python -m calib_board.extrinsics build/center_detection.json \
  --placement center_placement.json --output build/single.json
```

`--quick-check` is kept for compatibility; it only labels the result
`quick_check`. The shared `--placement` interface no longer requires it. A result
from fewer than three placements depends more on the measured placement(s) and
should be reported with that limitation.

## Gray patches

```bash
python -m calib_board.gray_ramp center.png \
  --detection build/center_detection.json --output build/gray.json
```

The tool projects a 20 × 20 grid into the central 60% of each patch, samples RGB
bilinearly, and marks out-of-frame patches unavailable. It checks brightness
ordering, highlights >=250, shadows <=5, and a code-value line-fit residual.
Unclipped middle patches estimate green-reference gains `[G/R,1,G/B]`.

This assumes unobstructed patches and reasonably uniform illumination. Printing,
light, and camera response all affect the values. It is approximate exposure and
white-balance diagnosis, not measured reflectance, proof of radiometric linearity,
or full color correction.

## When to recalibrate

Change of focus, zoom, lens, image crop, or resolution can change intrinsics.
Moving an otherwise unchanged camera changes world extrinsics; it does not by
itself require refitting intrinsics. Re-estimate extrinsics after camera movement,
and intrinsics after relevant imaging settings change.
