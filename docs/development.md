# Development

## Environment

The existing environment uses Python 3.14.7 and the exact versions in
[requirements.lock.txt](../requirements.lock.txt). The direct dependencies are in
[requirements.txt](../requirements.txt). Other Python versions/platforms are not
yet validated. Use an isolated environment and avoid installing multiple
competing OpenCV wheels in it.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock.txt
python -m pip check
python -m pytest -q
```

Tests use temporary directories for new calibration fixtures and write historical
synthetic acceptance images/metrics under ignored `build/` paths. They do not
contact a camera, robot, or remote machine.

## Modules

| Module | Role |
| --- | --- |
| `calib_board.placement_planner` | Local static form and SVG planner for four hole centers |
| `calib_board.generate` | Deterministic vector PDF and 300 DPI preview |
| `calib_board.intrinsics` | Image collection, ChArUco detection without prior K/D, pinhole intrinsic solve |
| `calib_board.detect` | Known-intrinsic board pose and corner overlay |
| `calib_board.calibrate_extrinsics` | Photo/placement manifest to joint world camera pose |
| `calib_board.extrinsics` | Placement math, joint PnP, low-level detection-file CLI, diagnostic legacy averaging |
| `calib_board.gray_ramp` | Approximate gray-patch white-balance/exposure checks |
| `calib_board.synthetic` | PDF rendering, synthetic poses, cell sampling calculations |
| `examples.make_synthetic_dataset` | Reproducible dataset for trying both solvers without hardware |

## Regeneration and versions

```bash
python -m calib_board.generate --spec spec/board_v1_1.json --output build/board_v1_1_A3.pdf
```

All generated PDFs, previews, captures, and results under `build/` are ignored.
Distribute printable board artifacts through [GitHub Releases](https://github.com/5o1/calib_board/releases). The specification is authoritative for layout. Change its
version when printed labels or geometry change, regenerate the PDF, and run tests.
Version 1.1.1 changes labels only. Old board prints retain their original
version; detect them with the matching archived specification. Saved detection
ID/version checks are intentionally strict.

The raw numerical solver functions permit diagnostic observations; the two
extrinsic command-line entry points enforce the three-distinct-placement
acquisition policy unless `--quick-check` is supplied. Automated input checks
cannot certify that a measured transform is physically correct.

## Synthetic example

```bash
python -m examples.make_synthetic_dataset --output build/demo
python -m calib_board.intrinsics build/demo/intrinsics --output build/demo/estimated_intrinsics.json
python -m calib_board.calibrate_extrinsics build/demo/manifest.json \
  --intrinsics build/demo/estimated_intrinsics.json --output build/demo/estimated_extrinsics.json
```

`build/demo/truth.json` contains K/D, the world camera transform, and the noise seed.
The renderer uses a pinhole camera with zero distortion, PDF rasterization,
light blur, and deterministic noise. A separate test remaps rendered images to exercise nonzero
distortion. Neither constitutes physical validation.

## Placement planner checks

```bash
node --test tests/test_placement_geometry.cjs
```

These checks use Node.js 18+ and require no npm dependencies. The planner itself
uses browser APIs and a Python standard-library launcher. See the
[planner guide](placement-planner.md) for its coordinate and export contract.
