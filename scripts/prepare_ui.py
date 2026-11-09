"""Download signed portable Node and local font assets for reproducible CSS builds.

Run explicitly during development; application runtime makes no external font requests.
"""
from __future__ import annotations

import hashlib
import re
import shutil
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NODE_VERSION = "22.16.0"


def download(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"})
    with urllib.request.urlopen(request, timeout=90) as response, target.open("wb") as output:
        shutil.copyfileobj(response, output)


def prepare_node() -> None:
    filename = f"node-v{NODE_VERSION}-win-x64.zip"
    runtime = ROOT / ".runtime" / "node"
    archive = runtime / filename
    executable = runtime / f"node-v{NODE_VERSION}-win-x64" / "node.exe"
    if executable.exists():
        print("Portable Node already available.")
        return
    base = f"https://nodejs.org/dist/v{NODE_VERSION}"
    download(f"{base}/{filename}", archive)
    checksum_file = runtime / "SHASUMS256.txt"
    download(f"{base}/SHASUMS256.txt", checksum_file)
    expected = next(line.split()[0] for line in checksum_file.read_text().splitlines() if line.endswith(filename))
    actual = hashlib.file_digest(archive.open("rb"), "sha256").hexdigest()
    if actual != expected:
        raise RuntimeError("Node archive checksum mismatch")
    with zipfile.ZipFile(archive) as source:
        for entry in source.infolist():
            destination = (runtime / entry.filename).resolve()
            if not destination.is_relative_to(runtime.resolve()):
                raise RuntimeError("Unsafe archive entry")
        source.extractall(runtime)
    print("Portable Node downloaded; upstream SHA-256 verified.")


def prepare_fonts() -> None:
    css_url = "https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800&display=swap"
    css_path = ROOT / ".runtime" / "fonts.css"
    download(css_url, css_path)
    css = css_path.read_text(encoding="utf-8")
    urls = list(dict.fromkeys(re.findall(r"https://fonts\.gstatic\.com/[^)\s]+", css)))
    for url in urls:
        filename = url.rsplit("/", 1)[1]
        target = ROOT / "static" / "fonts" / filename
        download(url, target)
        css = css.replace(url, "../fonts/" + filename)
    (ROOT / "static" / "css" / "fonts.css").write_text(css, encoding="utf-8")
    license_target = ROOT / "static" / "fonts" / "OFL.txt"
    download("https://raw.githubusercontent.com/google/fonts/main/ofl/bevietnampro/OFL.txt", license_target)
    print(f"Vendored {len(urls)} Be Vietnam Pro font assets and SIL license.")


def prepare_javascript() -> None:
    vendor = ROOT / "static" / "vendor"
    for url, filename in [
        ("https://cdn.jsdelivr.net/npm/chart.js@4.4.8/dist/chart.umd.min.js", "chart.umd.min.js"),
        ("https://cdn.jsdelivr.net/npm/chart.js@4.4.8/LICENSE.md", "CHARTJS-LICENSE.md"),
        ("https://cdn.jsdelivr.net/npm/htmx.org@2.0.4/dist/htmx.min.js", "htmx.min.js"),
        ("https://cdn.jsdelivr.net/npm/htmx.org@2.0.4/LICENSE", "HTMX-LICENSE.txt"),
    ]:
        download(url, vendor / filename)
        if filename.endswith(".js"):
            # Runtime does not ship development source maps. Keep license comments.
            target = vendor / filename
            content = target.read_text(encoding="utf-8")
            content = re.sub(r"(?m)^//# sourceMappingURL=.*$", "", content)
            target.write_text(content, encoding="utf-8")
    print("Vendored Chart.js 4.4.8 and HTMX 2.0.4 with upstream licenses.")


if __name__ == "__main__":
    prepare_node()
    prepare_fonts()
    prepare_javascript()
