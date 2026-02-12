""" Module containing GettableParameter class """
from __future__ import annotations
from typing import TYPE_CHECKING, Sequence

from qm import qua
import numpy as np

from .gettable_parameter_base import GettableParameterBase

if TYPE_CHECKING:
    from arbok_driver.read_sequence import ReadSequence
    from qm.qua._expressions import QuaVariable, QuaArrayVariable
    from qcodes.parameters.parameter_base import ParameterBase
    from .sequence_parameter import SequenceParameter

class GettableParameterMulti(GettableParameterBase):
    """
    GettableParameterMulti class handling high dimensional results from an
    abstract readout
    """
    def __init__(
            self,
            name: str,
            read_sequence: ReadSequence,
            var_type: int | bool | qua.fixed,
            internal_setpoints: Sequence[SequenceParameter],
            **kwargs
            ) -> None:
        """
        Constructor class for ReadSequence class
        Args:
            name (dict): name of the GettableParameter
            read_sequence (ReadSequence): Readout class summarizing data streams
                and variables
            var_type (int | bool | qua.fixed): type of qua variable to be saved
            setpoints (Sequence[SequenceParameter]): sequence of setpoints
            **kwargs
        """
        super().__init__(
            name = name,
            read_sequence = read_sequence,
            var_type = var_type,
            **kwargs
            )
        self.reset_measuerement_attributes()
        self.internal_setpoints: tuple[SequenceParameter] = tuple(internal_setpoints)
        self.qua_var_index: QuaVariable | None = None
        self.length: int = self.get_length()

    def qua_declare_variables(self) -> None:
        """Declares the qua variables and streams for this gettable"""
        self.length = self.get_length()
        self.qua_var_index: QuaVariable = qua.declare(int)
        self.qua_result_array: QuaArrayVariable = qua.declare(
            self.var_type,
            size = self.length
        )
        self.qua_stream = qua.declare_stream()

    def qua_save_variables(self) -> None:
        """Saves acquired results to qua stream"""
        with qua.for_(
            var = self.qua_var_index,
            init = 0,
            cond = self.qua_var_index < self.length,
            update = self.qua_var_index + 1
            ):
            qua.save(
                self.qua_result_array[self.qua_var_index], self.qua_stream)

    def reset_measuerement_attributes(self):
        """Resets all job specific attributes"""
        super().reset_measuerement_attributes()
        self.qua_result_array = None

    def configure_from_measurement(self, setpoints: tuple[ParameterBase, ...]):
        """
        Configures the gettable parameter from the measurement object.
        This method sets the sweep dimensions, batch size, and snaked shape
        based on the sweeps defined in the measurement.
        """
        super().configure_from_measurement(
            setpoints + self.internal_setpoints
        )

    def get_length(self) -> int:
        """Calculates length of internal sweep"""
        return int(np.prod([len(p.get()) for p in self.internal_setpoints]))
