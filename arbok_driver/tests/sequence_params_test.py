# import pytest

from arbok_driver.sequence import SequenceBase, Sample
from arbok_driver import SubSequence

import logging
logging.basicConfig(
    filename = 'logs/sequence_params_test.txt',
    filemode = 'w',
    encoding = 'utf-8',
    level = logging.DEBUG
)

square_conf2 = {
    'sticky_elements': {
        'value': ['gate_1', 'gate_2', 'gate_3', 'gate_4'],
        'unit': 'gate label'
    },
    'vHome': {
        'unit': 'V',
        "label": 'Default voltage point during the sequence',
        'elements': {
            'gate_1': 0,
            'gate_2': 0,
            'gate_3': 0,
            'gate_4': 0,
        }
    },
    'vSquare': {
        'unit': 'V',
        "label": 'Voltage amplitude of square pulse',
        'elements': {
            'gate_1': 0.1,
            'gate_2': -0.05,
            'gate_3': 0.08,
            'gate_4': 0.25,
        }
    },
    't_square_pulse': {
        'value': 100,
        'unit': 'cycles'
    },
    'ramp_time': {
        'value': 20,
        'unit': 'cycles'
    },
}

# class TestSample:
#     elements = None
# testSample = TestSample()
import sys
sys.path.append('../docs/example_configs')
from configuration import qm_config
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
sequenceBase = SubSequence('square_conf2', dummy_sample, square_conf2)
sequenceBase.print_readable_snapshot()
