"""
Module containing configuration of coulomb peak measurement on set1 and set2
"""

from arbok_driver.parameter_types import Voltage, Time, Int, List
from arbok_driver.examples.readout_classes import (
    DcAverage,
    DcChoppedReadout,
)
from arbok_driver.examples.sub_sequences import CoulombPeaks

coulomb_peaks_set1_set2_conf = {
    'sequence': CoulombPeaks,
    'parameters': {
        'set_elements': {
            'type': List,
            'value': ['SET1', 'SET2']
        },
        'gate_elements': {
            'type': List,
            'value': [
                'P1', 'J1',
                'P2', 'J2',
                'P3', 'J3',
                'P4', 'J4',
                'P5', 'J5',
                'P6', 'J6',
                'P7', 'J7',
                'P8',
            ]
        },
        't_wait_after_ramp': {
            'type': Time,
            'value': int(1e6/4)
        },
        't_wait_before_chop': {
            'type': Time,
            'value': int(100e3/4)
        },
        'v_home': {
            'type': Voltage,
            'elements': {
                'SET1': 0, 'SET2': 0,
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
        'v_set_level': {
            'type': Voltage,
            'elements': {
                'SET1': 0, 'SET2': 0,
                'P1': 0.1, 'J1': 0,
                'P2': 0, 'J2': 0,
                'P3': 0, 'J3': 0,
                'P4': 0, 'J4': 0,
                'P5': 0, 'J5': 0,
                'P6': 0, 'J6': 0,
                'P7': 0, 'J7': 0,
                'P8': 0,
            }
        },
    },
    'signals': ['set1', 'set2', 'chopped_readouts'],
    'readout_groups': {
        'read': {
            'set1': {
                'readout_class': DcAverage,
                'signal': 'set1',
                'kwargs': {
                    'qua_element': 'SET1'
                }
            },
            'set2': {
                'readout_class': DcAverage,
                'signal': 'set2',
                'kwargs': {
                    'qua_element': 'SET2'
                }
            }
        },
        'chop': {
            'stability': {
                'readout_class': DcChoppedReadout,
                'signal': 'chopped_readouts',
                'kwargs': {
                    'readout_qua_elements': {
                        'p1p2': 'SET1',
                        'p7p8': 'SET2',
                    }
                },
                'parameters': {
                    'v_chop': {
                        'type': Voltage,
                        'elements': {
                            'P1': 0.01,
                            'P8': 0.01,
                        }
                    },
                    'n_chops': {
                        'type': Int,
                        'value': 20
                    },
                    'chop_wait': {
                        'type': Time,
                        'value': int(20e3/4)
                    },
                },
            }
        },
    }
}
