import argparse
import hashlib
import json
import os
import subprocess
import tarfile
import tempfile
from pathlib import Path

import numpy as np

from .integrity import EXPECTED_IDENTITIES, verify_prediction_ledger
from .provenance import (
    MEMORY_CAP_BYTES,
    RAW_CAP_BYTES,
    WALL_CAP_SECONDS,
    repository_root,
    verify_panel_lock,
    verify_run_lock,
)
from .registry import sha256_file
from .storage import load_numeric_npz, write_json_atomic


def _canonical_tree_hash(entries: list[dict]) -> str:
    payload = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def _tracked_files(root: Path) -> list[str]:
    output = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout
    values = [value.decode("utf-8") for value in output.split(b"\0") if value]
    if not values:
        raise ValueError("repository has no tracked replay files")
    return sorted(values)


def _safe_run_path(run_dir: Path, relative: str) -> Path:
    path = (run_dir / relative).resolve()
    if not path.is_relative_to(run_dir.resolve()):
        raise ValueError(f"run manifest path escapes the run directory: {relative}")
    return path


def _archive_member_name(entry: dict) -> str:
    return f"{entry['scope']}/{entry['path']}"


def _entry_source(entry: dict, *, root: Path, run_dir: Path) -> Path:
    if entry["scope"] == "repository":
        return (root / entry["path"]).resolve()
    if entry["scope"] == "run":
        return _safe_run_path(run_dir, entry["path"])
    raise ValueError("unknown archive entry scope")


