from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path


OUTPUT_PATH = Path("THIRD_PARTY_LICENSES.md")
EXCLUDED_PACKAGES = {"clipscope", "pip", "setuptools", "wheel"}
LICENSE_KEYWORDS = ("LICENSE", "LICENCE", "COPYING", "NOTICE")
TEXT_SUFFIXES = {"", ".txt", ".md", ".rst", ".html"}


def normalize_license(dist: metadata.Distribution) -> str:
    meta = dist.metadata
    raw = (meta.get("License") or "").strip()
    if raw and raw.upper() != "UNKNOWN":
        first_line = raw.splitlines()[0].strip()
        return first_line or raw

    classifiers = [
        value.replace("License :: OSI Approved :: ", "").strip()
        for value in (meta.get_all("Classifier") or [])
        if "License ::" in value
    ]
    if classifiers:
        return classifiers[0]

    return "Unknown"


def resolve_homepage(dist: metadata.Distribution) -> str:
    meta = dist.metadata
    homepage = (meta.get("Home-page") or "").strip()
    if homepage:
        return homepage

    for project_url in meta.get_all("Project-URL") or []:
        if "," not in project_url:
            continue
        label, url = [part.strip() for part in project_url.split(",", 1)]
        if label.lower() in {"homepage", "home", "source", "repository"} and url:
            return url

    return "-"


def iter_license_files(dist: metadata.Distribution) -> Iterable[tuple[str, str]]:
    files = dist.files or []
    seen: set[str] = set()
    for relpath in files:
        relpath_str = str(relpath)
        upper = relpath_str.upper()
        if not any(keyword in upper for keyword in LICENSE_KEYWORDS):
            continue
        if "__PYCACHE__" in upper:
            continue
        suffix = Path(relpath_str).suffix.lower()
        if suffix not in TEXT_SUFFIXES:
            continue
        if relpath_str in seen:
            continue
        seen.add(relpath_str)

        absolute = Path(dist.locate_file(relpath))
        if not absolute.is_file():
            continue

        try:
            text = absolute.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = absolute.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        yield relpath_str, text.strip()


def collect_distributions() -> list[metadata.Distribution]:
    distributions = []
    for dist in metadata.distributions():
        name = (dist.metadata.get("Name") or "").strip()
        if not name:
            continue
        if name.lower() in EXCLUDED_PACKAGES:
            continue
        distributions.append(dist)
    return sorted(distributions, key=lambda item: (item.metadata["Name"] or "").lower())


def build_markdown(distributions: list[metadata.Distribution]) -> str:
    generated_at = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    lines: list[str] = []
    lines.append("# Third-Party Licenses")
    lines.append("")
    lines.append("ClipScope 配布物に含まれる、またはビルド時に使用する主要な Python 依存関係のライセンス一覧です。")
    lines.append("")
    lines.append(f"- Generated at: {generated_at}")
    lines.append(f"- Python: {sys.version.split()[0]}")
    lines.append(f"- Packages: {len(distributions)}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Package | Version | License | Homepage |")
    lines.append("| --- | --- | --- | --- |")

    for dist in distributions:
        name = dist.metadata["Name"]
        version = dist.version
        license_name = normalize_license(dist).replace("|", "\\|")
        homepage = resolve_homepage(dist).replace("|", "\\|")
        lines.append(f"| {name} | {version} | {license_name} | {homepage} |")

    lines.append("")
    lines.append("## License Texts")
    lines.append("")

    for dist in distributions:
        name = dist.metadata["Name"]
        version = dist.version
        files = list(iter_license_files(dist))
        lines.append(f"### {name} {version}")
        lines.append("")
        lines.append(f"- License: {normalize_license(dist)}")
        lines.append(f"- Homepage: {resolve_homepage(dist)}")
        if not files:
            lines.append("- License file: metadata から検出できませんでした")
            lines.append("")
            continue

        for relpath, text in files:
            lines.append(f"- Source: `{relpath}`")
            lines.append("")
            lines.append("```text")
            lines.append(text)
            lines.append("```")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate THIRD_PARTY_LICENSES.md from the current environment.")
    parser.add_argument(
        "--output",
        default=str(OUTPUT_PATH),
        help="Output markdown path. Default: THIRD_PARTY_LICENSES.md",
    )
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    distributions = collect_distributions()
    content = build_markdown(distributions)
    output_path.write_text(content, encoding="utf-8")
    print(f"Generated {output_path} ({len(distributions)} packages)")


if __name__ == "__main__":
    main()
