#!/usr/bin/env python3
"""Verify the curated public release without fitting or downloading anything.

Stage the intended public files, run --write-manifest, then stage the resulting
release/release_manifest.json. Default verification also works in a source
archive without Git, checking every manifest entry but not untracked files.
Only the standard library is required. Historical verification records describe
the original workspace; this verifier does not replay omitted research caches.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "release/release_manifest.json"
JNIRS = "revisions/jnirs_submission_v6"
MAX_BYTES = 50_000_000
SCOPE = (
    "Curated public research source, frozen inference bundles, aggregate evidence "
    "and JNIRS manuscript package. Raw spectra, training checkpoints, large "
    "prediction caches, downloaded third-party full texts and local environments "
    "are excluded. This verifies release integrity, not new scientific validation."
)
EXCLUDED_PARTS = {
    ".git", ".venv", ".bootstrap", ".python", ".uv-cache", ".pytest_cache",
    "__pycache__", "tmp", "checkpoints", "external_cache", "attempts", "pdf_qa",
}
EXCLUDED_PREFIXES = (
    "data/raw/", "data/sealed/", "data/processed/", "data/catalog/sources/",
    "data/catalog/qa/",
)
CREDENTIAL_RULES = {
    "github_personal_access_token": rb"\bgithub_pat_[A-Za-z0-9_]{30,}\b",
    "github_token": rb"\bgh[pousr]_[A-Za-z0-9]{30,}\b",
    "aws_access_key": rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b",
    "private_key": rb"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----",
    "slack_token": rb"\bxox[baprs]-[A-Za-z0-9-]{20,}\b",
    "openai_key": rb"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{40,}\b",
    "google_api_key": rb"\bAIza[0-9A-Za-z_-]{35}\b",
    "literal_secret_assignment": (
        rb"(?im)^\s*[\"']?(?:api[_-]?key|access[_-]?token|client[_-]?secret|password)"
        rb"[\"']?\s*[:=]\s*[\"'](?!\$|<|YOUR_|REPLACE_|example|placeholder)"
        rb"[A-Za-z0-9_+/=.-]{20,}[\"']"
    ),
}
PATTERNS = {name: re.compile(pattern) for name, pattern in CREDENTIAL_RULES.items()}
SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ReleaseError(Exception):
    """An integrity or release-scope check failed."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReleaseError(message)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_relative(name: str) -> PurePosixPath:
    require(isinstance(name, str) and bool(name), "Invalid empty release path")
    path = PurePosixPath(name)
    require(not path.is_absolute() and ".." not in path.parts and
            path.as_posix() == name and "\\" not in name and "\x00" not in name,
            "Unsafe or noncanonical release path")
    return path


def path_for(name: str) -> Path:
    relative = safe_relative(name)
    path = ROOT.joinpath(*relative.parts)
    require(not path.is_symlink() and ROOT in path.resolve().parents,
            f"Symlink or escaped release path: {name}")
    require(not any(parent.is_symlink() for parent in path.parents
                    if parent != ROOT and ROOT in parent.parents),
            f"Symlink parent: {name}")
    return path


def excluded_rule(name: str) -> str | None:
    path = safe_relative(name)
    if set(path.parts) & EXCLUDED_PARTS or name.startswith(EXCLUDED_PREFIXES):
        return "excluded_directory"
    low = path.name.lower()
    if (low in {".env", ".netrc", ".npmrc", ".pypirc", "credentials", "credentials.json",
                "secrets.json", "secrets.yaml", "secrets.yml", "id_rsa", "id_ed25519"}
            or low.startswith(".env.") and not low.endswith((".example", ".template"))
            or path.suffix.lower() in {".pem", ".key", ".p12", ".pfx", ".kdbx"}):
        return "credential_filename"
    if name.startswith("data/literature/") and path.suffix.lower() != ".json":
        return "third_party_full_text"
    if name.startswith("data/provenance/") and path.suffix.lower() in {
            ".pdf", ".txt", ".html", ".dat"}:
        return "third_party_source_copy"
    if path.suffix.lower() == ".pyc":
        return "python_cache"
    if low in {"external_predictions.csv", "policy_predictions.csv.gz", "predictions.csv.gz"}:
        return "large_prediction_cache"
    return None


def scan_bytes(name: str, data: bytes) -> None:
    for rule, pattern in PATTERNS.items():
        # Never include the matched value or surrounding source in diagnostics.
        require(pattern.search(data) is None, f"Credential-pattern match: {name} [{rule}]")


