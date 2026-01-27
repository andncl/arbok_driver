"""Module containing example measurement configuration for eight dot device"""
from qcodes import validators

from arbok_driver.parameter_types import (
    Time, Voltage, Frequency, List, Int
)
from arbok_driver.examples.configurations import (
    square_pulse_conf,
    square_pulse_scalable_conf
)
device_config = {
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
                'P2',
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
                'Q3', 'Q4',
                'Q5', 'Q6',
                'Q7', 'Q8',
                ]
        },
        'f_larmor': {
            'type': Frequency,
            'label': 'resonance frequency',
            'elements': {
                'Q1': int(27.85e6),
                'Q2': int(30.1e6),
                'Q3': int(26.7e6),
                'Q4': int(48.1e6),
                'Q5': int(45.342e6),
                'Q6': int(50.340e6),
                'Q7': int(45.4e6),
                'Q8': int(42.8e6),
                'qe1': int(1e6),
            },
        },
        't_2pi': {
            'type': Time,
            'label': '2pi time',
            'elements': {
                'Q1': int(2500),
                'Q2': int(2283),
                'Q3': int(1000),
                'Q4': int(1600),
                'Q5': int(1642),
                'Q6': int(1604),
                'Q7': int(1136),
                'Q8': int(1923),
            },
        },
        'v_home': {
            'type': Voltage,
            'label': 'home voltage point',
            'elements': {
                'P1': 0, 'J1': 0,
                'P2': 0, 'J2': 0,
                'P3': 0, 'J3': 0,
                'P4': 0, 'J4': 0,
                'P5': 0, 'J5': 0,
                'P6': 0, 'J6': 0,
                'P7': 0, 'J7': 0,
                'P8': 0,
            }
        },
        'v_control': {
            'type': Voltage,
            'label': 'control voltage point',
            'elements': {
                'P1': 0.0, 'J1': -0.05,
                'P2': 0.0, 'J2': -0.,
                'P3': 0.2, 'J3': -0.2,
                'P4': 0.2, 'J4': 0,
                'P5': -0.017, 'J5': -0.19,
                'P6': 0.017, 'J6': 0,
                'P7': 0, 'J7': -0.63,
                'P8': 0, #'LCB': 0
            }
        },
        'v_exchange': {
            'type': Voltage,
            'label': 'Exchange voltage point',
            'elements': {
                'P1': 0, 'J1': 0.01,
                'P2': 0, 'J2': 0.02,
                'P3': 0, 'J3': 0.03,
                'P4': 0, 'J4': 0.04,
                'P5': 0, 'J5': 0.05,
                'P6': 0, 'J6': 0.06,
                'P7': 0, 'J7': 0.07,
                'P8': 0,
            }
        },
    },
    'default_sequence_configs': {
        'square_pulse': {
            'config': square_pulse_conf
        },
        'square_pulse_custom': {
            'config': square_pulse_scalable_conf
        },
    },
}
