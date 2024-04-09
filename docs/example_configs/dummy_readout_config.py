dummy_readout_config = {
    'parameters': {
        't_between_measurements': {
            'value': 50,
            'unit': 'cycles',
        }
    },
    'signals':{
        'qubit1':{
            'elements': {
                'sensor1': 'readout_element',
            },
            'readout_points': {
                'ref': {
                    'method': 'average',
                    'desc':'reference point',
                    'observables': ['I', 'Q', 'IQ'],
                    'save_values': True
                },
                'read': {
                    'method': 'average',
                    'desc': 'redout point',
                    'observables': ['I', 'Q', 'IQ'],
                    'save_values': True
                }
            }
        },
    },
    'readout_groups': {
        'difference': {
            'qubit1__diff': {
                'method': 'difference',
                'name': 'diff',
                'args': {
                    'signal': 'qubit1',
                    'minuend': 'qubit1.ref.sensor1_IQ',
                    'subtrahend': 'qubit1.read.sensor1_IQ',
                },
            },
        }
    },
}