# Board, printing, and mounting

## Current specification

The authoritative layout is [board_v1_1.json](../spec/board_v1_1.json). Dimensions
are in millimeters; pose translations in tool outputs are in meters. Version
1.1.1 translates the printed labels and changes their font sizes/positions where
needed. Its checkerboard, markers, gray patches, rulers, slot, and hole geometry
are unchanged from 1.1.0. Detection files must match the selected specification
version; re-run detection for a new version instead of mixing saved results.

| Item | Value |
| --- | --- |
| Board ID / current version | STATION-CALIB-001 / 1.1.1 |
| Page | A3 landscape, 420 × 297 mm |
| ChArUco squares | 6 columns × 5 rows; 5 × 4 internal corners |
| Dictionary / marker IDs | DICT_4X4_50 / 0–14 |
| Square / marker side | 50 / 39 mm |
| Marker cells / white margin | 6 × 6 including border; 6.5 mm cell; 5.5 mm margin |
| Pattern extent | 300 × 250 mm |
| Pattern origin on paper | 25 mm from the left, 20 mm from the top |
| Gray patches | Eight 22 × 22 mm patches; nominal sRGB 16, 48, 80, 112, 144, 176, 208, 240 |
| Physical card slot | 63.5 × 109 mm, portrait, at board (314, 125) mm |
| X ruler endpoints | (45, 270) to (145, 270) mm |
| Y ruler endpoints | (−12, 40) to (−12, 140) mm |
| Mounting marks | 3.2 mm circles, 10 mm crosshairs, H1–H4 labels |

The gray patches are nominal printed RGB values, not measured reflectances. The
card slot is an outline for a physical Calibrite ColorChecker Classic Mini; no
color patches are printed. Its local frame and the exact rotated transform are
stored in `colorchecker_slot.T_board_card_mm` in the specification. Coplanarity
with the printed surface is an assumption, not a measured property.

Gray patch top-left positions in board coordinates are (317,15), (342,15),
(317,41), (342,41), (317,67), (342,67), (317,93), and (342,93) mm.

## Coordinates

The board origin is the upper-left **outer pattern corner**, not the paper
corner. Facing the print, X points right, Y down, and Z into the board. The board
uses OpenCV's non-legacy pattern. `T_A_B` maps coordinates from B into A.

| Hole | Board X,Y (mm) | Paper X,Y from top-left (mm) |
| --- | --- | --- |
| H1 | −15, −10 | 10, 10 |
| H2 | 385, −10 | 410, 10 |
| H3 | 385, 267 | 410, 287 |
| H4 | −15, 267 | 10, 287 |

Hole centers form a 400 × 277 mm rectangle with 486.548044904 mm diagonals.
Numbers run clockwise from H1 at the top-left. Circles indicate optional mounting
locations; printing them does not require drilling the board.

## Print acceptance

1. Print the PDF on A3 landscape at **100% / actual size**. Disable fit-to-page,
   driver scaling, and toner-saving settings. Use matte paper and verify that
   neither ruler nor any mounting mark is clipped.
2. Measure both 100 mm rulers between endpoint centers. Accept 99.5–100.5 mm.
3. Measure 50 mm square sides in the center and near the edges. Accept
   49.75–50.25 mm; measuring several squares together improves reading precision.
4. Measure H1–H2 (400 mm), H1–H4 (277 mm), and both diagonals
   (486.548044904 mm). Each relative deviation must be at most 0.5%.
5. Reject a print that fails any dimensional check. Do not solve poses using
   nominal dimensions for a known incorrectly scaled print.
6. Mount on a flat, rigid backing such as acrylic or foam board without bubbles,
   wrinkles, or bowing. Repeat measurements after mounting. Keep clips, screws,
   and tape away from the functional regions.
7. Complete [the measurement template](../spec/print_measurements_v1_1.template.json)
   and save it under `docs/measurements/<date>_<board-id>.json`. Null entries mean
   unmeasured, not accepted. Record the actual surface height including backing
   and adhesive when measuring a tabletop placement.

The PDF contains vector pattern cells and gray patches. The generated 300 DPI
PNG is a preview; use the PDF for printing. The PDF MediaBox uses 72/25.4 pt/mm.

## Working distance

The board was designed around the illustrative camera matrices in
[examples](../examples), including a 1280 × 720 camera with fx=906.561,
fy=905.986. These values are **not a calibration for your camera**.

For that camera, the historical geometric calculation at 0.9 m and a 45° angle
between board normal and view direction gave a minimum projected cell sampling
of about 3.53738 px. At a fixed 0.725 m camera height, the corresponding 3.5 px
sampling range was approximately 0.8372–0.9813 m. A 5.5 mm white margin exceeds
0.7 × 6.5 = 4.55 mm, the OpenCV tutorial's margin recommendation.

These are sampling calculations, not real detection-rate measurements. The
entire 0.65–0.80 m height and 0.8–1.0 m distance range does not meet 3.5 px under
all tilts. Smaller image size, blur, glare, shadows, and larger viewing angles can
make detection worse. Use diffuse illumination, sharp focus, and adequate image
coverage. See [validation](validation.md) and the [archived numerical budgets](archive/legacy/docs/v1_1/design-check.json).
