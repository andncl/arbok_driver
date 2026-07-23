"""
Configuration for heralded parity initialization of a qubit pair.

It reuses all voltage points and timings of the bare parity initialization
(`parity_init_conf`) and adds the single extra timing required by
`ParityInitHeralded`: the settle time applied once initialization has been
heralded successfully.
"""
import copy

from arbok_driver.parameter_types import Time
from arbok_driver.examples.sequences.parity_initialization_heralded import (
    ParityInitHeralded
)
from .parity_init_config import parity_init_conf

parity_init_heralded_conf = copy.deepcopy(parity_init_conf)
parity_init_heralded_conf['sequence'] = ParityInitHeralded
parity_init_heralded_conf['parameters']['t_wait_post_init'] = {
    'type': Time,
    'label': 'Settle time after a successful heralding before quantum control',
    'value': int(1e3/4),
}
