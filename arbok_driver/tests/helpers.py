import numpy as np

def set_sweeps_args(sequence) -> list:
    set_sweeps_args = [
        {
            sequence.dummy_parent_sub.sub_seq1.par1: np.zeros((5), dtype= int),
            sequence.dummy_parent_sub.sub_seq2.par4: np.ones((5)),
        },
        {
            sequence.dummy_parent_sub.sub_seq1.vHome_J1: np.zeros((7), dtype= int)
        },
    ]
    return set_sweeps_args