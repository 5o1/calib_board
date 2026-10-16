# Validation and limits

## Scope of evidence

This project is experimental. Physical print acceptance, real-camera intrinsic
calibration, and real-camera world-pose accuracy have not been validated here.
Synthetic results test software behavior under the implemented image model;
they do not validate paper, printer, board flatness, lens modeling, focus, or
placement measurements.

The current validation run is recorded in [current-validation.txt](current-validation.txt).
It covers the test suite, a generated-photo intrinsic/extrinsic workflow, and
camera-parameter/world-pose comparison. Run details and tolerances belong in
this document and the tests, not on the project front page.

## Current end-to-end example

The documented example used all 18 intrinsic images with RMS 0.112331 px. The
largest focal-length relative error against its synthetic truth was 0.199134%,
and principal-point errors were +0.482756 / -0.097081 px. Using these estimated
intrinsics for the three-position photo solver gave 1.583273 mm translation
error, 0.042653 degrees rotation error, and 0.097151 px median reprojection error.
See [machine-readable results](current-demo-results.json). These numbers describe
one synthetic dataset, not general accuracy bounds.

The nonzero-distortion fixture initially failed a fixed 5 px projected-ray check
with captures concentrated in the image center (7.721878 px). A calibrated
redetection control gave 8.905555 px and was not retained. Expanding only the XY
capture offsets, with the same view count, pose schedule, noise seeds, distortion
model, and solver, passed at 3.190995 px. This supports insufficient coverage and
extrapolation as contributors; it does not isolate all localization biases.
The threshold was unchanged. See the [experiment record](intrinsic-coverage-experiment.json).

## Historical geometry evidence

The original 1.1.0 report recorded 31 passing tests. In three synthetic
center/left/right joint solves, the largest camera translation error was
0.632033178 mm and rotation error 0.051480161 degrees. The maximum joint
reprojection median was 0.095301425 px. These values belong to those specific
fixed-seed cases and camera parameters, not a general performance guarantee.

Single-view main-camera results had translation error up to 3.850021859 mm and
rotation error up to 0.223988013 degrees. The old workspace projection threshold
failed in all eight main-camera views. A later acceptance decision made that
metric informational and used multi-position pose error and reprojection
thresholds instead. The underlying failures were not turned into successes.

Original values and criteria are preserved in the
[historical report](archive/legacy/docs/v1_1/review5/report.md),
[single-view values](archive/legacy/docs/v1_1/review5/single-results.json), and
[joint values](archive/legacy/docs/v1_1/review5/joint-results.json).
Version 1.1.1 keeps the calibration geometry but changes printed English labels;
current tests exercise its regenerated PDF separately. Historical hashes do not
identify the new source or PDF.

## Current checks

The test suite checks vector PDF dimensions and functional geometry, deterministic
regeneration, hole-based placement math, quaternion conventions, synthetic
single-view detection and multi-position pose recovery, intrinsic parameter
recovery from images with known distortion, and command-line workflows.
Input tests cover missing detections, mixed resolutions, insufficient views,
repeated placements, and explicit quick-check behavior.

The synthetic example renders the actual PDF with varied board poses. The
intrinsic solver detects corners without prior K/D and estimates camera
parameters; the extrinsic solver consumes the resulting intrinsics. A separate test
remaps ideal PDF images through a known nonzero lens-distortion model and checks
intrinsic recovery, including projected rays near the image periphery. The PDF
renderer itself does not simulate lens distortion.

## Proposed physical experiments — not executed

1. **Print geometry hypothesis:** print scaling or board deformation causes
   geometric bias. Measure the two rulers, several square spans, all specified
   hole baselines, and both diagonals before/after mounting. Compare against
   nominal dimensions with the same measuring instrument. Deviations above 0.5%
   fail print acceptance; passing this check does not independently certify
   camera accuracy.
2. **Intrinsic generalization hypothesis:** a diverse capture estimates stable
   K/D at fixed imaging settings. Fit two independently captured datasets and
   evaluate both on held-out views covering the center and edges. Stable K/D and
   similar low held-out residuals support repeatability. Large parameter changes
   or edge-dependent residuals contradict it and motivate inspecting focus,
   coverage, corner quality, and model suitability.
3. **Placement-error hypothesis:** world-pose disagreement is driven by measured
   board placement. Hold camera/settings fixed; repeat photographs without
   moving the board, then independently remeasure and reposition it. Compare
   within-placement and between-placement variation, and project an independently
   measured target that was not used in fitting. Variation that tracks changed
   measurements supports this hypothesis; similar bias with independently
   verified placements suggests another source.

No claim of physical millimeter accuracy should be based only on fitting
residuals, jackknife repeatability, or the synthetic test thresholds.
