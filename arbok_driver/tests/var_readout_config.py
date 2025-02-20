from arbok_driver.parameter_types import Voltage, String

var_readout_config = {    
    'parameters' : {
        'dummy_var': {
            'type': Voltage,
            'value': 0.,
            # 'is_variable': True
            'validator': None,
            'scale': None
        },
    },
    'signals':{
        'var_signal':{},
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
                            'var_signal': 'dummy_var',
                        }
                    },
                }
            },
        },
    }
}