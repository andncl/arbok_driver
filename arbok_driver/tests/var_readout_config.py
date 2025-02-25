from arbok_driver.parameter_types import Voltage, String

var_readout_config = {    
    'parameters' : {
        'dummy_var': {
            'type': Voltage,
            'value': 0.,
            'validator': None,
            'scale': None
        },
    },
    'signals':{
        'varSignal':{},
    },
    'readout_groups': {
        'var_readouts': {
            'var_readout': {
                'method': 'var_readout',
                'name': 'var',
                'params': {
                    'signal_param': {
                        'type': String,
                        'elements': {
                            'varSignal': 'dummy_var',
                        }
                    },
                }
            },
        },
    }
}