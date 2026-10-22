# Station Calibration Board

An A3 printable ChArUco board and Python tools for camera intrinsic calibration,
world-frame extrinsic calibration, and basic exposure and white-balance checks.

[Download the printable PDF](https://github.com/5o1/calib_board/releases/download/v1.1.1/board_v1_1_A3.pdf) ·
[Printing and board specification](docs/board.md) ·
[Calibration guide](docs/calibration.md)

The board combines a 6 × 5 ChArUco pattern, eight nominal gray patches, a slot for
an actual ColorChecker Classic Mini, measurement rulers, and mounting marks.
It works independently of any robot software.

**Status: experimental.** Software has synthetic validation; physical printing
and real-camera accuracy have not been validated. See [validation](docs/validation.md).
The current English board is v1.1.1, with the same calibration geometry as v1.1.0.

## Install

Run commands from the repository root. The recorded development environment uses
Python 3.14.7; other Python versions and platforms have not been validated.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock.txt
python -m pip check
```

## Print the board

Print the [PDF](https://github.com/5o1/calib_board/releases/download/v1.1.1/board_v1_1_A3.pdf) on **A3 landscape at 100% actual size**.
Disable “fit to page”, measure both 100 mm rulers, and mount the sheet flat on a
rigid backing. Follow the [print acceptance checklist](docs/board.md#print-acceptance)
before using nominal dimensions for calibration.

To regenerate the vector PDF and its 300 DPI preview:

```bash
python -m calib_board.generate
```

## Plan board placements

Open a standalone visual form for four measured mounting-hole centers:

```bash
python -m calib_board.placement_planner
```

The browser shows a configurable tabletop, schematic camera direction, colored
candidate positions, and four edge-distance dimensions for each rotated board.
Drafts stay in the browser; export/import JSON to keep them, or export the diagram
as SVG. The launcher uses only the Python standard library. See the
[placement planner guide](docs/placement-planner.md) for coordinates and usage.

## Calibrate intrinsics

Capture 15–30 sharp views at the intended resolution and focus setting. Move and
tilt the board to cover the image center, edges, and corners. The solver requires
at least ten usable views by default and does not need existing intrinsics.

```bash
python -m calib_board.intrinsics captures/intrinsics \
  --output build/intrinsics.json --overlay-dir build/intrinsics_overlays
```

The output contains `K`, five distortion coefficients `D`, image size, detected
view counts, and reprojection diagnostics. JSON and YAML output are supported.
See [capture guidance and output interpretation](docs/calibration.md#intrinsics).

## Calibrate extrinsics

Keep the camera fixed and photograph the board in one or more measured
placements. A single image is accepted; three or more distinct placements are
recommended because they reduce the dependence on any one placement measurement
and enable leave-one-out uncertainty. Pair each photograph with its own placement
measurement in an [observation manifest](examples/extrinsics_manifest.json).

```bash
python -m calib_board.calibrate_extrinsics captures/extrinsics/manifest.json \
  --intrinsics build/intrinsics.json --output build/extrinsics.json \
  --diagnostics-dir build/extrinsics_views
```

The solver jointly fits all world/image corner correspondences and outputs
`T_world_camera_optical` and `[x, y, z, qw, qx, qy, qz]`, with translation in meters.
Each placement can use two measured hole centers on a flat table or a full
`T_world_board` transform. See [placement measurements and frames](docs/calibration.md#extrinsics).
With fewer than three distinct placements the solver still writes the result,
prints a warning and sets `below_recommended_placements: true`.

## Try without a camera

Generate a reproducible synthetic dataset and run both solvers:

```bash
python -m examples.make_synthetic_dataset --output build/demo
python -m calib_board.intrinsics build/demo/intrinsics --output build/demo/estimated_intrinsics.json
python -m calib_board.calibrate_extrinsics build/demo/manifest.json \
  --intrinsics build/demo/estimated_intrinsics.json --output build/demo/estimated_extrinsics.json
```

The dataset includes known camera parameters and world pose for comparison.
It exercises the software, not physical calibration accuracy.

## Documentation

- [Board dimensions, printing, mounting, and working distance](docs/board.md)
- [Capture, intrinsics, extrinsics, and gray-patch analysis](docs/calibration.md)
- [Validation evidence and practical limits](docs/validation.md)
- [Development and tests](docs/development.md)
- [Technical references](docs/research.md)
- [Historical design and acceptance records](docs/archive/README.md)

## License

[MIT](LICENSE). The ColorChecker outline is a mounting placeholder; its proprietary
color patches are not reproduced in this project.
