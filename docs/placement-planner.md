# Visual placement planner

Run from the repository root; no OpenCV or web framework is required:

```bash
python -m calib_board.placement_planner
```

Open `http://localhost:8769/placement_planner.html`. Use `--port` to change the
port or `--no-browser` to suppress automatic browser opening. The static HTML
under `calib_board/web/` can also be opened directly. The Chinese interface runs
entirely in the browser, including JSON/SVG exports.

## Coordinates and editing

The default table is 1250 mm wide (left to right) and 625 mm deep (back to front).
Both dimensions are editable. The origin is the **back-left table corner**:

- X is the perpendicular distance from the back edge, increasing toward the front.
- Y is the perpendicular distance from the left edge, increasing toward the right.
- H1–H4 are the **mounting-hole centers**, in their printed clockwise order.
  They are not the paper corners. See [board coordinates](board.md#coordinates).

Add, rename, duplicate, hide, recolor, or delete candidate positions in the list.
Enter all eight X/Y values for each position; the diagram updates while editing.
The initial 400 × 277 mm hole rectangle is a starting layout, not a measurement.
Changing table dimensions does not rescale existing hole coordinates.

Each translucent polygon joins the four hole centers. It is not the outer paper
boundary. The camera symbol indicates a viewing side only, and can be moved to
any table edge; it is not a camera pose or calibrated field of view.

## The four distance annotations

For each valid quadrilateral:

1. Compare all sixteen hole/table-corner pairs by Euclidean distance. The
   nearest pair selects the reference table corner and the board hole **b**.
   Exact ties use back-left, back-right, front-right, front-left corner order,
   then H1–H4 order.
2. Use b's two adjacent holes. **a** is the neighbor whose direction from b is
   more parallel to the front/back edge; **c** is the other neighbor.
3. Show a and b's perpendicular distances to the selected front/back edge.
   Show b and c's perpendicular distances to the selected left/right edge.

Thus three adjacent points form an L, with **one dimension at a, two at b, and
one at c**. Dimension endpoints have ticks and numerical millimeter labels.
The same rule works for rotated boards. Negative values indicate a hole beyond
the chosen edge. Invalid/crossed or incomplete coordinates remain editable but
are not drawn as valid boards.

All visible positions show dimensions by default. Select “仅显示当前项尺寸” to
reduce overlap, then click a polygon or focus a list item to select it.

## Save and reuse

The page saves drafts in this browser's local storage. Export JSON to preserve
or move a plan; importing replaces the current plan. Missing coordinate values
are saved as `null`, never silently converted to zero. Export SVG saves the
currently displayed diagram, including the selected dimension visibility.

JSON records the table dimensions, coordinate convention, schematic camera
side, colors, visibility, names, and all four `hole_measurements` per position.
It is a **placement plan**, not an extrinsic solver manifest. Calibration also
requires matching photographs, measured board-surface height, and intrinsics.
The existing two-hole placement solver interface is unchanged by this tool.

## Implementation and checks

Rendering uses native [SVG viewBox](https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Attribute/viewBox);
drafts use [localStorage](https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage),
and downloads use [Blob](https://developer.mozilla.org/en-US/docs/Web/API/Blob).
The static tool has no external assets, analytics, camera connection, or robot
project dependency. The optional Python launcher serves only its static directory
on localhost.

Geometry checks (Node.js 18+):

```bash
node --test tests/test_placement_geometry.cjs
```

They cover rotations, all four reference table corners, dimension values, table
resizing, incomplete/crossed points, and preservation of four-hole JSON drafts.
