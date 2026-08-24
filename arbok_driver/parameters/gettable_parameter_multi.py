""" Module containing GettableParameter class """
from __future__ import annotations
from typing import TYPE_CHECKING, Sequence

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
    hw_var_index: QuaVariable[int]
    def __init__(
            self,
            name: str,
            read_sequence: ReadSequence,
            var_type: int | bool | float,
            internal_setpoints: Sequence[SequenceParameter],
            **kwargs
            ) -> None:
        """
        Constructor class for ReadSequence class
        Args:
            name (dict): name of the GettableParameter
            read_sequence (ReadSequence): Readout class summarizing data streams
                and variables
            var_type (int | bool | float): type of hardware variable to be saved
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
        self.length: int = self.get_length()

    def fpga_declare_variables(self) -> None:
        """Declares the hardware variables and streams for this gettable"""
        backend = self.read_sequence.backend
        self.length = self.get_length()
        self.hw_var_index = backend.declare(int)
        self.hw_result_array: QuaArrayVariable = backend.declare(
            self.var_type,
            size=self.length
        )
        self.hw_stream = backend.declare_stream()

    def fpga_save_variables(self) -> None:
        """Saves acquired results to stream"""
        backend = self.read_sequence.backend
        with backend.for_loop(
            variable=self.hw_var_index,
            init=0,
            condition=self.hw_var_index < self.length,
            update=self.hw_var_index + 1
            ):
            backend.save(
                self.hw_result_array[self.hw_var_index], self.hw_stream)

    @property
    def qua_var_index(self):
        """Deprecated: use hw_var_index instead."""
        return self.hw_var_index

    @qua_var_index.setter
    def qua_var_index(self, value):
        """Deprecated: use hw_var_index instead."""
        self.hw_var_index = value

    @property
    def qua_result_array(self):
        """Deprecated: use hw_result_array instead."""
        return self.hw_result_array

    @qua_result_array.setter
    def qua_result_array(self, value):
        """Deprecated: use hw_result_array instead."""
        self.hw_result_array = value

    def reset_measuerement_attributes(self):
        """Resets all job specific attributes"""
        super().reset_measuerement_attributes()
        self.hw_result_array = None

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
