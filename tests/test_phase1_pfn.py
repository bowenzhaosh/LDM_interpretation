import numpy as np
import pytest
import torch

from pfn_dag_verify.phase1_pfn import _infer


class _ToyPFN(torch.nn.Module):
    def forward(self, context, query, token):
        base = context.sum(dim=(1, 2)) + query.sum(dim=(1, 2)) + token.float()
        logits = (
            base[:, None, None]
            + torch.arange(100, dtype=context.dtype, device=context.device)[
                None, None, :
            ]
            / 100.0
        )
        return logits


def test_native_scorer_is_batch_and_context_row_invariant():
    rng = np.random.default_rng(9)
    contexts = rng.normal(size=(7, 30, 4))
    queries = rng.normal(size=(7, 3))
    model = _ToyPFN().eval()
    singleton = _infer(model, contexts, queries, 1, torch.device("cpu"))
    batched = _infer(model, contexts, queries, 4, torch.device("cpu"))
    permuted = _infer(
        model, contexts[:, np.roll(np.arange(30), 7)], queries, 4, torch.device("cpu")
    )
    np.testing.assert_allclose(singleton, batched, atol=1e-6, rtol=0)
    np.testing.assert_allclose(singleton, permuted, atol=1e-5, rtol=0)


def test_native_scorer_rejects_nonfinite_inputs():
    contexts = np.zeros((1, 30, 4), dtype=np.float64)
    contexts[0, 0, 0] = np.nan
    with pytest.raises(RuntimeError, match="non-finite input"):
        _infer(
            _ToyPFN(),
            contexts,
            np.zeros((1, 3), dtype=np.float64),
            1,
            torch.device("cpu"),
        )
