(function () {
  const data = window.LINKY_DATA;

  // ---- Build the graph model ------------------------------------------------

  const nodes = [
    ...data.bands.map((b) => ({ id: b.id, name: b.name, type: b.solo ? "solo" : "band" })),
    ...data.people.map((p) => ({ id: p.id, name: p.name, type: "person" })),
  ];
  const byId = new Map(nodes.map((n) => [n.id, n]));

  const links = data.memberships
    .filter((m) => byId.has(m.person) && byId.has(m.band))
    .map((m) => ({
      source: m.person,
      target: m.band,
      role: m.role || "",
      status: m.status || "member",
      note: m.note || "",
      verified: m.verified !== false,
    }));

  // Adjacency: node id -> [{ other, link }]
  const adj = new Map(nodes.map((n) => [n.id, []]));
  for (const l of links) {
    adj.get(l.source).push({ other: l.target, link: l });
    adj.get(l.target).push({ other: l.source, link: l });
  }
  for (const n of nodes) n.degree = adj.get(n.id).length;

  const byName = new Map(nodes.map((n) => [n.name.toLowerCase(), n]));

  // ---- Fill the search lists -----------------------------------------------

  const sorted = [...nodes].sort((a, b) => a.name.localeCompare(b.name));
  document.getElementById("all-names").innerHTML = sorted
    .map((n) => `<option value="${esc(n.name)}"></option>`).join("");
  document.getElementById("people-names").innerHTML = sorted
    .filter((n) => n.type === "person")
    .map((n) => `<option value="${esc(n.name)}"></option>`).join("");

  // ---- Draw ----------------------------------------------------------------

  const container = document.getElementById("graph");
  const svg = d3.select(container).append("svg");
  const zoomLayer = svg.append("g");

  const radius = (n) => (n.type === "person" ? 5 + n.degree * 1.5 : 9 + n.degree * 1.6);

  const linkSel = zoomLayer.append("g")
    .selectAll("line")
    .data(links)
    .join("line")
    .attr("class", (l) => {
      let c = "link";
      if (l.status !== "member") c += " soft";
      if (!l.verified) c += " unverified";
      return c;
    });

  const nodeSel = zoomLayer.append("g")
    .selectAll("g")
    .data(nodes)
    .join("g")
    .attr("class", (n) => `node ${n.type}`)
    .on("click", (event, n) => { event.stopPropagation(); select(n.id); })
    .on("mouseenter", (event, n) => { if (!selectedId && !pathIds) focus(neighborhood(n.id)); })
    .on("mouseleave", () => { if (!selectedId && !pathIds) unfocus(); });

  nodeSel.append("circle").attr("r", radius);
  nodeSel.append("title").text((n) => n.name);
  nodeSel.append("text")
    .attr("dy", (n) => radius(n) + 12)
    .attr("text-anchor", "middle")
    .text((n) => n.name);

  const sim = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links).id((n) => n.id).distance(55).strength(0.7))
    .force("charge", d3.forceManyBody().strength(-260))
    .force("collide", d3.forceCollide().radius((n) => radius(n) + 14))
    .force("x", d3.forceX().strength(0.04))
    .force("y", d3.forceY().strength(0.06))
    .on("tick", () => {
      linkSel
        .attr("x1", (l) => l.source.x).attr("y1", (l) => l.source.y)
        .attr("x2", (l) => l.target.x).attr("y2", (l) => l.target.y);
      nodeSel.attr("transform", (n) => `translate(${n.x},${n.y})`);
    });

  nodeSel.call(d3.drag()
    .on("start", (event, n) => { if (!event.active) sim.alphaTarget(0.3).restart(); n.fx = n.x; n.fy = n.y; })
    .on("drag", (event, n) => { n.fx = event.x; n.fy = event.y; })
    .on("end", (event, n) => { if (!event.active) sim.alphaTarget(0); n.fx = null; n.fy = null; }));

  const zoom = d3.zoom().scaleExtent([0.25, 4])
    .on("zoom", (event) => zoomLayer.attr("transform", event.transform));
  svg.call(zoom).on("dblclick.zoom", null);
  svg.on("click", () => clearAll());

  function resize() {
    const { width, height } = container.getBoundingClientRect();
    svg.attr("viewBox", [-width / 2, -height / 2, width, height]);
  }
  resize();
  window.addEventListener("resize", resize);

  // Zoom to fit once the first layout settles, so small windows see everything.
  function fitToView() {
    const { width, height } = container.getBoundingClientRect();
    const xs = d3.extent(nodes, (n) => n.x);
    const ys = d3.extent(nodes, (n) => n.y);
    const pad = 40;
    const k = Math.min(1.2, width / (xs[1] - xs[0] + pad * 2), height / (ys[1] - ys[0] + pad * 2));
    svg.transition().duration(600).call(zoom.transform,
      d3.zoomIdentity.scale(k).translate(-(xs[0] + xs[1]) / 2, -(ys[0] + ys[1]) / 2));
  }
  sim.on("end.fit", () => { sim.on("end.fit", null); fitToView(); });

  // ---- Highlighting --------------------------------------------------------

  let selectedId = null;
  let pathIds = null;

  function neighborhood(id) {
    const ids = new Set([id]);
    for (const { other } of adj.get(id)) ids.add(other);
    return ids;
  }

  function focus(ids, pathLinks) {
    svg.classed("focused", true);
    nodeSel.classed("lit", (n) => ids.has(n.id));
    linkSel
      .classed("lit", (l) => pathLinks ? pathLinks.has(l) : ids.has(l.source.id) && ids.has(l.target.id) &&
        (l.source.id === selectedId || l.target.id === selectedId || !selectedId))
      .classed("on-path", (l) => !!pathLinks && pathLinks.has(l));
  }

  function unfocus() {
    svg.classed("focused", false);
    nodeSel.classed("lit", false);
    linkSel.classed("lit", false).classed("on-path", false);
  }

  function select(id) {
    pathIds = null;
    selectedId = id;
    nodeSel.classed("selected", (n) => n.id === id);
    focus(neighborhood(id));
    renderDetails(byId.get(id));
  }

  function clearAll() {
    selectedId = null;
    pathIds = null;
    nodeSel.classed("selected", false);
    unfocus();
    panel.innerHTML = `<p class="hint">Click a band or musician to see its connections. Drag to rearrange, scroll to zoom.</p>`;
  }

  // ---- Side panel ----------------------------------------------------------

  const panel = document.getElementById("panel");

  panel.addEventListener("click", (event) => {
    const a = event.target.closest("a[data-id]");
    if (a) { event.preventDefault(); select(a.dataset.id); }
  });

  const nodeLink = (id) => `<a data-id="${id}">${esc(byId.get(id).name)}</a>`;

  function membershipMeta(l) {
    const bits = [l.role];
    if (l.status !== "member") bits.push(l.status);
    let html = `<span class="meta">${esc(bits.filter(Boolean).join(" · "))}</span>`;
    if (l.note) html += `<br><span class="meta">${esc(l.note)}</span>`;
    if (!l.verified) html += `<br><span class="warn">Unverified</span>`;
    return html;
  }

  // For a node, find nodes two hops away (same type) and what connects them.
  function secondHop(id) {
    const out = new Map();
    for (const { other: mid } of adj.get(id)) {
      for (const { other } of adj.get(mid)) {
        if (other === id) continue;
        if (!out.has(other)) out.set(other, []);
        out.get(other).push(mid);
      }
    }
    return [...out.entries()].sort((a, b) => b[1].length - a[1].length ||
      byId.get(a[0]).name.localeCompare(byId.get(b[0]).name));
  }

  function renderDetails(n) {
    const isPerson = n.type === "person";
    const direct = adj.get(n.id)
      .slice()
      .sort((a, b) => byId.get(a.other).name.localeCompare(byId.get(b.other).name));
    const hops = secondHop(n.id);

    panel.innerHTML = `
      <h2>${esc(n.name)}</h2>
      <div class="kind">${isPerson ? "Musician" : n.type === "solo" ? "Solo act" : "Band"}</div>

      <h3>${isPerson ? "Bands" : "Members"}</h3>
      <ul>${direct.map(({ other, link }) => `<li>${nodeLink(other)}<br>${membershipMeta(link)}</li>`).join("")}</ul>

      <h3>${isPerson ? "Has played with" : "Connected bands"}</h3>
      ${hops.length ? `<ul>${hops.map(([other, via]) =>
        `<li>${nodeLink(other)}<br><span class="meta">via ${via.map((v) => esc(byId.get(v).name)).join(", ")}</span></li>`
      ).join("")}</ul>` : `<p class="meta">None in this dataset yet.</p>`}
    `;
  }

  // ---- Path finder ---------------------------------------------------------

  function shortestPath(fromId, toId) {
    const prev = new Map([[fromId, null]]);
    const queue = [fromId];
    while (queue.length) {
      const cur = queue.shift();
      if (cur === toId) break;
      for (const { other, link } of adj.get(cur)) {
        if (!prev.has(other)) { prev.set(other, { from: cur, link }); queue.push(other); }
      }
    }
    if (!prev.has(toId)) return null;
    const ids = [];
    const pathLinks = new Set();
    for (let cur = toId; cur !== null; ) {
      ids.unshift(cur);
      const p = prev.get(cur);
      if (p) pathLinks.add(p.link);
      cur = p ? p.from : null;
    }
    return { ids, pathLinks };
  }

  const fromInput = document.getElementById("path-from");
  const toInput = document.getElementById("path-to");

  function tryPath() {
    const a = byName.get(fromInput.value.trim().toLowerCase());
    const b = byName.get(toInput.value.trim().toLowerCase());
    if (!a || !b || a.type !== "person" || b.type !== "person") return;

    selectedId = null;
    nodeSel.classed("selected", (n) => n.id === a.id || n.id === b.id);
    const result = shortestPath(a.id, b.id);
    if (!result) {
      pathIds = new Set([a.id, b.id]);
      focus(pathIds, new Set());
      panel.innerHTML = `<h2>No link found</h2><p class="meta">${esc(a.name)} and ${esc(b.name)} aren't connected in this dataset yet.</p>`;
      return;
    }
    pathIds = new Set(result.ids);
    focus(pathIds, result.pathLinks);
    const steps = (result.ids.length - 1) / 2;
    panel.innerHTML = `
      <h2>${esc(a.name)} → ${esc(b.name)}</h2>
      <div class="kind">${steps} band${steps === 1 ? "" : "s"} apart</div>
      <h3>Path</h3>
      <ol class="path">${result.ids.map((id) => `<li>${nodeLink(id)}</li>`).join("")}</ol>
    `;
  }

  fromInput.addEventListener("change", tryPath);
  toInput.addEventListener("change", tryPath);

  document.getElementById("search").addEventListener("change", (event) => {
    const n = byName.get(event.target.value.trim().toLowerCase());
    if (!n) return;
    select(n.id);
    const t = d3.zoomTransform(svg.node());
    svg.transition().duration(500)
      .call(zoom.translateTo, n.x, n.y)
      .call(zoom.scaleTo, Math.max(t.k, 1.4));
  });

  document.getElementById("clear").addEventListener("click", () => {
    document.getElementById("search").value = "";
    fromInput.value = "";
    toInput.value = "";
    clearAll();
  });

  function esc(s) {
    return String(s).replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  }
})();
