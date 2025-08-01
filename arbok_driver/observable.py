"""Module containing Observable class"""
import logging
from qm import qua

class Observable():
    """Observable class for AbstractRadouts"""
    def __init__(
        self,
        observable_name: str,
        abstract_readout,
        signal: str,
        qua_type: int | bool | qua.fixed,
        adc_trace: bool = False,
        ):
        """
        Constructor method for Observable
        
        Args:
            observable_name (str): Name of the observable
            readout (AbstractReadout): Abstract readout under which the
                observable will be registered
            signal (Signal): Signal to be stored on
            qua_type (type): type of variable to create
            adc_stream (bool): Whether an ADC stream is saved. Defaults to False
        """
        self.qua_var = None
        self.qua_stream = None
        self.qua_buffer = None
        self.gettable = None

        self.observable = observable_name
        self.readout = abstract_readout
        self.signal = signal

        self.name = observable_name
        self.qua_type = qua_type
        self.adc_trace = adc_trace

        self.full_name = f"{self.readout.read_sequence.short_name}__{self.name}"
        self.signal.add_observable(self)
        logging.debug(
            "Added observable %s to signal %s", self.name, self.signal.name)

    def __call__(self):
        """
        Overwrites the default calling behaviour and returns the associated
        gettable to the observable
        """
        return self.gettable
