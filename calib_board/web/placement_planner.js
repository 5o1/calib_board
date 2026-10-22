(function () {
  "use strict";
  const M = PlacementModel, $ = id => document.getElementById(id);
  const STORAGE_KEY = "calibration-board-placement-plan-v1";
  const EDGE = {back: "后沿", front: "前沿", left: "左侧边", right: "右侧边"};
  let plan = M.defaultPlan(), selected = plan.placements[0].id, saveTimer;
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) plan = M.validatePlan(JSON.parse(stored));
  } catch (error) {
    $("message").textContent = "未载入浏览器存档：" + error.message;
  }
  selected = plan.placements[0]?.id;
  const fmt = value => Number(value.toFixed(1)).toString();
  function element(tag, className, text) {
    const e = document.createElement(tag);
    if (className) e.className = className;
    if (text !== undefined) e.textContent = text;
    return e;
  }
  function save() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(() => {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(plan));
        $("save-status").textContent = "已自动保存到此浏览器";
      } catch {
        $("save-status").textContent = "浏览器无法自动保存，请导出 JSON";
      }
    }, 150);
  }
  function selectPlacement(id) {
    selected = id;
    document.querySelectorAll(".card").forEach(card => card.classList.toggle("active", card.dataset.id === id));
    renderScene();
  }
  function colorFor(index) {
    const h = (index * 137.508 + 220) % 360, s = .72, l = .44;
    const channel = n => {
      const k = (n + h / 30) % 12, a = s * Math.min(l, 1 - l);
      return Math.round(255 * (l - a * Math.max(-1, Math.min(k - 3, 9 - k, 1)))).toString(16).padStart(2, "0");
    };
    return "#" + channel(0) + channel(8) + channel(4);
  }
  function freshColor() {
    let index = plan.placements.length;
    while (plan.placements.some(p => p.color === colorFor(index))) index++;
    return colorFor(index);
  }
  function addPlacement(original) {
    const p = structuredClone(original || M.defaultPlan().placements[0]);
    p.id = "position-" + crypto.randomUUID();
    p.color = freshColor();
    p.visible = true;
    p.name = original ? original.name + " 副本" : "位置 " + (plan.placements.length + 1);
    if (!original) {
      const dx = (plan.table.depth_mm - 277) / 2 - 174;
      const dy = (plan.table.width_mm - 400) / 2 - 425;
      p.hole_measurements.forEach(h => {
        h.from_back_edge_mm += dx;
        h.from_left_edge_mm += dy;
      });
    }
    plan.placements.push(p);
    selected = p.id;
    renderCards(); renderScene(); save();
    const card = [...document.querySelectorAll(".card")].find(c => c.dataset.id === p.id);
    card.scrollIntoView({block: "nearest", behavior: "smooth"});
  }
  function summary(p, target) {
    target.replaceChildren();
    const g = M.geometry(p, plan.table);
    if (g.error) {
      target.append(element("span", "error", g.error)); return;
    }
    const roles = Object.entries(g.roles).map(([r, i]) => `${r} = ${g.points[i].id}`).join("，");
    target.append(element("strong", "", `${g.corner.name}桌角 · ${roles}`));
    const values = element("div", "dimensions-summary");
    g.dimensions.forEach(d => values.append(element("span", "", `${d.point.id} → ${EDGE[d.edge]} ${fmt(d.distance)} mm`)));
    target.append(values);
    if (g.outside) target.append(element("div", "warning", "有孔位超出台面；负尺寸表示越过该边。"));
  }
  function renderCards() {
    const list = $("placements"); list.replaceChildren();
    $("count").textContent = `${plan.placements.length} 项`;
    if (!plan.placements.length) list.append(element("div", "empty", "点击“添加位置”开始填写。"));
    plan.placements.forEach(p => {
      const card = element("article", "card" + (selected === p.id ? " active" : ""));
      card.dataset.id = p.id; card.style.setProperty("--color", p.color);
      card.addEventListener("focusin", () => selectPlacement(p.id));
      const head = element("div", "card-head");
      const color = element("input"); color.type = "color"; color.value = p.color;
      color.setAttribute("aria-label", `${p.name} 颜色`);
      color.addEventListener("input", () => {
        p.color = color.value; card.style.setProperty("--color", p.color); renderScene(); save();
      });
      const name = element("input", "name"); name.value = p.name; name.setAttribute("aria-label", "位置名称");
      name.addEventListener("input", () => {p.name = name.value; renderScene(); save();});
      const remove = element("button", "", "删除"); remove.setAttribute("aria-label", `删除 ${p.name}`);
      remove.addEventListener("click", () => {
        plan.placements = plan.placements.filter(q => q.id !== p.id);
        if (selected === p.id) selected = plan.placements[0]?.id;
        renderCards(); renderScene(); save();
      });
      head.append(color, name, remove);
      const options = element("div", "card-options");
      const visibleLabel = element("label");
      const visible = element("input"); visible.type = "checkbox"; visible.checked = p.visible;
      visible.addEventListener("change", () => {p.visible = visible.checked; renderScene(); save();});
      visibleLabel.append(visible, document.createTextNode("显示此位置"));
      const copy = element("button", "", "复制");
      copy.addEventListener("click", () => addPlacement(p));
      options.append(visibleLabel, copy);
      const table = element("table");
      const header = element("tr");
      ["孔位", "X · 距后沿 (mm)", "Y · 距左边 (mm)"].forEach(t => header.append(element("th", "", t)));
      table.append(header);
      const details = element("div", "summary");
      p.hole_measurements.forEach(h => {
        const row = element("tr"); row.append(element("td", "", h.id));
        ["from_back_edge_mm", "from_left_edge_mm"].forEach((key, axis) => {
          const cell = element("td"), input = element("input");
          input.type = "number"; input.step = "0.1"; input.value = h[key] ?? "";
          input.dataset.hole = h.id; input.dataset.axis = axis === 0 ? "x" : "y";
          input.setAttribute("aria-label", `${p.name} ${h.id} ${axis === 0 ? "X 距后沿" : "Y 距左侧边"} mm`);
          input.addEventListener("input", () => {
            h[key] = input.value === "" ? null : Number(input.value);
            summary(p, details); renderScene(); save();
          });
          cell.append(input); row.append(cell);
        });
        table.append(row);
      });
      summary(p, details);
      card.append(head, options, table, details); list.append(card);
    });
  }

  const NS = "http://www.w3.org/2000/svg";
  let dimensionLabels = [];
  function svg(tag, attrs = {}, parent = $("scene"), text) {
    const e = document.createElementNS(NS, tag);
    Object.entries(attrs).forEach(([key, value]) => e.setAttribute(key, String(value)));
    if (text !== undefined) e.textContent = text;
    parent.append(e); return e;
  }
  function line(x1, y1, x2, y2, parent, attrs = {}) {
    return svg("line", {x1, y1, x2, y2, ...attrs}, parent);
  }
  function label(x, y, text, parent, attrs = {}) {
    return svg("text", {x, y, "font-size": 21, "text-anchor": "middle",
      "dominant-baseline": "middle", fill: "#647a91", ...attrs}, parent, text);
  }
  function dimension(d, g, color, index, slot, placementId) {
    const p = d.point, w = plan.table.width_mm, depth = plan.table.depth_mm;
    const vertical = d.edge === "back" || d.edge === "front";
    const offset = 20 + (index % 6) * 12 + ((slot === 0 || slot === 3) ? 10 : 0);
    const group = svg("g", {class: "dimension", "data-placement": placementId,
      "data-hole": p.id, "data-role": d.role, "data-edge": d.edge, "data-distance": d.distance,
      stroke: color, "stroke-width": 1.7, fill: "none"});
    let x1, y1, x2, y2;
    if (vertical) {
      const edgeY = d.edge === "back" ? 0 : depth;
      x1 = x2 = p.y + (g.corner.vertical === "left" ? -offset : offset);
      y1 = p.x; y2 = edgeY;
      line(p.y, y1, x1, y1, group, {"stroke-opacity": .5});
      line(p.y, y2, x1, y2, group, {"stroke-opacity": .5});
    } else {
      const edgeX = d.edge === "left" ? 0 : w;
      y1 = y2 = p.x + (g.corner.horizontal === "back" ? -offset : offset);
      x1 = p.y; x2 = edgeX;
      line(x1, p.x, x1, y1, group, {"stroke-opacity": .5});
      line(x2, p.x, x2, y2, group, {"stroke-opacity": .5});
    }
    line(x1, y1, x2, y2, group);
    [[x1, y1], [x2, y2]].forEach(([x, y]) => line(x - 5, y - 5, x + 5, y + 5, group, {"stroke-width": 2.4}));
    const text = fmt(d.distance) + " mm", boxWidth = text.length * 11.3 + 12;
    let position;
    // Short orthogonal dimensions can cross at their labels. Try other points
    // along the same dimension, then a small offset with a connecting leader.
    for (const offset of [0, -28, 28, -56, 56, -84, 84]) {
      for (const fraction of [.5, .25, .75]) {
        const baseX = x1 + (x2-x1)*fraction, baseY = y1 + (y2-y1)*fraction;
        const x = baseX + (vertical ? offset : 0), y = baseY + (vertical ? 0 : offset);
        const width = vertical ? 28 : boxWidth, height = vertical ? boxWidth : 28;
        const box = {left: x-width/2-4, right: x+width/2+4, top: y-height/2-4, bottom: y+height/2+4};
        if (!dimensionLabels.some(b => box.left < b.right && box.right > b.left &&
            box.top < b.bottom && box.bottom > b.top)) {
          position = {x, y, baseX, baseY, box}; break;
        }
      }
      if (position) break;
    }
    position ||= {x: (x1+x2)/2, y: (y1+y2)/2};
    if (position.box) dimensionLabels.push(position.box);
    if (position.baseX !== undefined && (position.x !== position.baseX || position.y !== position.baseY)) {
      line(position.baseX, position.baseY, position.x, position.y, group, {"stroke-opacity": .6});
    }
    const textGroup = svg("g", {class: "dimension-label",
      transform: `translate(${position.x} ${position.y}) rotate(${vertical ? -90 : 0})`, stroke: "none"}, group);
    svg("rect", {x: -boxWidth/2, y: -14, width: boxWidth, height: 28, rx: 4, fill: "#ffffff", "fill-opacity": .94}, textGroup);
    label(0, 1, text, textGroup, {fill: color, "font-size": 20, "font-weight": 600});
  }
  function camera(w, d) {
    const edge = plan.camera_hint.edge;
    const [x, y, angle] = {
      back: [w/2, -88, 0], front: [w/2, d+88, 180],
      left: [-88, d/2, -90], right: [w+88, d/2, 90]
    }[edge];
    const g = svg("g", {transform: `translate(${x} ${y}) rotate(${angle})`, "data-camera-edge": edge});
    svg("rect", {x: -18, y: -19, width: 36, height: 25, rx: 5, fill: "#50677c"}, g);
    svg("path", {d: "M-9 6 L9 6 L16 17 L-16 17 Z", fill: "#50677c"}, g);
    line(0, 24, 0, 68, g, {stroke: "#50677c", "stroke-width": 2.2, "stroke-dasharray": "6 5"});
    svg("path", {d: "M-6 62 L0 73 L6 62", fill: "none", stroke: "#50677c", "stroke-width": 2.2}, g);
    label(x, y - 37, "相机（示意）");
  }
  function renderScene() {
    const scene = $("scene"), w = plan.table.width_mm, d = plan.table.depth_mm;
    scene.replaceChildren();
    dimensionLabels = [];
    scene.setAttribute("viewBox", `-160 -155 ${w+320} ${d+295}`);
    scene.setAttribute("font-family", "Segoe UI, Microsoft YaHei, sans-serif");
    $("table-caption").textContent = `${fmt(w)} × ${fmt(d)} mm · 原点在后左角`;
    const defs = svg("defs");
    const pattern = svg("pattern", {id: "grid", width: 50, height: 50, patternUnits: "userSpaceOnUse"}, defs);
    svg("path", {d: "M 50 0 L 0 0 0 50", fill: "none", stroke: "#dfe7ef", "stroke-width": 1}, pattern);
    svg("rect", {width: w, height: d, fill: "#f7fafc"});
    svg("rect", {width: w, height: d, fill: "url(#grid)", stroke: "#92a9bf", "stroke-width": 2});
    label(w/2, -23, "后沿 · X = 0");
    label(w/2, d+30, "前沿 · X = " + fmt(d));
    label(-25, d/2, "左侧边 · Y = 0", scene, {transform: `rotate(-90 -25 ${d/2})`});
    label(w+28, d/2, "右侧边 · Y = " + fmt(w), scene, {transform: `rotate(90 ${w+28} ${d/2})`});
    label(-7, -23, "后左原点", scene, {"text-anchor": "end", "font-size": 19});
    line(0, 0, 105, 0, scene, {stroke: "#48647e", "stroke-width": 3});
    line(0, 0, 0, 105, scene, {stroke: "#48647e", "stroke-width": 3});
    svg("path", {d: "M98 -5 L106 0 L98 5 M-5 98 L0 106 L5 98", stroke: "#48647e", "stroke-width": 2, fill: "none"});
    label(120, 5, "+Y", scene, {"font-size": 20});
    label(5, 121, "+X", scene, {"text-anchor": "start", "font-size": 20});
    camera(w, d);
    const valid = [];
    plan.placements.forEach((p, index) => {
      if (!p.visible) return;
      const g = M.geometry(p, plan.table);
      if (g.error) return;
      valid.push({p, g, index});
      const polygon = svg("polygon", {
        points: g.points.map(q => `${q.y},${q.x}`).join(" "),
        fill: p.color, "fill-opacity": selected === p.id ? .21 : .13,
        stroke: p.color, "stroke-width": selected === p.id ? 3.5 : 2.2,
        class: "board", "data-placement": p.id, tabindex: 0, role: "button",
        "aria-label": p.name, style: "cursor:pointer"
      });
      polygon.addEventListener("click", () => selectPlacement(p.id));
      polygon.addEventListener("keydown", event => {
        if (event.key === "Enter" || event.key === " ") {event.preventDefault(); selectPlacement(p.id);}
      });
    });
    valid.forEach(({p, g, index}) => {
      if (!$("selected-only").checked || p.id === selected) {
        g.dimensions.forEach((m, slot) => dimension(m, g, p.color, index, slot, p.id));
        svg("circle", {cx: g.corner.y, cy: g.corner.x, r: 8, fill: "white", stroke: p.color, "stroke-width": 2});
      }
      const center = g.points.reduce((s, q) => ({x: s.x + q.x/4, y: s.y + q.y/4}), {x: 0, y: 0});
      label(center.y, center.x, p.name || "未命名位置", scene, {fill: p.color, "font-size": 24,
        "font-weight": 700, stroke: "#fff", "stroke-width": 4, "paint-order": "stroke"});
      g.points.forEach((q, i) => {
        const role = Object.entries(g.roles).find(([, value]) => value === i)?.[0];
        svg("circle", {cx: q.y, cy: q.x, r: role === "b" ? 6 : 4.5, fill: "white", stroke: p.color, "stroke-width": 2.5});
        // Keep hole labels inside the board, away from the outward dimension lines.
        const dx = q.y < center.y ? 12 : -12, dy = q.x < center.x ? 19 : -18;
        label(q.y+dx, q.x+dy, q.id + (role ? " · " + role : ""), scene, {
          fill: p.color, "text-anchor": dx < 0 ? "end" : "start", "font-size": 20,
          stroke: "white", "stroke-width": 4, "paint-order": "stroke"
        });
      });
    });
    const legend = $("legend"); legend.replaceChildren();
    plan.placements.forEach(p => {
      const button = element("button");
      const swatch = element("span", "swatch"); swatch.style.background = p.color;
      button.append(swatch, document.createTextNode(p.name + (p.visible ? "" : "（隐藏）")));
      button.addEventListener("click", () => selectPlacement(p.id)); legend.append(button);
    });
  }
  function settings() {
    $("table-width").value = plan.table.width_mm;
    $("table-depth").value = plan.table.depth_mm;
    $("camera-edge").value = plan.camera_hint.edge;
  }
  function download(name, content, type) {
    const url = URL.createObjectURL(new Blob([content], {type}));
    const a = element("a"); a.href = url; a.download = name; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  ["table-width", "table-depth"].forEach((id, index) => {
    $(id).addEventListener("input", () => {
      const value = Number($(id).value);
      if (!Number.isFinite(value) || value <= 0) {
        $("message").textContent = "桌面尺寸必须为正数，图中暂保留上一个有效尺寸。"; return;
      }
      $("message").textContent = "";
      plan.table[index === 0 ? "width_mm" : "depth_mm"] = value;
      document.querySelectorAll(".card").forEach(card => {
        summary(plan.placements.find(p => p.id === card.dataset.id), card.querySelector(".summary"));
      });
      renderScene(); save();
    });
  });
  $("camera-edge").addEventListener("change", () => {plan.camera_hint.edge = $("camera-edge").value; renderScene(); save();});
  $("selected-only").addEventListener("change", renderScene);
  $("add").addEventListener("click", () => addPlacement());
  $("export-json").addEventListener("click", () => download("board-placements.json", JSON.stringify(plan, null, 2) + "\n", "application/json"));
  $("export-svg").addEventListener("click", () => download("board-placements.svg",
    new XMLSerializer().serializeToString($("scene")), "image/svg+xml"));
  $("import-json").addEventListener("click", () => $("file-input").click());
  $("file-input").addEventListener("change", async event => {
    const file = event.target.files[0]; if (!file) return;
    try {
      const next = M.validatePlan(JSON.parse(await file.text()));
      plan = next; selected = plan.placements[0]?.id;
      settings(); renderCards(); renderScene(); save(); $("message").textContent = "";
    } catch (error) {
      $("message").textContent = "导入失败，现有方案保留：" + error.message;
    }
    event.target.value = "";
  });
  settings(); renderCards(); renderScene(); save();
})();
