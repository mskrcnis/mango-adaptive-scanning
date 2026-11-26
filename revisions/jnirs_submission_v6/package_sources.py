#!/usr/bin/env python3
"""Package and independently compile the journal sources without research data.

Uses only the Python standard library plus bash, pdfLaTeX, BibTeX, pdfinfo and
pdftotext. Source files are never edited. Reports live outside the source ZIP to
avoid self-referential package hashes. Run again after finalizing author inputs
or review reports; a previous hash-bound visual review then needs reassessment.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile


HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "output"
RESULTS = HERE / "results"
ARCHIVE = OUTPUT / "Mango_JNIRS_LaTeX_Source.zip"
FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)
ROOT_SUFFIXES = {".tex", ".cls", ".sty", ".bst", ".bib", ".bbl"}
REQUIRED_DOCUMENTS = [
    "build_pdfs.sh", "README.md", "AUTHOR_INPUTS.md", "cover_letter.txt",
    "supplement_description.txt", "scope.md", "guideline_audit.md",
    "bibliography_audit.md", "content_review.md", "literature_and_claims_review.md",
    "literature_expansion_sources.md", "prepare_figures.py", "verify_package.py",
    "package_sources.py",
]
OPTIONAL_DOCUMENTS = ["RUN_STATUS.md", "verification_report.md"]
# Explicit allowlist: packaging reports and historical render snapshots are not
# source dependencies. These reports describe the final review/provenance state.
REVIEW_JSONS = [
    "verification.json", "v5_preservation_before.json", "conversion_map.json",
    "independent_content_review.json", "main_visual_review.json",
    "supplement_visual_review.json", "bibliography_verification.json",
    "bibliography_review.json", "final_content_review.json",
]
PDF_DELIVERIES = {
    "main": "Mango_JNIRS_Manuscript.pdf",
    "supplement": "Mango_JNIRS_Supplement.pdf",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def snapshot_sources() -> dict[str, bytes]:
    paths = {p for p in HERE.iterdir() if p.is_file() and p.suffix in ROOT_SUFFIXES}
    for name in REQUIRED_DOCUMENTS:
        path = HERE / name
        if not path.is_file():
            raise FileNotFoundError(f"Required package source missing: {name}")
        paths.add(path)
    paths.update(HERE / name for name in OPTIONAL_DOCUMENTS if (HERE / name).is_file())
    directory_suffixes = {
        "template_provenance": {".cls", ".bst", ".json", ".md", ".txt"},
        "figure_data": {".csv", ".json", ".md", ".txt"},
        "evidence_tables": {".csv", ".json", ".md", ".txt"},
    }
    for directory, suffixes in directory_suffixes.items():
        folder = HERE / directory
        if not folder.is_dir():
            raise FileNotFoundError(f"Required source directory missing: {directory}")
        for path in folder.rglob("*"):
            if path.is_file() and path.suffix in suffixes and not any(
                    part.startswith(".") or part in {"__pycache__", "tmp", "cache"}
                    for part in path.relative_to(folder).parts):
                paths.add(path)
    for number in range(1, 5):
        path = HERE / "figures" / f"Figure_{number}.pdf"
        if not path.is_file():
            raise FileNotFoundError(f"Required figure missing: {path.name}")
        paths.add(path)
    paths.update(RESULTS / name for name in REVIEW_JSONS if (RESULTS / name).is_file())
    required_sources = {"main.tex", "supplement.tex", "references.bib", "sagej.cls",
                        "sagev.bst", "jnirs_sagev.bst", "jnirs_review.sty",
                        "main.bbl", "supplement.bbl"}
    names = {p.relative_to(HERE).as_posix() for p in paths}
    if missing := required_sources - names:
        raise FileNotFoundError(f"Required LaTeX dependencies missing: {sorted(missing)}")
    for path in paths:
        if path.is_symlink():
            raise ValueError(f"Symlinks are not packaged: {path}")
    return {p.relative_to(HERE).as_posix(): p.read_bytes()
            for p in sorted(paths, key=lambda item: item.relative_to(HERE).as_posix())}


def zip_bytes(sources: dict[str, bytes]) -> bytes:
    manifest = "".join(f"{sha(data)}  {name}\n" for name, data in sorted(sources.items()))
    entries = {**sources, "SHA256SUMS": manifest.encode("utf-8")}
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9, allowZip64=True) as archive:
        for name, data in sorted(entries.items()):
            info = zipfile.ZipInfo(name, date_time=FIXED_ZIP_TIME)
            info.create_system = 3
            mode = 0o755 if name.endswith((".sh", ".py")) else 0o644
            info.external_attr = (0o100000 | mode) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data, compresslevel=9)
    return stream.getvalue()


def verify_archive(data: bytes) -> dict[str, str]:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        if names != sorted(set(names)):
            raise ValueError("Archive names are not unique and sorted")
        for name in names:
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or "\\" in name:
                raise ValueError(f"Unsafe archive path: {name}")
        if bad := archive.testzip():
            raise ValueError(f"Archive CRC failure: {bad}")
        manifest = {}
        for line in archive.read("SHA256SUMS").decode("utf-8").splitlines():
            digest, name = line.split("  ", 1)
            if not re.fullmatch(r"[a-f0-9]{64}", digest) or name in manifest:
                raise ValueError("Invalid or duplicate manifest entry")
            manifest[name] = digest
        if set(manifest) != set(names) - {"SHA256SUMS"}:
            raise ValueError("Internal manifest does not cover exactly the archive sources")
        for name, digest in manifest.items():
            if sha(archive.read(name)) != digest:
                raise ValueError(f"Manifest checksum failure: {name}")
        if any(info.date_time != FIXED_ZIP_TIME for info in archive.infolist()):
            raise ValueError("Non-deterministic archive timestamp")
        figures = [name for name in names if name.endswith(".pdf")]
        expected = [f"figures/Figure_{n}.pdf" for n in range(1, 5)]
        if figures != expected:
            raise ValueError(f"Unexpected PDFs in source archive: {figures}")
    return manifest


def pdf_details(path: Path) -> dict:
    info = subprocess.run(["pdfinfo", str(path)], check=True, capture_output=True,
                          text=True).stdout
    page_match = re.search(r"^Pages:\s+(\d+)\s*$", info, re.M)
    if page_match is None:
        raise ValueError(f"Unable to count PDF pages: {path}")
    text = subprocess.run(["pdftotext", "-layout", str(path), "-"], check=True,
                          capture_output=True).stdout
    data = path.read_bytes()
    return {"sha256": sha(data), "bytes": len(data), "pages": int(page_match[1]),
            "layout_text_sha256": sha(text), "layout_text_bytes": len(text)}


def copy_submission_files() -> list[dict]:
    destination = OUTPUT / "submission_files"
    destination.mkdir(parents=True, exist_ok=True)
    copies = [(OUTPUT / "pdf" / name, name) for name in PDF_DELIVERIES.values()]
    copies += [(HERE / "figures" / f"Figure_{n}.pdf", f"Figure_{n}.pdf")
               for n in range(1, 5)]
    copies += [(HERE / "cover_letter.txt", "Cover_Letter.txt"),
               (HERE / "supplement_description.txt", "Supplement_Description.txt")]
    result = []
    for source, name in copies:
        target = destination / name
        shutil.copyfile(source, target)
        source_hash = sha(source.read_bytes())
        if sha(target.read_bytes()) != source_hash:
            raise ValueError(f"Submission copy checksum mismatch: {name}")
        result.append({"path": target.relative_to(HERE).as_posix(),
                       "source": source.relative_to(HERE).as_posix(),
                       "sha256": source_hash, "bytes": target.stat().st_size})
    return result


def main() -> int:
    OUTPUT.mkdir(exist_ok=True)
    RESULTS.mkdir(exist_ok=True)
    report = {"status": "failed", "passed": False, "submission_performed": False,
              "scope": "Source-archive integrity and isolated document reproduction; "
                       "no research fitting, numerical re-evaluation, or submission.",
              "archive": ARCHIVE.relative_to(HERE).as_posix(), "checks": {}}
    inventory = {"status": "failed", "submission_performed": False,
                 "archive": ARCHIVE.relative_to(HERE).as_posix()}
    started = time.monotonic()
    try:
        for command in ["bash", "pdflatex", "bibtex", "pdfinfo", "pdftotext"]:
            if not shutil.which(command):
                raise RuntimeError(f"Required compilation/verification command unavailable: {command}")
        sources = snapshot_sources()
        data = zip_bytes(sources)
        report["checks"]["deterministic_archive_bytes"] = data == zip_bytes(sources)
        manifest = verify_archive(data)
        report["checks"]["internal_manifest_verified"] = True
        report["checks"]["sorted_members_and_fixed_timestamps"] = True
        report["checks"]["only_four_named_figure_pdfs_in_source_zip"] = True
        temporary_archive = ARCHIVE.with_suffix(".zip.tmp")
        temporary_archive.write_bytes(data)
        temporary_archive.replace(ARCHIVE)
        report["archive_sha256"] = sha(data)
        report["archive_bytes"] = len(data)
        report["source_file_count"] = len(sources)
        report["archive_member_count"] = len(sources) + 1
        inventory.update({"archive_sha256": sha(data), "archive_bytes": len(data),
                          "fixed_zip_timestamp": list(FIXED_ZIP_TIME),
                          "source_file_count": len(sources),
                          "archive_member_count": len(sources) + 1,
                          "members": [{"path": name, "sha256": sha(blob), "bytes": len(blob)}
                                      for name, blob in sorted(sources.items())],
                          "internal_manifest_sha256": sha("".join(
                              f"{digest}  {name}\n" for name, digest in sorted(manifest.items())
                          ).encode("utf-8"))})
        report["delivered_documents"] = {
            name: pdf_details(OUTPUT / "pdf" / filename)
            for name, filename in PDF_DELIVERIES.items()}
        with tempfile.TemporaryDirectory(prefix="mango-jnirs-build-") as temporary:
            extracted = Path(temporary).resolve()
            project_root = HERE.parents[1].resolve()
            if os.path.commonpath([str(extracted), str(project_root)]) == str(project_root):
                raise RuntimeError("Isolated build directory must be outside the research workspace")
            report["isolated_build_directory"] = str(extracted)
            report["checks"]["build_directory_outside_research_workspace"] = True
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                archive.extractall(extracted)
            for name, digest in manifest.items():
                if sha((extracted / name).read_bytes()) != digest:
                    raise ValueError(f"Extracted source manifest mismatch: {name}")
            report["checks"]["extracted_manifest_verified"] = True
            environment = os.environ.copy()
            # Prevent an inherited project-specific TeX search path from masking
            # a missing packaged dependency. Use only packaged and system files.
            removed = [key for key in ("TEXINPUTS", "BIBINPUTS", "BSTINPUTS")
                       if environment.pop(key, None) is not None]
            report["cleared_tex_search_environment_variables"] = removed
            report["build_command"] = ["bash", "build_pdfs.sh"]
            result = subprocess.run(report["build_command"], cwd=extracted,
                                    env=environment, capture_output=True, text=True,
                                    timeout=600)
            report["build_returncode"] = result.returncode
            log = result.stdout + result.stderr
            for document in PDF_DELIVERIES:
                build_log = extracted / "results" / f"{document}.build.log"
                if build_log.is_file():
                    log += f"\n--- {document}.build.log ---\n" + build_log.read_text(errors="replace")
            (RESULTS / "isolated_compilation.log").write_text(log)
            report["build_log"] = "results/isolated_compilation.log"
            if result.returncode:
                raise RuntimeError(f"Isolated compilation failed (exit {result.returncode}); see build log")
            report["checks"]["isolated_compilation_succeeded"] = True
            report["comparisons"] = {}
            for document, filename in PDF_DELIVERIES.items():
                rebuilt = pdf_details(extracted / "output" / "pdf" / filename)
                delivered = report["delivered_documents"][document]
                current = pdf_details(OUTPUT / "pdf" / filename)
                comparison = {"rebuilt": rebuilt, "delivered": delivered,
                              "exact_pdf_bytes_match": rebuilt["sha256"] == delivered["sha256"],
                              "extracted_layout_text_matches": rebuilt["layout_text_sha256"] == delivered["layout_text_sha256"],
                              "page_count_matches": rebuilt["pages"] == delivered["pages"],
                              "delivered_pdf_unchanged_during_packaging": current == delivered}
                report["comparisons"][document] = comparison
                for check in ["exact_pdf_bytes_match", "extracted_layout_text_matches",
                              "page_count_matches", "delivered_pdf_unchanged_during_packaging"]:
                    report["checks"][document + "_" + check] = comparison[check]
            report["checks"]["packaged_sources_unchanged_during_build"] = all(
                (HERE / name).is_file() and sha((HERE / name).read_bytes()) == digest
                for name, digest in manifest.items())
        report["isolated_directory_removed_after_check"] = not extracted.exists()
        if not all(report["checks"].values()):
            failed = [name for name, passed in report["checks"].items() if not passed]
            raise RuntimeError(f"Package verification failed: {failed}")
        inventory["submission_files"] = copy_submission_files()
        report["checks"]["named_submission_copies_verified"] = True
        report["status"] = inventory["status"] = "pass"
        report["passed"] = True
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
        inventory["error"] = report["error"]
    report["elapsed_seconds"] = round(time.monotonic() - started, 3)
    write_json(RESULTS / "isolated_compilation.json", report)
    write_json(RESULTS / "package_inventory.json", inventory)
    print(json.dumps({key: report.get(key) for key in
                      ["status", "archive", "archive_sha256", "source_file_count", "error"]}, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
