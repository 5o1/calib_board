const {test} = require("node:test");
const assert = require("node:assert/strict");
const M = require("../calib_board/web/placement_model.js");
const table = {width_mm: 1250, depth_mm: 625};
function placement(xy) {
  return {hole_measurements: xy.map(([x, y], i) => ({
    id: M.HOLES[i], from_back_edge_mm: x, from_left_edge_mm: y
  }))};
}
const rotated = [[80, 120], [180, 450], [380, 390], [280, 60]];

test("rotated board: adjacent a/b/c give exactly four perpendicular dimensions", () => {
  const g = M.geometry(placement(rotated), table);
  assert.equal(g.corner.name, "左后");
  assert.deepEqual(g.roles, {a: 1, b: 0, c: 3});
  assert.deepEqual(g.dimensions.map(d => [d.point.id, d.role, d.edge, d.distance]), [
    ["H2", "a", "back", 180], ["H1", "b", "back", 80],
    ["H1", "b", "left", 120], ["H4", "c", "left", 60]
  ]);
});
test("all four nearest table corners select their corresponding two edges", () => {
  for (const [flipX, flipY, name, edges] of [
    [false, false, "左后", ["back", "left"]],
    [false, true, "右后", ["back", "right"]],
    [true, true, "右前", ["front", "right"]],
    [true, false, "左前", ["front", "left"]]
  ]) {
    const p = placement(rotated.map(([x, y]) => [flipX ? 625-x : x, flipY ? 1250-y : y]));
    const g = M.geometry(p, table);
    assert.equal(g.corner.name, name);
    assert.deepEqual([...new Set(g.dimensions.map(d => d.edge))], edges);
    assert.equal(g.dimensions.filter(d => d.role === "b").length, 2);
    assert.deepEqual(g.dimensions.map(d => d.distance), [180, 80, 120, 60]);
  }
});
test("large rotations swap the adjacent measurement roles", () => {
  const xy = [[70, 80], [310, 130], [270, 320], [30, 270]];
  const g = M.geometry(placement(xy), table);
  assert.equal(g.roles.b, 0);
  assert.equal(g.roles.a, 3);
  assert.equal(g.roles.c, 1);
});
test("table resize changes distances without rescaling measured hole coordinates", () => {
  const p = placement(rotated.map(([x, y]) => [625-x, 1250-y]));
  const before = JSON.stringify(p);
  const g = M.geometry(p, {width_mm: 1300, depth_mm: 700});
  assert.equal(g.corner.name, "右前");
  assert.deepEqual(g.dimensions.map(d => d.distance), [255, 155, 170, 110]);
  assert.equal(JSON.stringify(p), before);
});
test("crossed or missing holes do not generate a misleading polygon", () => {
  assert.ok(M.geometry(placement([[0,0],[200,200],[0,200],[200,0]]), table).error);
  const p = placement(rotated); p.hole_measurements[0].from_back_edge_mm = null;
  assert.ok(M.geometry(p, table).error);
});
test("draft JSON round-trips all four named hole measurements", () => {
  const plan = M.defaultPlan();
  plan.placements[0].hole_measurements[2].from_left_edge_mm = null;
  const restored = M.validatePlan(JSON.parse(JSON.stringify(plan)));
  assert.deepEqual(restored, plan);
  assert.equal(restored.placements[0].hole_measurements.length, 4);
});
test("imports reject a mismatched coordinate system or duplicate placement ids", () => {
  const plan = M.defaultPlan(); plan.coordinates.x = "left_to_right";
  assert.throws(() => M.validatePlan(plan), /坐标/);
  const other = M.defaultPlan(); other.placements.push(structuredClone(other.placements[0]));
  assert.throws(() => M.validatePlan(other), /候选/);
});
