"""Module containing threshold readout helper"""
from dataclasses import dataclass

from qm import qua
from arbok_driver import (
    AbstractReadout,
    ReadSequence,
    Signal,
    ParameterClass
)

from arbok_driver.parameter_types import Voltage

@dataclass(frozen=True)
class ThresholdParameters(ParameterClass):
    threshold: Voltage

class Threshold(AbstractReadout):
    """Helper class enabling threshold readout from a given signal"""
    PARAMETER_CLASS = ThresholdParameters
    arbok_params: ThresholdParameters

    def __init__(
        self,
        name: str,
        read_sequence: ReadSequence,
        signal: Signal,
        save_results: bool,
        parameters: dict,
        charge_readout: str,
        ):
        """
        Constructor method of `Threshold` readout helper
        
        Args:
            name (str): Name of readout
            read_sequence (arbok_driver.ReadSequence): ReadSequence performing the
                abstract readout
            signal (arbok_driver.Signal): Signal to be measured
            save_results (bool): Whether to save the results
            parameters (dict): Parameters to be added to the read sequence
            charge_readout (str): Name of the charge readout gettable
        """
        super().__init__(
            name = name,
            read_sequence = read_sequence,
            signal = signal,
            save_results = save_results,
            parameters = parameters
        )
        self.signal = signal
        self.charge_readout = charge_readout
        self._create_gettables()

    def qua_measure(self):
        """
        Measures the given gettables and assigns the result to the variables.
        Only to be called within qua.program() context manager!
        """
        qua.assign(
            self.state_gettable.qua_result_var,
            self.current_gettable.qua_result_var > self.arbok_params.threshold.qua
            )

    def _create_gettables(self):
        """Creates the gettables for the given readout"""
        self.current_gettable = self.get_gettable_from_path(self.charge_readout)

        self.state_gettable = self.create_gettable(
            gettable_name = self.name,
            var_type = bool,
        )
        self.gettables[self.state_gettable.full_name] = self.state_gettable
