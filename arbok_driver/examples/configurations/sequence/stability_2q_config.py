from arbok_driver.parameter_types import (
    Time, Voltage, List, Int)
from arbok_driver.examples.readout_classes import (
    DcChoppedReadout
)
from arbok_driver.examples.sequences import StabilityMap

stability_2q_conf = {
    'sequence': StabilityMap,
    'parameters': {
        'iteration': {
            'type': Int,
            'value': 0
            },
        'gate_elements': {
            'type': List,
            'value': [
                'P1', 'J1',
                'P2'
                ]
            },
        't_pre_chop': {
            'type': Time,
            'value': int(50e3/4)
            },
        'v_level': {
            'type': Voltage,
            'elements': {
                'P1': 0.3, 'J1': -0.7,
                'P2': 0.6,
                }
            },
        'v_home': {
            'type': Voltage,
            'elements': {
                'P1': 0, 'J1': 0,
                'P2': 0,
                }
            },
        },
    'signals': ['chopped_readouts'],
    'readout_groups': {
        'chop': {
            'stability': {
                'readout_class': DcChoppedReadout,
                'signal': 'chopped_readouts',
                'kwargs': {
                    'readout_qua_elements': {
                        'p1p2': 'SET1',
                    }
                },
                'parameters': {
                    'v_chop': {
                        'type': Voltage,
                        'elements': {
                            'P1': 0.01,
                            'P2': -0.01,
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
