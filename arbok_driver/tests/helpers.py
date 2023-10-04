import numpy as np

def set_sweeps_args(sequence) -> list:
    set_sweeps_args = [
        {
            sequence.seq1.par1: np.zeros((5)),
            sequence.seq2.par4: np.zeros((5)),
        },
        {
            sequence.seq1.vHome_J1: np.zeros((7))
        },
    ]
    return set_sweeps_args