def file_bytes(name: str, scan: bool = True) -> bytes:
    rule = excluded_rule(name)
    require(rule is None, f"Excluded tracked path: {name} [{rule}]")
    path = path_for(name)
    require(path.is_file(), f"Missing file: {name}")
    require(path.stat().st_size <= MAX_BYTES, f"File exceeds 50 MB: {name}")
    data = path.read_bytes()
    if scan:
        scan_bytes(name, data)
    return data


def read_json(name: str) -> dict:
    value = json.loads(file_bytes(name))
    require(isinstance(value, dict), f"Expected JSON object: {name}")
    return value


def tracked_files(required: bool = False) -> set[str] | None:
    if not (ROOT / ".git").exists():
        require(not required, "--write-manifest requires a Git checkout with staged files")
        return None
    try:
        top = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], cwd=ROOT, stderr=subprocess.DEVNULL)
        require(Path(top.decode().strip()).resolve() == ROOT, "Unexpected Git checkout root")
        output = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ReleaseError("Unable to enumerate Git-tracked files") from exc
    names = [name.decode("utf-8") for name in output.split(b"\x00") if name]
    require(len(names) == len(set(names)), "Duplicate tracked paths or unresolved Git index")
    require(bool(names), "No tracked files; stage the curated release first")
    return set(names)


def write_manifest() -> None:
    names = tracked_files(required=True) - {MANIFEST}
    files = {}
    for name in sorted(names):
        data = file_bytes(name)
        files[name] = {"sha256": digest(data), "size_bytes": len(data)}
    record = {"schema_version": 1, "scope": SCOPE, "files": files,
              "file_count": len(files), "total_bytes": sum(v["size_bytes"] for v in files.values())}
    path = path_for(MANIFEST)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def verify_release_manifest() -> dict:
    record = read_json(MANIFEST)
    require(record.get("schema_version") == 1 and record.get("scope") == SCOPE,
            "Release manifest schema or scope mismatch")
    files = record.get("files")
    require(isinstance(files, dict) and bool(files) and MANIFEST not in files,
            "Invalid release manifest file map")
    names = tracked_files()
    if names is not None:
        require(names - {MANIFEST} == set(files), "Tracked-file set differs from release manifest")
    total = 0
    for name, expected in files.items():
        data = file_bytes(name)
        require(isinstance(expected, dict) and SHA256.fullmatch(expected.get("sha256", ""))
                and digest(data) == expected["sha256"] and len(data) == expected.get("size_bytes"),
                f"Release hash/size mismatch: {name}")
        total += len(data)
    require(record.get("file_count") == len(files) and record.get("total_bytes") == total,
            "Release manifest totals mismatch")
    return {"passed": True, "files": len(files), "total_bytes": total,
            "tracked_set_checked": names is not None, "credential_scan_passed": True}


def verify_source_zip() -> dict:
    archive_name = f"{JNIRS}/output/Mango_JNIRS_LaTeX_Source.zip"
    file_bytes(archive_name)
    with zipfile.ZipFile(path_for(archive_name)) as archive:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        require(len(names) == len(set(names)) and "SHA256SUMS" in names,
                "Source ZIP has duplicate names or no SHA256SUMS")
        require(sum(entry.file_size for entry in entries) <= 250_000_000,
                "Source ZIP exceeds expected uncompressed size")
        for entry in entries:
            safe_relative(entry.filename)
            require(not entry.is_dir() and entry.file_size <= MAX_BYTES,
                    f"Invalid source ZIP member: {entry.filename}")
            require((entry.external_attr >> 16) & 0o170000 != 0o120000,
                    f"Source ZIP symlink: {entry.filename}")
        require(archive.testzip() is None, "Source ZIP CRC check failed")
        hashes = {}
        for line in archive.read("SHA256SUMS").decode("utf-8").splitlines():
            match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
            require(match is not None, "Invalid source ZIP SHA256SUMS line")
            expected, name = match.groups()
            safe_relative(name)
            require(name not in hashes, "Duplicate source ZIP checksum entry")
            hashes[name] = expected
        require(set(hashes) == set(names) - {"SHA256SUMS"},
                "Source ZIP checksum manifest does not cover exact member set")
        for name, expected in hashes.items():
            data = archive.read(name)
            scan_bytes(f"{archive_name}!{name}", data)
            require(digest(data) == expected, f"Source ZIP internal hash mismatch: {name}")
            current = file_bytes(f"{JNIRS}/{name}")
            require(data == current, f"Source ZIP differs from current source: {name}")
    return {"passed": True, "members_checked": len(hashes), "crc_passed": True,
            "internal_hashes_passed": True, "current_source_bytes_match": True}


