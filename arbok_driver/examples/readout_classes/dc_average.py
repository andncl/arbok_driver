"""Module containing Average child class inheriting from ReadoutPoint"""
from __future__ import annotations
from typing import TYPE_CHECKING

from qm import qua
from arbok_driver import (
    AbstractReadout,
    ReadSequence,
    Signal, 
)

if TYPE_CHECKING:
    from arbok_driver.parameters.gettable_parameter import GettableParameter

class DcAverage(AbstractReadout):
    """
    ReadoutPoint child class providing a `qua_measure` method to measure I and Q
    in a static averaging manner
    """
    def __init__(
            self,
            name: str,
            read_sequence: ReadSequence,
            signal: Signal,
            save_results: bool,
            parameters: dict,
            qua_element: str,
            ):
        """
        Constructor method of ReadoutPoint class
        
        Args:
            point_name (str): Name of readout point
            signal (Signal): Signal corresponding to readout point
            config (dict): List of readout points
        """
        super().__init__(
            name = name,
            read_sequence = read_sequence,
            signal = signal,
            save_results = save_results,
            parameters = parameters
        )
        self.signal = signal
        self.qua_element = qua_element
        self._create_gettables()

    def qua_measure(self):
        """
        Measures I and Q at the given read point in a static averaging manner
        """
        outputs = [
            qua.integration.full('x_const', self.current_gettable.qua_result_var),
            ]
        qua.measure('measure', self.qua_element, None, *outputs)

    def _create_gettables(self):
        self.current_gettable: GettableParameter = self.create_gettable(
            gettable_name = self.name,
            var_type = qua.fixed
        )
