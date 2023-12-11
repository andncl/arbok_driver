"""Module containing ReadoutPoint class"""
import logging
from qm import qua

class ReadoutPoint:
    """
    Class managing voltage signal readout points of OPX
    """
    def __init__(
            self,
            point_name: str,
            signal: any,
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
        self.point_name = point_name
        self.name = f"{self.signal.name}__{point_name}"
        self.config = config
        self.description = self.config["desc"]
        self._qua_variable_names = []
        self._qua_stream_names = []
        self._observables = []
        self.valid_observables = ('I', 'Q')
        self._add_qua_variable_attributes(self.signal.readout_elements)

    def qua_declare_variables(self):
        """Declares all neccessary qua variables"""
        qua_name_zip = zip(self._qua_variable_names, self._qua_stream_names)
        for var_name, stream_name in qua_name_zip:
            setattr(self, var_name, qua.declare(qua.fixed))
            setattr(self, stream_name, qua.declare_stream())
            logging.debug(
                "Assigned qua-var %s to point %s", var_name, self.name)
            logging.debug(
                "Assigned qua-stream %s to point %s", var_name, self.name)

    def _add_qua_variable_attributes(self, readout_elements: dict):
        """
        Adds attributes to the readout point that will later store the qua 
        variables. This is primarily done to make all streams and qua varables
        visible before we ask to generate the qua script
        
        Args:
            readout_elements (dict): Readout elements from which to read
        """
        for name, _ in readout_elements.items():
            for observable in self.config["observables"]:
                self._check_observable_validity(observable)
                var_name = f"{name}_{observable}"
                stream_name = f"{var_name}_stream"
                self._observables.append(observable)
                self._qua_variable_names.append(var_name)
                self._qua_stream_names.append(stream_name)
                logging.debug(
                    "Added qua-var-name %s to point %s", var_name, self.name)
                logging.debug(
                    "Added qua-stream-name %s to point %s", var_name, self.name)

    def _check_observable_validity(self, observable):
        """Checks if observable is valid"""
        if observable not in self.valid_observables:
            raise ValueError(
                f"Given observable {observable} not valid."
                f"Must be in {self.valid_observables}")

    def qua_measure_and_save(self):
        """Measures and saves qua variables"""
        qua.align()
        self._qua_measure()
        self._qua_save_vars()
        qua.align()

    def _qua_measure(self):
        """Measures I and Q at the given read point"""
        for name, qm_element in self.signal.readout_elements.items():
            self._check_IQ_qua_vars(name)
            var_I = getattr(self, f"{name}_I")
            var_Q = getattr(self, f"{name}_Q")
            qua.measure(
                qua.demod.full('x', var_I),
                qua.demod.full('y', var_Q),
                pulse = 'measure',
                element = qm_element,
                stream = None,
                )
            if 'IQ' in self.config["observables"]:
                qua.assign(getattr(self, f"{name}_IQ"), var_I + var_Q)

    def _qua_save_vars(self):
        """Saves streams after measurement"""
        for name, _ in self.signal.readout_elements.items():
            self._check_IQ_qua_vars(name)
            qua.save(
                getattr(self, f"{name}_I"),
                getattr(self, f"{name}_I_stream")
                )
            qua.save(
                getattr(self, f"{name}_Q"),
                getattr(self, f"{name}_Q_stream")
                )
            if 'IQ' in self.config["observables"]:
                qua.save(
                    getattr(self, f"{name}_IQ"),
                    getattr(self, f"{name}_IQ_stream")
                    )

    def _check_IQ_qua_vars(self, name):
        """
        Validates that mandatory attributes for IQ measurements that store qua
        variables exist
        
        Args:
            name (str): Name of the readout element
        """
        if not hasattr(self, f"{name}_I") or not hasattr(self, f"{name}_I"):
            raise AttributeError(
                f"{self.name} does not have I and Q variable"
                )
    def save_streams(self):
        """Saves streams and buffers of streams"""
        sweep_size = self.signal.sequence.parent_sequence.sweep_size
        for name, _ in self.signal.readout_elements.items():
            full_name = f"{self.name}_{name}"
            I_buffer = getattr(self, f"{name}_I_stream").buffer(sweep_size)
            Q_buffer = getattr(self, f"{name}_Q_stream").buffer(sweep_size)
            I_buffer.save(f"{full_name}_I_buffer")
            Q_buffer.save(f"{full_name}_Q_buffer")
            getattr(self, f"{name}_I_stream").save_all(f"{full_name}_I")
            getattr(self, f"{name}_Q_stream").save_all(f"{full_name}_Q")

hanswurscht = {
    'signals':{
        'p1p2':{
            'element': {
                'set1': 'SDC1',
            },
            'readout_points': {
                'ref': {
                    'desc':'reference point in 3-1 region',
                    'observables': ['I', 'Q', 'IQ']
                },
                'read': {
                    'desc':'psb region of between 4-0 and 3-1 region',
                    'observables': ['I', 'Q', 'IQ']
                }
            }
        },
        'p3p4':{
            'element': {
                'set1': 'SDC1',
                'set2': 'SDC2'
            },
            'readout_points': {
                'ref': {
                    'desc':'reference point in 3-1 region',
                    'observables': ['I', 'Q', 'IQ']
                },
                'read': {
                    'desc':'psb region of between 4-0 and 3-1 region',
                    'observables': ['I', 'Q', 'IQ']
                }
            }
        },
        'p5p6':{
            'element': {
                'set2': 'SDC2'
            },
            'read_points': {
                'ref': {
                    'desc':'reference point in 3-1 region',
                    'observables': ['I', 'Q', 'IQ'],
                    'save': True
                },
                'read': {
                    'desc':'psb region of between 4-0 and 3-1 region',
                    'observables': ['I', 'Q', 'IQ'],
                    'save': True
                }
            }
        },
    },
    'readout_groups': {
        'difference': {
            'p1p2_diff': {
                'method': 'difference',
                'name': 'diff',
                'signal': 'p1p2',
                'args': {
                    'minuend': 'p1p2.ref.set1',
                    'subtrahend': 'p1p2.read.set1',
                    'observables': ['IQ'] 
                },
            },
            'p5p6_diff': {
                'method': 'difference',
                'name': 'diff',
                'signal': 'p5p6',
                'args': {
                    'minuend': 'p5p6.ref.set2',
                    'subtrahend': 'p5p6.read.set2',
                    'observables': ['IQ'] 
                }
            },
        },
        'spin_readouts': {
            'p1p2_spin_parity': {
                'method': 'threshold',
                'name': 'state',
                'signal': 'p1p2',
                'args': {
                    'charge_readouts': ['p1p2.diff'],
                    'threshold': 0.1
                }
            },
            'p5p6_spin_parity': {
                'method': 'threshold',
                'name': 'state',
                'signal': 'p5p6',
                'args': {
                    'charge_readouts': ['p5p6.diff'],
                    'threshold': 0.1
                }
            },
        }
}
