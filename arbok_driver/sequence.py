"""Module containing sequence class"""
import math
from collections import Counter

import numpy as np
from qcodes.validators import Arrays
import matplotlib.pyplot as plt

from .gettable_parameter import GettableParameter
from .sequence_parameter import SequenceParameter
from .sample import Sample
from .sequence_base import SequenceBase
from .sweep import Sweep

class Sequence(SequenceBase):
    """Class describing a Sequence in an OPX driver"""
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
        self.driver = None
        self.parent_sequence = self
        self.stream_mode = "pause_each"
        self._input_stream_parameters = []
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

    @property
    def input_stream_parameters(self) -> list:
        """Registered input stream parameters"""
        return self._input_stream_parameters

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
        if not all(isinstance(sweep_dict, dict) for sweep_dict in args):
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
        self._check_given_gettables(args)
        self._gettables = list(args)
        self._configure_gettables()
        self.sweeps.reverse()

    def _configure_gettables(self) -> None:
        """
        Configures all gettables to be measured. Sets batch_size, can_resume,
        setpoints and vals
        """
        for i, gettable in enumerate(self.gettables):
            gettable.batch_size = self.sweep_size
            gettable.can_resume = True if i==(len(self.gettables)-1) else False
            gettable.setpoints = self._setpoints_for_gettables
            gettable.vals = Arrays(
                shape = tuple(sweep.length for sweep in self.sweeps))

    def _check_given_gettables(self, gettables: list) -> None:
        """
        Check validity of given gettables
        
        Args:
            gettables (list): List of GettableParameters

        Raises:
            TypeError: If not all gettables are of type GettableParameter
            AttributeError: If not all gettables belong to self
        """
        all_gettable_parameters = all(
            isinstance(gettable, GettableParameter) for gettable in gettables)
        all_gettables_from_self = all(
            gettable.sequence.parent_sequence == self for gettable in gettables)
        if not all_gettable_parameters:
            raise TypeError(
                f"All args need to be GettableParameters, Are: {gettables}")
        if not all_gettables_from_self:
            raise AttributeError(
                f"Not all GettableParameters belong to {self.name}")

    def get_sequence_path(self):
        """Returns its name since sequence is the top level sequence"""
        return self.name

    def add_input_stream_parameter(self, parameter) -> None:
        """Adds given parameter to input stream parameters"""
        if not isinstance(parameter, SequenceParameter):
            raise TypeError(
                "Parameter must be of type SequenceParameter, "
                f"is: {type(parameter)}"
                )
        self._input_stream_parameters.append(parameter)

    def advance_input_streams(self, new_value_dict: dict) -> None:
        """
        Advances all input streams by one step with the new given values
        
        Args:
            new_value_dict (dict): Dictionary containing all parameters and 
                their new values
        """
        if Counter(new_value_dict.keys()) != Counter(self.input_stream_parameters):
            raise KeyError(
                "Given value dict must contain all input stream parameters"
                f"given are: {new_value_dict.keys()}.\n Required are: "
                f"{self.input_stream_parameters}"
                )
        for parameter in self.input_stream_parameters:
            self.driver.qm_job.advance_input_stream(
                name = parameter.full_name
            )

    def plot_current_histograms(self, gettables: list = None, bins: int = 50):
        """
        Plots current histograms for all gettables
        
        Args:
            gettables (list, GettableParameter): Parameter or list of parameters
                to plot histograms for
            bins (int): Number of bins for histogram
        """
        gettable_list = []
        if gettables is None:
            gettable_list = self.gettables
        elif isinstance(gettables, GettableParameter):
            gettable_list = [gettables]
        else:
            raise ValueError(
                f"""gettables must be of type GettableParameter or list with 
                Gettable parameters is: {type(gettables)}"""
                )
        fig, ax = plt.subplots(
            len(self.gettables),
            figsize = (5, 3*len(self.gettables))
            )

        ALPHA = 0.8
        for i, gettable in enumerate(gettable_list):
            current_gettable = getattr(
                gettable.instrument, f"{gettable.name}")
            current_vals = np.array(current_gettable.get_all(), dtype = float)
            ax[i].hist(
                current_vals,
                bins = bins,
                label = current_gettable.name,
                alpha = ALPHA,
                color = 'black'
                )
            ax[i].set_xlabel("SET read current histogram")
            ax[i].set_ylabel("counts")
            ax[i].grid()
            ax[i].legend()
        fig.tight_layout()
        return fig, ax
