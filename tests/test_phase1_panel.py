import numpy as np

from pfn_dag_verify.phase1_panel import split_stream


def _fake_stream(count: int) -> dict[str, np.ndarray]:
    return {
        "contexts": np.arange(count * 30 * 4, dtype=np.float64).reshape(count, 30, 4),
        "queries": np.arange(count * 3, dtype=np.float64).reshape(count, 3),
        "outcomes": np.arange(count, dtype=np.float64),
        "outcome_bins": np.arange(count, dtype=np.int64) % 100,
        "sigmas": np.tile(np.eye(4, dtype=np.float64), (count, 1, 1)),
        "true_orderings": np.arange(count, dtype=np.int64) % 24,
    }


def test_full_stream_is_split_only_after_generation_and_reconstructs_exactly():
    stream = _fake_stream(11)
    shards = split_stream(
        stream,
        prior_code=1,
        draw_index=2,
        evaluation_seed=881013002,
        atom_seeds=[881003101, 881003102, 881003103],
        identity_sha256="ab" * 32,
        nested_half_draw=0,
        nested_half_stop=4,
    )
    assert [len(inputs["row_id"]) for inputs, _ in shards] == [4, 4, 3]
    for bank, (inputs, labels) in enumerate(shards):
        assert np.all(inputs["stream_index"] % 3 == bank)
        assert np.array_equal(inputs["stream_index"] // 3, inputs["shard_local_index"])
        assert np.array_equal(inputs["row_key_sha256"], labels["row_key_sha256"])
        assert not np.any(inputs["nested_half_mask"])
    reconstructed = np.empty_like(stream["contexts"])
    for inputs, _ in shards:
        reconstructed[inputs["stream_index"]] = inputs["contexts"]
    np.testing.assert_array_equal(reconstructed, stream["contexts"])


def test_nested_half_mask_is_frozen_by_draw_and_original_stream_index():
    shards = split_stream(
        _fake_stream(11),
        prior_code=0,
        draw_index=0,
        evaluation_seed=881003000,
        atom_seeds=[881003101, 881003102, 881003103],
        identity_sha256="cd" * 32,
        nested_half_draw=0,
        nested_half_stop=5,
    )
    marked = sorted(
        int(index)
        for inputs, _ in shards
        for index in inputs["stream_index"][inputs["nested_half_mask"] == 1]
    )
    assert marked == [0, 1, 2, 3, 4]
