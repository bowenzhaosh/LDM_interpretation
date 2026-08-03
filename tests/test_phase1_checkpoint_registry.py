import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_phase1_registry_is_exact_complete_and_filename_bound():
    registry = json.loads(
        (ROOT / "config" / "phase1_checkpoint_registry.json").read_text()
    )
    assert registry["schema_version"] == 1
    assert registry["model_definition_sha256"] == (
        "22c61ee73a6fb1ea2c8f54d24a8597722e33ca7b562ef5b8ee74d42c38d7f897"
    )
    records = registry["records"]
    expected = {
        (prior, seed, step)
        for prior in ("C", "N")
        for seed in range(3)
        for step in (20_000, 60_000, 120_000)
    }
    observed = {
        (row["prior"], row["seed"], row["checkpoint_step"]) for row in records
    }
    assert len(records) == 18
    assert observed == expected
    assert len({row["sha256"] for row in records}) == 18
    assert all(len(row["sha256"]) == 64 for row in records)
    assert all(row["planned_total_steps"] == 120_000 for row in records)
    for row in records:
        prefix = f"M4_{row['prior']}_s{row['seed']}_st120000"
        expected_name = (
            f"{prefix}.pt"
            if row["checkpoint_step"] == 120_000
            else f"{prefix}_ck{row['checkpoint_step']}.pt"
        )
        assert row["filename"] == expected_name
        assert row["bytes"] == (
            4_343_220 if row["checkpoint_step"] == 120_000 else 4_344_012
        )
