"""Module containing Observable class"""
import logging
from qm import qua

class ObservableBase:
    """
    Base class for observables for both I and Q readouts and AbstractReadouts
    """
    def __init__(
        self,
        observable_name: str,
        readout,
        ):
        """
        Constructor method for the ObservableBase class
        
        Args:
            observable_name (str): Name of the observable
            readout_point (str): Read
        """
        self.observable = observable_name
        self.readout = readout
        self.gettable = None

        self.qua_var = None
        self.qua_stream = None
        self.qua_buffer = None

        self.qm_elements = None

    def __call__(self):
        """
        Overwrites the default calling behaviour and returns the associated
        gettable to the observable
        """
        return self.gettable

class Observable(ObservableBase):
    """
    Observable class inheriting from ObservableBase. Helper class for readout.
    points
    """
    def __init__(
        self,
        element_name,
        element,
        observable_name,
        readout_point,
        ):
        """
        Constructor method for the Observable class. Inherits from 
        ObservableBase.

        Args:
            element_name (str): Name of the measured element
            element (str): Quantum machines element to measure on
            observable_name (str): Name of the observable
            readout_point (ReadoutPoint): ReadoutPont on which observable is
                registered
        """
        super().__init__(observable_name, readout = readout_point)
        self.qua_type = qua.fixed
        self.element_name = element_name
        self.element = element
        self.name = f"{self.element_name}_{observable_name}"
        self.full_name = f"{self.readout.sequence.short_name}"
        self.full_name += f"__{self.readout.name}__{self.name}"
        self.signal = self.readout.signal
        self.qm_elements = list(dict.fromkeys(self.signal.readout_elements.values()))

class AbstractObservable(ObservableBase):
    """Observable class for AbstractRadouts"""
    def __init__(
        self,
        observable_name: str,
        abstract_readout,
        signal: str,
        qua_type,
        adc_trace: bool = False,
        ):
        """
        Constructor method for AbstractObservable
        
        Args:
            observable_name (str): Name of the observable
            readout (AbstractReadout): Abstract readout under which the
                observable will be registered
            signal (Signal): Signal to be stored on
            qua_type (type): type of variable to create
            adc_stream (bool): Whether an ADC stream is saved. Defaults to False
        """
        super().__init__(observable_name, readout = abstract_readout)
        self.name = observable_name
        self.qua_type = qua_type
        self.adc_trace = adc_trace

        self.signal = getattr(self.readout.sequence, signal)
        self.qm_elements = list(dict.fromkeys(self.signal.readout_elements.values()))
        self.full_name = f"{self.readout.sequence.short_name}"
        self.full_name += f"__{self.signal.name}__{self.name}"
        self.signal.observables[self.full_name] = self
        setattr(self.signal, self.name, self)
        logging.debug(
            "Added observable %s to signal %s", self.name, self.signal.name)
