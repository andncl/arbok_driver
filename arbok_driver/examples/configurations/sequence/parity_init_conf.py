"""
Configuration for a eight quantum dot device initializing the qubits parity state
"""
from arbok_driver.parameter_types import (
    Time, Voltage, List
)

from arbok_driver.examples.sequences.parity_initialization import ParityInit

parity_init_conf = {
    'sequence': ParityInit,
    'parameters': {
        'gate_elements': {
            'type': List,
            'value': [
                'P1', 'J1',
                'P2',
                'P7', 'J7',
                'P8',
                ]
            },
        't_ramp_to_t1': {
            'type': Time,
            'value': int(1e3/4)
            },
        't_wait_at_t1': {
            'type': Time,
            'value': int(200e3/4)
            },
        't_ramp_to_crossing': {
            'type': Time,
            'value': int(1e3/4)
            },
        't_wait_before_crossing': {
            'type': Time, 
            'value': int(9571)
            },
        't_ramp_over_crossing': {
            'type': Time,
            'value': int(141)
            },
        't_wait_after_crossing': {
            'type': Time,
            'value': int(1e3/4)
            },
        'tHomeRamp': {
            'type': Time,
            'value': int(600)
            },
        'v_home': {
            'type': Voltage,
            'elements': {
                    'P1': 0, 'J1': 0,
                    'P2': 0,
                    'P7': 0, 'J7': 0,
                    'P8': 0,
            }
        },
        'v_t1_point': {
            'type': Voltage,
            'elements': {
                    'P1': 0.06, 'J1': -0.085,
                    'P2': -0.06,
                    'P7': -0.07, 'J7': -0.05,
                    'P8': 0.07,
            }
        },
        'v_pre_crossing': {
            'type': Voltage,
            'elements': {
                    'P1': 0.0435, 'J1': -0.05,
                    'P2': -0.0435,
                    'P7': 0.029, 'J7': 0.067,
                    'P8': -0.029,
            }
        },
        'v_delta': {
            'type': Voltage,
            'elements': {
                    'P1': -0.03, 'J1': 0,
                    'P2': 0.03,
                    'P7': -0.02, 'J7': 0,
                    'P8': 0.02,
            }
        },
    }
}