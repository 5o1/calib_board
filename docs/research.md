# Technical references

## OpenCV APIs

- [ChArUco camera calibration, OpenCV 4.13](https://docs.opencv.org/4.13.0/da/d13/tutorial_aruco_calibration.html):
  detect board corners across different views, match object/image points, and
  solve for intrinsics with the standard camera-calibration API.
- [ChArUco detection and pose](https://docs.opencv.org/4.13.0/df/d4a/tutorial_charuco_detection.html):
  board construction, homography interpolation without prior intrinsics,
  calibrated detection, marker-refinement guidance, and `matchImagePoints`/PnP.
- [Camera calibration reference](https://docs.opencv.org/4.13.0/d9/d0c/group__calib3d.html):
  pinhole distortion models, reprojection optimization, and parameter uncertainty.

This project uses `CharucoBoard`, `CharucoDetector`, `matchImagePoints`,
`calibrateCameraExtended`, `solvePnP`, and `solvePnPRefineLM`. The current board is
6 × 5 squares, with 50 mm squares and 39 mm DICT_4X4_50 markers. Non-legacy
pattern behavior is explicit. The original research note described the obsolete
7 × 6 design; it is preserved in the archive rather than used as current advice.

## Design references

The following links were recorded during the original design research; their
historical observations are retained in the
[original research record](archive/legacy/docs/research.md).

- [DROID camera calibration workflow](https://droid-dataset.github.io/droid/example-workflows/calibrating-cameras.html)
  and [DROID parameters](https://github.com/droid-dataset/droid/blob/main/droid/misc/parameters.py).
  This was a workflow reference, not the source of this board's dimensions or software.
- [calib.io calibration best practices](https://calib.io/blogs/knowledge-base/calibration-best-practices)
  and [pattern generator notes](https://calib.io/pages/camera-calibration-pattern-generator).
  This project generates its own PDF; it does not redistribute that generator's output.
- [Calibrite ColorChecker Classic Mini](https://calibrite.com/us/product/colorchecker-classic-mini/?noredirect=en-US).
  The board reserves an outline for a physical card; it does not reproduce color patches.

Upstream recommendations, this repository's geometry choices, synthetic results,
and still-unexecuted physical checks are separate kinds of evidence. See
[validation](validation.md) for the experiments needed to establish physical behavior.