def verify_documents() -> dict:
    record = read_json(f"{JNIRS}/results/verification.json")
    require(record.get("passed") is True, "Recorded JNIRS verification did not pass")
    details = record.get("details", {}).get("documents", {})
    results = {}
    for key, name in [("main", "Mango_JNIRS_Manuscript.pdf"),
                      ("supplement", "Mango_JNIRS_Supplement.pdf")]:
        expected = details.get(key, {})
        data = file_bytes(f"{JNIRS}/output/pdf/{name}")
        require(data.startswith(b"%PDF-") and digest(data) == expected.get("sha256")
                and len(data) == expected.get("size_bytes"), f"Recorded PDF hash mismatch: {name}")
        require(data == file_bytes(f"{JNIRS}/output/submission_files/{name}"),
                f"Submission PDF copy differs: {name}")
        results[key] = {"sha256": digest(data), "size_bytes": len(data),
                        "recorded_pages": expected.get("pages")}
    return {"passed": True, "documents": results,
            "page_counts_from_existing_verification_not_reparsed": True}


def verify_frozen_bundles() -> dict:
    candidate = "revisions/candidate_v4/frozen"
    record = read_json(f"{candidate}/manifest.json")
    require(record.get("status") == "frozen" and record.get("schema_version") == 1,
            "Candidate bundle is not frozen schema version 1")
    files = record.get("files")
    require(isinstance(files, dict) and bool(files), "Candidate manifest is empty")
    folder = path_for(f"{candidate}/manifest.json").parent
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob("*")
              if p.is_file() and p.name != "manifest.json"}
    require(actual == set(files), "Candidate bundle member set mismatch")
    for name, expected in files.items():
        require(SHA256.fullmatch(expected) and digest(file_bytes(f"{candidate}/{name}")) == expected,
                f"Candidate bundle hash mismatch: {name}")
    require(record.get("harvest_recommendations_enabled") is False and
            record.get("external_evaluation") is False,
            "Candidate validation/harvest boundary has changed; review release claims")
    require(files.get("models.joblib") == record.get("model_checkpoint_sha256"),
            "Candidate model-checkpoint hash disagrees with bundle map")
    original = read_json("results/frozen/manifest.json")
    hashes = original.get("hashes", {})
    require(isinstance(hashes, dict), "Invalid original frozen manifest")
    included = {name: value for name, value in hashes.items()
                if name.startswith("results/frozen/")}
    require(bool(included), "Original frozen manifest has no bundle files")
    for name, expected in included.items():
        require(SHA256.fullmatch(expected) and digest(file_bytes(name)) == expected,
                f"Original frozen bundle hash mismatch: {name}")
    return {"passed": True, "candidate_files": len(files), "original_bundle_files": len(included),
            "original_external_dependencies_not_checked": len(hashes) - len(included),
            "harvest_recommendations_enabled": False, "candidate_external_evaluation": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-manifest", action="store_true",
                        help="Hash the currently tracked public file set, then verify it")
    parser.add_argument("--output", type=Path,
                        help="Optionally save the report to an untracked path")
    args = parser.parse_args()
    output = args.output.resolve() if args.output else None
    if output is not None:
        tracked = tracked_files()
        protected = set(tracked or ()) | {MANIFEST}
        if (ROOT / MANIFEST).is_file():
            protected.update(read_json(MANIFEST).get("files", {}))
        require(output not in {ROOT / name for name in protected},
                "--output must not overwrite a tracked or manifest-protected source")
    checks = {}
    try:
        if args.write_manifest:
            write_manifest()
        for name, function in [("release_manifest", verify_release_manifest),
                               ("source_zip", verify_source_zip),
                               ("documents", verify_documents),
                               ("frozen_bundles", verify_frozen_bundles)]:
            checks[name] = function()
        result = {"passed": True, "scope": SCOPE, "checks": checks}
    except (ReleaseError, OSError, ValueError, TypeError, KeyError, zipfile.BadZipFile) as exc:
        result = {"passed": False, "scope": SCOPE, "checks": checks,
                  "error": str(exc) if isinstance(exc, ReleaseError)
                  else f"Unable to verify input ({type(exc).__name__})"}
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
