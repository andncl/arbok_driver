"""Module containing Observable class"""

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
        self.element_name = element_name
        self.element = element
        self.name = f"{self.element_name}_{observable_name}"
        self.full_name = f"{self.readout.name}__{self.name}"
        self.signal = self.readout.signal

class AbstractObservable(ObservableBase):
    """Observable class for AbstractRadouts"""
    def __init__(
        self,
        observable_name: str,
        abstract_readout,
        signal: str
        ):
        """
        Constructor method for AbstractObservable
        
        Args:
            observable_name (str): Name of the observable
            readout (AbstractReadout): Abstract readout under which the
                observable will be registered
            signal 
        """
        super().__init__(observable_name, readout = abstract_readout)
        self.name = observable_name
        self.signal = getattr(self.readout.sequence, signal)
        self.full_name = f"{self.signal.name}__{self.name}"
        self.signal.observables[self.full_name] = self
        setattr(self.signal, self.name, self)