def _create_archive(
    *, manifest_path: Path, entries: list[dict], root: Path, run_dir: Path
) -> Path:
    bundle_dir = root / "bundles"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    tree_hash = json.loads(manifest_path.read_text())["content_tree_sha256"]
    archive_path = bundle_dir / f"{tree_hash}.tar"
    with tempfile.NamedTemporaryFile(
        dir=bundle_dir, prefix=tree_hash + ".", suffix=".tmp", delete=False
    ) as handle:
        temporary = Path(handle.name)
    try:
        with tarfile.open(temporary, mode="w") as archive:
            sources = [("sealed_manifest.json", manifest_path)]
            sources.extend(
                (_archive_member_name(entry), _entry_source(entry, root=root, run_dir=run_dir))
                for entry in entries
            )
            for member_name, source in sources:
                info = tarfile.TarInfo(member_name)
                info.size = source.stat().st_size
                info.mode = 0o644
                info.mtime = 0
                info.uid = 0
                info.gid = 0
                info.uname = ""
                info.gname = ""
                with source.open("rb") as source_handle:
                    archive.addfile(info, source_handle)
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, archive_path)
        descriptor = os.open(bundle_dir, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return archive_path


def _verify_archive(
    *, archive_path: Path, manifest_path: Path, entries: list[dict]
) -> None:
    if not archive_path.is_file():
        raise FileNotFoundError("content-addressed replay archive is missing")
    expected = {"sealed_manifest.json": sha256_file(manifest_path)}
    expected.update({_archive_member_name(entry): entry["sha256"] for entry in entries})
    with tarfile.open(archive_path, mode="r") as archive:
        members = archive.getmembers()
        if {member.name for member in members} != set(expected) or len(members) != len(expected):
            raise ValueError("replay archive member set is incomplete or duplicated")
        for member in members:
            if not member.isfile():
                raise ValueError(f"replay archive contains a non-file member: {member.name}")
            source = archive.extractfile(member)
            if source is None:
                raise ValueError(f"cannot read replay archive member: {member.name}")
            digest = hashlib.sha256()
            while chunk := source.read(1024 * 1024):
                digest.update(chunk)
            if digest.hexdigest() != expected[member.name]:
                raise ValueError(f"replay archive member hash mismatch: {member.name}")


def _run_files(run_dir: Path) -> tuple[list[str], dict, dict]:
    panel_path = run_dir / "panel.npz"
    prediction_dir = run_dir / "predictions"
    derived_dir = run_dir / "derived"
    panel, prediction_ledger, _ = verify_prediction_ledger(
        panel_path=panel_path, prediction_dir=prediction_dir
    )
    verify_panel_lock(panel)
    derived_ledger_path = derived_dir / "derived_ledger.json"
    derived_ledger = json.loads(derived_ledger_path.read_text())
    if (
        derived_ledger.get("schema_version") != 1
        or derived_ledger.get("scientific") is not True
        or derived_ledger.get("panel_sha256") != sha256_file(panel_path)
        or derived_ledger.get("prediction_ledger_sha256")
        != sha256_file(prediction_dir / "prediction_ledger.json")
    ):
        raise ValueError("derived ledger identity mismatch during sealing")
    records = derived_ledger.get("records")
    if not isinstance(records, list) or len(records) != 64:
        raise ValueError("derived ledger must contain exactly 64 records")
    identities = {
        (int(record["seed"]), int(record["step"]), int(record["bank_index"]))
        for record in records
    }
    if identities != EXPECTED_IDENTITIES:
        raise ValueError("derived ledger identities are incomplete")
    derived_names = set()
    for record in records:
        path = derived_dir / str(record["path"])
        if (
            not path.is_file()
            or path.stat().st_size != int(record["size"])
            or sha256_file(path) != record["sha256"]
        ):
            raise ValueError(f"derived file mismatch during sealing: {path.name}")
        derived_names.add(path.name)
    if {path.name for path in derived_dir.glob("derived_*.npz")} != derived_names:
        raise ValueError("derived directory contains a stale or missing shard")
    relative = [
        "panel.npz",
        "panel.json",
        "predictions/prediction_ledger.json",
        "derived/derived_ledger.json",
    ]
    relative.extend(
        f"predictions/{record['path']}" for record in prediction_ledger["records"]
    )
    relative.extend(f"derived/{record['path']}" for record in records)
    if len(relative) != 132 or len(set(relative)) != 132:
        raise AssertionError("sealed run file set is incomplete or duplicated")
    for item in relative:
        if not _safe_run_path(run_dir, item).is_file():
            raise FileNotFoundError(item)
    return sorted(relative), prediction_ledger, derived_ledger


def seal_run(run_dir: Path, out_path: Path | None = None) -> dict:
    root = repository_root()
    commit, run_lock_hash, _ = verify_run_lock(root)
    run_dir = run_dir.resolve()
    out_path = run_dir / "sealed_manifest.json" if out_path is None else out_path.resolve()
    if out_path.parent != run_dir:
        raise ValueError("sealed manifest must live at the run root")
    run_files, prediction_ledger, derived_ledger = _run_files(run_dir)
    panel = load_numeric_npz(run_dir / "panel.npz")
    panel_commit, _ = verify_panel_lock(panel)
    if panel_commit != commit:
        raise ValueError("sealed run commit differs from clean HEAD")

    panel_metadata = json.loads((run_dir / "panel.json").read_text())
    wall_seconds = float(panel_metadata["wall_seconds"])
    wall_seconds += float(prediction_ledger["wall_seconds"])
    wall_seconds += float(derived_ledger["wall_seconds"])
    peak_rss_bytes = max(
        int(panel_metadata["peak_rss_bytes"]),
        int(prediction_ledger["peak_rss_bytes"]),
        int(derived_ledger.get("peak_rss_bytes", 0)),
    )

    entries = []
    for relative in _tracked_files(root):
        path = root / relative
        if not path.is_file():
            raise ValueError(f"tracked replay input is not a regular file: {relative}")
        entries.append(
            {
                "scope": "repository",
                "path": relative,
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    for relative in run_files:
        path = _safe_run_path(run_dir, relative)
        entries.append(
            {
                "scope": "run",
                "path": relative,
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    entries.sort(key=lambda value: (value["scope"], value["path"]))
    raw_bytes = sum(entry["size"] for entry in entries if entry["scope"] == "run")
    if wall_seconds > WALL_CAP_SECONDS:
        raise RuntimeError("BLOCKED_COST: actual wall-clock limit exceeded")
    if peak_rss_bytes > MEMORY_CAP_BYTES:
        raise RuntimeError("BLOCKED_COST: actual memory limit exceeded")
    if raw_bytes > RAW_CAP_BYTES:
        raise RuntimeError("BLOCKED_COST: actual raw-storage limit exceeded")
    manifest = {
        "schema_version": 1,
        "scientific": True,
        "commit_sha": commit,
        "run_lock_sha256": run_lock_hash,
        "panel_sha256": sha256_file(run_dir / "panel.npz"),
        "content_tree_sha256": _canonical_tree_hash(entries),
        "files": entries,
        "resource_totals": {
            "wall_seconds": wall_seconds,
            "peak_rss_bytes": peak_rss_bytes,
            "raw_bytes": raw_bytes,
            "wall_cap_seconds": WALL_CAP_SECONDS,
            "memory_cap_bytes": MEMORY_CAP_BYTES,
            "raw_cap_bytes": RAW_CAP_BYTES,
        },
    }
    write_json_atomic(out_path, manifest)
    _create_archive(
        manifest_path=out_path,
        entries=entries,
        root=root,
        run_dir=run_dir,
    )
    verify_sealed_manifest(out_path)
    return manifest


def verify_sealed_manifest(path: Path) -> dict:
    root = repository_root()
    commit, run_lock_hash, _ = verify_run_lock(root)
    path = path.resolve()
    run_dir = path.parent
    manifest = json.loads(path.read_text())
    if (
        manifest.get("schema_version") != 1
        or manifest.get("scientific") is not True
        or manifest.get("commit_sha") != commit
        or manifest.get("run_lock_sha256") != run_lock_hash
        or manifest.get("panel_sha256") != sha256_file(run_dir / "panel.npz")
    ):
        raise ValueError("sealed manifest identity mismatch")
    expected_run_files, prediction_ledger, derived_ledger = _run_files(run_dir)
    expected_repository_files = _tracked_files(root)
    entries = manifest.get("files")
    if not isinstance(entries, list):
        raise ValueError("sealed manifest file list is missing")
    observed_run = sorted(
        entry["path"] for entry in entries if entry.get("scope") == "run"
    )
    observed_repository = sorted(
        entry["path"] for entry in entries if entry.get("scope") == "repository"
    )
    if observed_run != expected_run_files or observed_repository != expected_repository_files:
        raise ValueError("sealed manifest does not contain the exact replay tree")
    for entry in entries:
        if entry.get("scope") == "run":
            target = _safe_run_path(run_dir, entry["path"])
        elif entry.get("scope") == "repository":
            target = (root / entry["path"]).resolve()
            if not target.is_relative_to(root):
                raise ValueError("repository manifest path escapes the root")
        else:
            raise ValueError("sealed manifest contains an unknown scope")
        if (
            not target.is_file()
            or target.stat().st_size != int(entry.get("size", -1))
            or sha256_file(target) != entry.get("sha256")
        ):
            raise ValueError(f"sealed content mismatch: {entry.get('path')}")
    ordered = sorted(entries, key=lambda value: (value["scope"], value["path"]))
    if manifest.get("content_tree_sha256") != _canonical_tree_hash(ordered):
        raise ValueError("sealed content-tree hash mismatch")
    archive_path = root / "bundles" / f"{manifest['content_tree_sha256']}.tar"
    _verify_archive(
        archive_path=archive_path,
        manifest_path=path,
        entries=ordered,
    )
    totals = manifest.get("resource_totals", {})
    panel_metadata = json.loads((run_dir / "panel.json").read_text())
    computed_wall = (
        float(panel_metadata["wall_seconds"])
        + float(prediction_ledger["wall_seconds"])
        + float(derived_ledger["wall_seconds"])
    )
    computed_peak = max(
        int(panel_metadata["peak_rss_bytes"]),
        int(prediction_ledger["peak_rss_bytes"]),
        int(derived_ledger.get("peak_rss_bytes", 0)),
    )
    computed_raw = sum(
        int(entry["size"]) for entry in entries if entry["scope"] == "run"
    )
    if (
        float(totals.get("wall_seconds", np.inf)) != computed_wall
        or int(totals.get("peak_rss_bytes", -1)) != computed_peak
        or int(totals.get("raw_bytes", -1)) != computed_raw
    ):
        raise ValueError("sealed resource totals do not match the replay tree")
    if (
        computed_wall > WALL_CAP_SECONDS
        or computed_peak > MEMORY_CAP_BYTES
        or computed_raw > RAW_CAP_BYTES
    ):
        raise RuntimeError("BLOCKED_COST: sealed resources exceed a scientific cap")
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    result = seal_run(args.run_dir)
    print(
        json.dumps(
            {
                "content_tree_sha256": result["content_tree_sha256"],
                "files": len(result["files"]),
                "resource_totals": result["resource_totals"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
