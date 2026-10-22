/* Pure geometry shared by the browser and the Node geometry tests. */
(function (root) {
  "use strict";
  const HOLES = ["H1", "H2", "H3", "H4"];
  const FORMAT = "calibration-board-placement-plan";

  function defaultPlan() {
    return {
      format: FORMAT, version: 1, units: "mm",
      coordinates: {origin: "table_back_left", x: "back_to_front", y: "left_to_right"},
      reference_points: "H1-H4 mounting-hole centers, clockwise on the print",
      table: {width_mm: 1250, depth_mm: 625}, camera_hint: {edge: "back"},
      placements: [{
        id: "position-1", name: "位置 1", color: "#2563eb", visible: true,
        hole_measurements: [
          {id: "H1", from_back_edge_mm: 174, from_left_edge_mm: 425},
          {id: "H2", from_back_edge_mm: 174, from_left_edge_mm: 825},
          {id: "H3", from_back_edge_mm: 451, from_left_edge_mm: 825},
          {id: "H4", from_back_edge_mm: 451, from_left_edge_mm: 425}
        ]
      }]
    };
  }

  function points(placement) {
    return placement.hole_measurements.map(p => ({
      id: p.id, x: p.from_back_edge_mm, y: p.from_left_edge_mm
    }));
  }

  function geometry(placement, table) {
    const p = points(placement);
    if (p.some(q => !Number.isFinite(q.x) || !Number.isFinite(q.y))) {
      return {error: "请填写四个孔中心的 X、Y 坐标。"};
    }
    const turns = p.map((a, i) => {
      const b = p[(i + 1) % 4], c = p[(i + 2) % 4];
      return (b.x - a.x) * (c.y - b.y) - (b.y - a.y) * (c.x - b.x);
    });
    if (!turns.every(v => v > 1e-9) && !turns.every(v => v < -1e-9)) {
      return {error: "H1–H4 应按板上顺序形成四边形，请检查重复或交叉的坐标。"};
    }
    const {width_mm: w, depth_mm: d} = table;
    const corners = [
      {name: "左后", x: 0, y: 0, horizontal: "back", vertical: "left"},
      {name: "右后", x: 0, y: w, horizontal: "back", vertical: "right"},
      {name: "右前", x: d, y: w, horizontal: "front", vertical: "right"},
      {name: "左前", x: d, y: 0, horizontal: "front", vertical: "left"}
    ];
    let best = null;
    corners.forEach(corner => p.forEach((point, index) => {
      const squared = (point.x - corner.x) ** 2 + (point.y - corner.y) ** 2;
      if (!best || squared < best.squared) best = {corner, index, squared};
    }));
    const b = best.index, neighbors = [(b + 1) % 4, (b + 3) % 4];
    // a's side is more parallel to the front/back edge; c is the other neighbor.
    const parallel = i => Math.abs(p[i].y - p[b].y) /
      Math.hypot(p[i].x - p[b].x, p[i].y - p[b].y);
    const [a, c] = parallel(neighbors[0]) >= parallel(neighbors[1])
      ? neighbors : neighbors.slice().reverse();
    const measurement = (index, role, edge) => ({
      point: p[index], role, edge,
      distance: edge === "back" ? p[index].x : edge === "front" ? d - p[index].x
        : edge === "left" ? p[index].y : w - p[index].y
    });
    return {
      points: p, corner: best.corner, roles: {a, b, c},
      outside: p.some(q => q.x < 0 || q.x > d || q.y < 0 || q.y > w),
      dimensions: [
        measurement(a, "a", best.corner.horizontal),
        measurement(b, "b", best.corner.horizontal),
        measurement(b, "b", best.corner.vertical),
        measurement(c, "c", best.corner.vertical)
      ]
    };
  }

  function validatePlan(plan) {
    if (plan?.format !== FORMAT || plan.version !== 1 || plan.units !== "mm") {
      throw Error("请选择本工具导出的毫米制位置方案 JSON。");
    }
    if (plan.reference_points !== defaultPlan().reference_points ||
        plan.coordinates?.origin !== "table_back_left" ||
        plan.coordinates?.x !== "back_to_front" || plan.coordinates?.y !== "left_to_right") {
      throw Error("坐标定义或测量点基准不匹配。");
    }
    if (![plan.table?.width_mm, plan.table?.depth_mm].every(n => Number.isFinite(n) && n > 0)) {
      throw Error("桌面长宽必须为正数。");
    }
    if (!["back", "front", "left", "right"].includes(plan.camera_hint?.edge) ||
        !Array.isArray(plan.placements)) throw Error("位置方案格式不完整。");
    const ids = new Set();
    for (const p of plan.placements) {
      if (typeof p.id !== "string" || ids.has(p.id) || typeof p.name !== "string" ||
          !/^#[0-9a-f]{6}$/i.test(p.color) || typeof p.visible !== "boolean" ||
          !Array.isArray(p.hole_measurements) || p.hole_measurements.length !== 4) {
        throw Error("候选位置的名称、颜色或四个孔位格式不正确。");
      }
      ids.add(p.id);
      p.hole_measurements.forEach((h, i) => {
        if (h.id !== HOLES[i] ||
            ![h.from_back_edge_mm, h.from_left_edge_mm].every(v => v === null || Number.isFinite(v))) {
          throw Error("孔位须按 H1–H4 排列，坐标须为数字或尚未填写的 null。");
        }
      });
    }
    return plan;
  }

  const api = {HOLES, FORMAT, defaultPlan, points, geometry, validatePlan};
  root.PlacementModel = api;
  if (typeof module !== "undefined") module.exports = api;
})(globalThis);
