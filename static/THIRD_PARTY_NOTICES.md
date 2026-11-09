# Frontend dependencies

All runtime frontend assets are local. No CDN is required to render the application.
Development source-map directives are removed from vendored runtime JavaScript; upstream license comments are retained.

| Dependency | Version | License | Location |
| --- | --- | --- | --- |
| Chart.js | 4.4.8 | MIT | `vendor/chart.umd.min.js`, `vendor/CHARTJS-LICENSE.md` |
| HTMX | 2.0.4 | Zero-Clause BSD | `vendor/htmx.min.js`, `vendor/HTMX-LICENSE.txt` |
| Be Vietnam Pro | Google Fonts upstream | SIL Open Font License 1.1 | `fonts/`, `fonts/OFL.txt` |
| Tailwind CSS | 3.4.19 | MIT | compiled `css/tailwind.css`, `vendor/TAILWIND-LICENSE.txt` |

`scripts/prepare_ui.py` downloads the pinned JavaScript packages and fonts for maintainers. `package-lock.json` records development dependency integrity. Portable Node 22.16.0 is a development tool kept under ignored `.runtime/`; its official archive SHA-256 is verified against the Node distribution checksum manifest.
