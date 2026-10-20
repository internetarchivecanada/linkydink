// Shared menu bar for the linkydink pages. Include it with
//   <script src="../nav.js" defer></script>
// and add a page here to put it in the menu.
//
// The bar sits above <body>, full width, inside a shadow root, so it looks the
// same on every page: page styles can't reach it and its styles can't leak out.
(function () {
  const PAGES = [
    ["casey-jones-1971", "Casey Jones, 1971"],
    ["gd1971-map", "Grateful Dead 1971 map"],
    ["seedlist-builder", "Seedlist builder"],
    ["player", "Player"],
    ["gd-player", "Grateful Dead shows map"],
    ["aadam-jacobs", "Aadam Jacobs Collection"],
  ];
  const parts = location.pathname.split("/").filter(Boolean);
  const here = parts.at(-1) === "index.html" ? parts.at(-2) : parts.at(-1);

  const host = document.createElement("linkydink-nav");
  const root = host.attachShadow({ mode: "open" });
  root.innerHTML = `<style>
:host { all: initial; display: block; position: relative; z-index: 30;
  --bg: #ffffff; --ink: #1d2230; --muted: #626a78; --line: #dcdcd6; --on: #1d2230; --on-ink: #ffffff; --focus: #3556a0; }
@media (prefers-color-scheme: dark) {
  :host { --bg: #1a1e27; --ink: #e6e8ee; --muted: #9aa1ae; --line: #2c3240; --on: #e6e8ee; --on-ink: #12151c; --focus: #7d9be0; }
}
nav { background: var(--bg); border-bottom: 1px solid var(--line); font: 500 13px/1.2 system-ui, -apple-system, "Segoe UI", sans-serif; }
.in { max-width: 1180px; margin: 0 auto; padding: 8px 16px; display: flex; flex-wrap: wrap; align-items: center; gap: 6px 14px; box-sizing: border-box; }
b { font-weight: 600; color: var(--ink); letter-spacing: .02em; }
ul { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 4px; }
li { margin: 0; padding: 0; }
a { display: block; color: var(--muted); text-decoration: none; padding: 5px 10px; border-radius: 999px; }
a:hover { color: var(--ink); background: color-mix(in srgb, var(--ink) 8%, transparent); }
a[aria-current="page"] { background: var(--on); color: var(--on-ink); }
a:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; }
</style>
<nav aria-label="linkydink pages"><div class="in"><b>linkydink</b><ul>${PAGES.map(([dir, label]) =>
    `<li><a href="../${dir}/"${dir === here ? ' aria-current="page"' : ""}>${label}</a></li>`).join("")}</ul></div></nav>`;
  document.documentElement.insertBefore(host, document.body);
})();
