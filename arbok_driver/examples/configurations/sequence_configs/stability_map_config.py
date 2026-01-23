from arbok_driver.parameter_types import (
    Time, Voltage, List, Int)
from arbok_driver.examples.readout_classes import (
    DcChoppedReadout
)
from arbok_driver.examples.sub_sequences import StabilityMap

stability_map_config = {
    'sequence': StabilityMap,
    'parameters': {
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
                'P8'
                ]
            },
        't_pre_chop': {
            'type': Time,
            'value': int(50e3/4)
            },
        'v_level': {
            'type': Voltage,
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
        'v_home': {
            'type': Voltage,
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
                        'p7p8': 'SET2',
                    }
                },
                'parameters': {
                    'v_chop': {
                        'type': Voltage,
                        'elements': {
                            'P1': 0.01,
                            'P2': -0.01,
                            'P7': 0.01,
                            'P8': -0.01,
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

