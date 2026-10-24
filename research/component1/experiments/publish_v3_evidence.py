"""Prepare a public research supplement; publishing to Git remains a separate step.

Only the completed evidence archive and explicit research-source paths are used.
Vendor OHLCV histories, participant responses, credentials and model weights
are outside this allowlist.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "output/Component1_V3_Completed_Results_R26-IT-076.zip"
PUBLIC = ROOT / "research/component1/results/paper_v3_verified"
RELEASES = ROOT / "research/component1/releases"
CODE_ZIP = RELEASES / "Component1_Research_Code_and_Results_R26-IT-076.zip"


def main():
    import json
    with zipfile.ZipFile(SOURCE) as archive:
        receipt = json.loads(archive.read("package_receipt.json"))
        if receipt.get("execution_complete") is not True:
            raise ValueError("Only completed execution can be published.")
        checks = [line.split("  ", 1) for line in archive.read("SHA256SUMS").decode().splitlines()]
        if set(name for _, name in checks) != set(archive.namelist()) - {"SHA256SUMS"}:
            raise ValueError("Evidence inventory does not match checksums.")
        for digest, name in checks:
            if hashlib.sha256(archive.read(name)).hexdigest() != digest:
                raise ValueError("Evidence fingerprint mismatch: " + name)
        PUBLIC.mkdir(parents=True, exist_ok=True)
        RELEASES.mkdir(parents=True, exist_ok=True)
        files = {}
        for name in archive.namelist():
            path = Path(name)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("Unsafe archive path.")
            data = archive.read(name)
            # Individual stock summaries stay in the downloadable ZIP; aggregate
            # tables and provenance are also browsable directly in the repository.
            if not name.startswith("per_stock/") and name != "README.md":
                target = PUBLIC / ("ARCHIVE_SHA256SUMS" if name == "SHA256SUMS" else path)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            files["research/component1/artifacts/paper_v3_verified/" + name] = data
    shutil.copy2(SOURCE, RELEASES / SOURCE.name)

    for folder in ("research/component1/experiments", "research/component1/src",
                   "research/user_study"):
        for path in (ROOT / folder).rglob("*"):
            if (path.is_file() and path.suffix in {".py", ".md", ".html", ".json"}
                    and "__pycache__" not in path.parts
                    and not {"responses", "results"}.intersection(path.parts)):
                files[str(path.relative_to(ROOT))] = path.read_bytes()
    for name in ("research/component1/requirements.txt", "research/component1/README.md",
                 "server/scripts/exportResearchHistories.js"):
        files[name] = (ROOT / name).read_bytes()
    files["RELEASE_README.md"] = (
        "# Component 1 Research Code and Completed Results\n\n"
        "Contains current experiment code, Component 1 Python source, the blank "
        "participant-study kit and completed evaluation summary metrics. It is a "
        "research supplement to the R26-IT-076 repository, not a standalone MERN "
        "application bundle. Use that repository for the complete app and exporter "
        "dependencies. Install research/component1/requirements.txt in a compatible "
        "Python environment.\n\n"
        "The supplied results cover 173 completed held-out securities, 27 recorded "
        "failures and two development stocks. Per-security summaries and failure "
        "reasons are under research/component1/artifacts/paper_v3_verified/. "
        "Run experiments/aggregate_results.py from research/component1 to rebuild "
        "the aggregate tables. No new training is needed to aggregate saved metrics.\n\n"
        "Raw vendor OHLCV histories, model weights, credentials and participant "
        "responses are not distributed. Repeating training requires lawful source "
        "data; the source manifest preserves the original cutoff and fingerprints. "
        "The participant study has not been conducted.\n\n"
        "For anonymous review, do not cite this identifying repository URL. Follow "
        "the selected venue's anonymous-supplement policy.\n"
    ).encode()
    files["SHA256SUMS"] = "".join(
        f"{hashlib.sha256(data).hexdigest()}  {name}\n"
        for name, data in sorted(files.items())).encode()
    with zipfile.ZipFile(CODE_ZIP, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            archive.writestr(name, data)
    (RELEASES / "SHA256SUMS").write_text("".join(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n"
        for path in sorted(RELEASES.glob("*.zip"))))
    (PUBLIC / "SHA256SUMS").write_text("".join(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(PUBLIC)}\n"
        for path in sorted(PUBLIC.rglob("*"))
        if path.is_file() and path.name != "SHA256SUMS"))
    print("Public summaries:", PUBLIC)
    print("Code and results archive:", CODE_ZIP)


if __name__ == "__main__":
    main()
