"""Parity read config p1p2 p7p8 for nova."""
from arbok_driver.parameter_types import (
    Time, Voltage, List, Int
)

from arbok_driver.examples.readout_classes import (
    DcAverage,
    Difference,
    Threshold,
) 

from arbok_driver.examples.sub_sequences.parity_readout import ParityRead

parity_read_conf = {
    'sequence': ParityRead,
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
        't_wait_home_before': {
            'type': Time,
            'label': 'Wait time at the home point before readout',
            'value': int(100e3/4)
            },
        't_wait_pre_read': {
            'type': Time,
            'value': int(100e3/4)
            },
        't_wait_post_read': {
            'type': Time,
            'value': int(20e3/4)
            },
        't_ramp_to_reference':{
            'type': Time,
            'var_type': 'fixed',
            'value': int(25e3/4)
            },
        't_ramp_to_read': {
            'type': Time,
            'value': int(1e3/4)
            },
        't_wait_after_reset': {
            'type': Time,
            'value': int(4e3/4)
            },
        'v_reference': {
            'type': Voltage,
            'label': 'Default voltage point during the sequence',
            'elements': {
                'P1': 0.023, 'J1': -0.02,
                'P2': -0.023,

                'P7': -0.0325, 'J7': 0.005,
                'P8': 0.0325,
                }
            },
        'v_read': {
            'type': Voltage,
            'label': 'Readout voltage point',
            'elements': {
                'P1': 0.025, 'J1': -0.02,
                'P2': -0.025,

                'P7': -0.035, 'J7': 0.005,
                'P8': 0.035,
            }
        },
    },
    'signals': ['p1p2', 'p7p8'],
    'readout_groups': {
        'ref': {
            'p1p2': {
                'readout_class': DcAverage,
                'signal': 'p1p2',
                'kwargs': {
                    'qua_element': 'SET1'
                },
                'params': {
                    'test': {'type': Int, 'value': 1},
                }
            },
            'p7p8': {
                'readout_class': DcAverage,
                'name': 'ref',
                'signal': 'p7p8',
                'kwargs': {
                    'qua_element': 'SET2'
                }
            }
        },
        'read': {
            'p1p2': {
                'readout_class': DcAverage,
                'signal': 'p1p2',
                'kwargs': {
                    'qua_element': 'SET1'
                }
            },
            'p7p8': {
                'readout_class': DcAverage,
                'signal': 'p7p8',
                'kwargs': {
                    'qua_element': 'SET2'
                }
            }
        },
        'diff': {
            'p1p2': {
                'readout_class': Difference,
                'signal': 'p1p2',
                'kwargs': {
                    'minuend': 'parity_read.p1p2.ref__p1p2',
                    'subtrahend': 'parity_read.p1p2.read__p1p2',
                },

            },
            'p7p8': {
                'readout_class': Difference,
                'signal': 'p7p8',
                'kwargs': {
                    'minuend': 'p7p8.ref__p7p8',
                    'subtrahend': 'p7p8.read__p7p8',
                }
            },
        },
        'state': {
            'p1p2': {
                'readout_class': Threshold,
                'signal': 'p1p2',
                'kwargs': {
                    'charge_readout': 'p1p2.diff__p1p2',
                },
                'parameters': {
                    'threshold': {'type': Voltage, 'value': 0.001}
                }
            },
            'p7p8': {
                'readout_class': Threshold,
                'signal': 'p7p8',
                'kwargs': {
                    'charge_readout': 'p7p8.diff__p7p8',
                },
                'parameters': {
                    'threshold': {'type': Voltage, 'value': -0.001}
                }
            },
        },
    },
}