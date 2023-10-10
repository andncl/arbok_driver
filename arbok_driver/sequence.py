import math
from typing import Union

from qcodes.validators import Arrays

from .gettable_parameter import GettableParameter
from .sample import Sample
from .sequence_base import SequenceBase
from .sweep import Sweep

class Sequence(SequenceBase):
    """Class describing a Sequence in an OPX program"""
    def __init__(
            self,
            name: str,
            sample: Sample,
            param_config: dict | None = None,
            **kwargs
            ) -> None:
        """
        Constructor method for Sequence
        
        Args:
            name (str): Name of the sequence
            sample (Sample): Sample object describing the device in use
            param_config (dict): Config containing all sequence params and their
                initial values and units0
            **kwargs: Key word arguments for InstrumentModule 
        """
        super().__init__(name, sample, param_config, **kwargs)
        self.program = None
        self.parent_sequence = self
        self.stream_mode = "pause_each"
        self._sweeps = []
        self._gettables = []
        self._sweep_size = 1
        self._setpoints_for_gettables = ()


    @property
    def sweeps(self) -> list:
        """List of Sweep objects for `SubSequence`"""
        return self._sweeps

    @property
    def gettables(self) -> list:
        """List of `GettableParameter`s for data acquisition"""
        return self._gettables

    @property
    def sweep_size(self) -> int:
        """Dimensionality of sweep axes"""
        self._sweep_size = int(
            math.prod([sweep.length for sweep in self.sweeps]))
        return self._sweep_size

    def set_sweeps(self, *args) -> None:
        """ 
        Sets the given sweeps from its dict type arguments. Each argument 
        creates one sweep axis. Each dict key, value pair is sweept concurrently
        along this axis.

        Args:
            *args (dict): Arguments of type dict with SequenceParameters as keys 
                and np arrays as setpoints. All values (arrays) must have same 
                length!
        """
        if not all([isinstance(sweep_dict, dict) for sweep_dict in args]):
            raise TypeError("All arguments need to be of type dict")
        self._sweeps = []
        for sweep_dict in args:
            self._sweeps.append(Sweep(sweep_dict))
        self._setpoints_for_gettables = ()
        for sweep in self.sweeps:
            for param, setpoints in sweep.config_to_register.items():
                param.vals = Arrays(shape=(len(setpoints),))
                self._setpoints_for_gettables += (param,)

    def register_gettables(self, *args) -> None:
        """
        Registers GettableParameters that will be retreived during measurement
        
        Args:
            *args (GettableParameter): Parameters to be measured
        """
        if not all(isinstance(param, GettableParameter) for param in args):
            raise TypeError("All arguments need to be of type dict")
        if not all(param.sequence.parent_sequence == self for param in args):
            raise AttributeError(
                f"Not all GettableParameters belong to {self.name}")
        self._gettables = list(args)
        for i, gettable in enumerate(self.gettables):
            gettable.batch_size = self.sweep_size
            gettable.can_resume = True if i==(len(self.gettables)-1) else False
            gettable.setpoints = self._setpoints_for_gettables
            gettable.vals = Arrays(
                shape = tuple(sweep.length for sweep in self.sweeps))
        self.sweeps.reverse()
