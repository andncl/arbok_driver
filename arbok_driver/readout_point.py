"""Module containing ReadoutPoint class"""
from qm import qua
from .signal import Signal

class ReadoutPoint:
    """
    Class managing voltage signal readout points of OPX
    """
    def __init__(
            self,
            name: str,
            signal: Signal,
            config: dict,
            ):
        """
        Constructor method of ReadoutPoint class
        
        Args:
            name (str): Name of the signal
            signal (Signal): Signal corresponding to readout point
            config (dict): List of readout points
        """
        self.signal = signal
        self.name = f"{self.signal.name}__{name}"
        self.config = config
        self.description = self.config["desc"]
        self._streams = []
        self._qua_variables = []
        self.valid_observables = ('I', 'Q')

    def declare_qua_variables(self):
        """Declares all neccessary qua variables"""
        for name, qm_element in self.signal.readout_elements.items():
            for observable in self.config.observables():
                self._check_observable_validity(observable)
                var_name = f"{name}_{observable}"
                stream_name = f"{var_name}_stream"
                setattr(self, var_name, qua.declare(qua.fixed))
                setattr(self, stream_name, qua.declare_stream())
                self._qua_variables.append(getattr(var_name))
                self._streams.append(getattr(stream_name))

    def _check_observable_validity(self, observable):
        """Checks if observable is valid"""
        if observable not in self.valid_observables:
            raise ValueError(
                f"Given observable {observable} not valid."
                f"Must be in {self.valid_observables}")
    def save_streams(self):


        hanswurscht = {
            'signals':{
                'p1p2':{
                    'element': {
                        'set1': 'SDC1',
                    },
                    'read_points': {
                        'ref': {
                            'desc':'point specification (voltages, I,Q, trace ..)',
                            'observables': ['I', 'Q', 'ADC_trace']
                        },
                        'read': {
                            'desc':'point specification (voltages, I,Q, trace ..)',
                            'observables': ['I', 'Q', 'ADC_trace']
                        }
                    }
                },
                'p3p4':{
                    'element': {
                        'set1': 'SDC1',
                        'set2': 'SDC2'
                    },
                    'read_points': {
                        'ref': {
                            'desc':'point specification (voltages, I,Q, trace ..)',
                            'observables': ['I', 'Q', 'ADC_trace']
                        },
                        'read': {
                            'desc':'point specification (voltages, I,Q, trace ..)',
                            'observables': ['I', 'Q', 'ADC_trace']
                        }
                    }
                },
                'p5p6':{
                    'element': {
                        'set2': 'SDC2'
                    },
                    'read_points': {
                        'ref': {
                            'desc':'point specification (voltages, I,Q, trace ..)',
                            'observables': ['I', 'Q', 'ADC_trace']
                        },
                        'read': {
                            'desc':'point specification (voltages, I,Q, trace ..)',
                            'observables': ['I', 'Q', 'ADC_trace']
                        }
                    }
                },
            },
            'charge_readouts': {
                'p1p2_charge': {
                    'method': 'take_diff',
                    'read_points': ['set1_ref', 'set1_read'],
                },
                'p5p6_chopped': {
                    'method': 'take_diff',
                    'args': {
                        'read_points': ['set2_ref', 'set2_read'],
                        'n_chop': 4
                    },
                },
                'p3p4_correlate': {
                    'method': 'correlate',
                    'args': {
                        'charge_reads': ['p5p6_chopped', 'p1p2_charge'],
                    },
                },
            'spin_readouts': {
                'p1p2_spin_parity': {
                    'method': 'threshold',
                    'args': {
                        'charge_readouts': ['p1p2_charge'],
                        'threshold': 0.1
                    }
                }
            }
        }
        }