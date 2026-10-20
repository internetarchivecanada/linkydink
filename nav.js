// Shared menu bar for the linkydink pages. Include it with
//   <script src="../nav.js" defer></script>
// and add a page here to put it in the menu.
(function () {
  const PAGES = [
    ["casey-jones-1971", "Casey Jones, 1971"],
    ["gd1971-map", "Grateful Dead 1971 map"],
    ["seedlist-builder", "Seedlist builder"],
    ["player", "Player"],
  ];
  const here = location.pathname.split("/").filter(Boolean).at(-1) === "index.html"
    ? location.pathname.split("/").filter(Boolean).at(-2)
    : location.pathname.split("/").filter(Boolean).at(-1);

  const css = document.createElement("style");
  css.textContent = `
.ld-nav { --ld-bg: #ffffff; --ld-ink: #1d2230; --ld-muted: #626a78; --ld-line: #dcdcd6; --ld-on: #1d2230; --ld-on-ink: #ffffff;
  position: relative; z-index: 30; background: var(--ld-bg); border-bottom: 1px solid var(--ld-line);
  font: 500 13px/1.2 system-ui, -apple-system, "Segoe UI", sans-serif; margin: 0 0 16px; }
@media (prefers-color-scheme: dark) {
  .ld-nav { --ld-bg: #1a1e27; --ld-ink: #e6e8ee; --ld-muted: #9aa1ae; --ld-line: #2c3240; --ld-on: #e6e8ee; --ld-on-ink: #12151c; }
}
.ld-nav-in { max-width: 1180px; margin: 0 auto; padding: 8px 16px; display: flex; flex-wrap: wrap; align-items: center; gap: 6px 14px; }
.ld-nav b { font-weight: 600; color: var(--ld-ink); margin-right: 4px; letter-spacing: .02em; }
.ld-nav ul { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 4px; }
.ld-nav a { display: block; color: var(--ld-muted); text-decoration: none; padding: 5px 10px; border-radius: 999px; }
.ld-nav a:hover { color: var(--ld-ink); background: color-mix(in srgb, var(--ld-ink) 8%, transparent); }
.ld-nav a[aria-current="page"] { background: var(--ld-on); color: var(--ld-on-ink); }
.ld-nav a:focus-visible { outline: 2px solid #3556a0; outline-offset: 2px; }`;
  document.head.appendChild(css);

  const nav = document.createElement("nav");
  nav.className = "ld-nav";
  nav.setAttribute("aria-label", "linkydink pages");
  nav.innerHTML = `<div class="ld-nav-in"><b>linkydink</b><ul>${PAGES.map(([dir, label]) =>
    `<li><a href="../${dir}/"${dir === here ? ' aria-current="page"' : ""}>${label}</a></li>`).join("")}</ul></div>`;
  document.body.prepend(nav);
})();
