"""Module containing configuration for eight dot device"""
from arbok_driver.parameter_types import (
    Time, Voltage, Frequency, Amplitude, List, Int, Radian
)
from qcodes import validators

master_config = {
    'parameters': {
        'iteration': {
            'type': Int,
            'value': int(1),
            'vals': validators.Ints(),
        },
        'gate_elements': {
            'type': List,
            'value': [
                'P1', 'J1',
                'P2', 'J2',
                'P7', 'J7',
                'P8',
            ]
        },
        'readout_elements': {
            'type': List,
            'value': [
                'SET1',
                'SET2',
            ]
        },
        'qubit_elements': {
            'type': List,
            'value': [
                'Q1', 'Q2',
                # 'Q3', 'Q4',
                # 'Q5', 'Q6',
                # 'Q7', 'Q8',
                'qe1','qe2',
                ]
        },
        'f_larmor': {
            'type': Frequency,
            'label': 'resonance frequency',
            'elements': {
                'Q1': int(27.85e6),
                'Q2': int(30.1e6),
            },
        },
    },
    'default_sequence_configs': {
    },
}

