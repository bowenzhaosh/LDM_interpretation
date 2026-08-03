import numpy as np

N_CONTEXT = 30
N_BINS = 100
BIN_EDGES = np.linspace(-8.0, 8.0, N_BINS + 1, dtype=np.float64)
BIN_CENTERS = 0.5 * (BIN_EDGES[:-1] + BIN_EDGES[1:])
NULL_TOKEN = 2

SIGMA_LO = 0.6
SIGMA_HI = 1.5
RHO_MAG_LO = 0.4
RHO_MAG_HI = 0.8
A_VALID_LO = -1.5
A_VALID_HI = 1.5
B_VALID_LO = 0.30
B_VALID_HI = 1.30
AL40_SKEW = 4.0

BASE_MODEL_CONFIG = {
    "d_model": 256,
    "d_ff": 512,
    "n_heads": 4,
    "n_layers": 2,
}

