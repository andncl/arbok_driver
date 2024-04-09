from arbok_driver import Sample
from .configuration import qm_config

opx_scale = 2
divider_config = {
    'gate_1': {
        'division': 1*opx_scale,
    },
    'gate_2': {
        'division': 1*opx_scale,
    },
    'readout_element': {
        'division': 1*opx_scale
    }
}

dummy_sample = Sample('dummy_sample', qm_config, divider_config)