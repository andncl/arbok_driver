""" Module containing GettableParameter class """
from __future__ import annotations
from typing import Type, TYPE_CHECKING

from .gettable_parameter_base import GettableParameterBase

if TYPE_CHECKING:
    from arbok_driver.read_sequence import ReadSequence
    from qm.qua._expressions import QuaVariable

class GettableParameter(GettableParameterBase):
    """
    Gettableparameter class handling scalar results from an abstract readout
    """
    hw_result_var: QuaVariable

    def __init__(
            self,
            name: str,
            read_sequence: ReadSequence,
            var_type: Type[int | bool | float],
            **kwargs
            ) -> None:
        """
        Constructor class for ReadSequence class
        Args:
            name (dict): name of the GettableParameter
            read_sequence (ReadSequence): Readout class summarizing data streams
                and variables
            var_type (int | bool | float): Type of hardware variable to use
            **kwargs
        """
        super().__init__(
            name = name,
            read_sequence = read_sequence,
            var_type = var_type,
            **kwargs
            )
        self.reset_measuerement_attributes()

    def fpga_declare_variables(self):
        """Declares the hardware variable and stream for this gettable"""
        backend = self.read_sequence.backend
        self.hw_result_var = backend.declare(self.var_type)
        self.hw_stream = backend.declare_stream()

    def fpga_save_variables(self):
        """Saves acquired results to stream"""
        backend = self.read_sequence.backend
        backend.save(self.hw_result_var, self.hw_stream)

    @property
    def qua_result_var(self):
        """Deprecated: use hw_result_var instead."""
        return self.hw_result_var

    @qua_result_var.setter
    def qua_result_var(self, value):
        """Deprecated: use hw_result_var instead."""
        self.hw_result_var = value

    def set_raw(self, *args, **kwargs) -> None:
        """Empty abstract `set_raw` method. Parameter not meant to be set"""
        raise NotImplementedError("GettableParameters are not meant to be set")

    def reset_measuerement_attributes(self):
        """Resets all job specific attributes"""
        super().reset_measuerement_attributes()
        self.hw_result_var = None
