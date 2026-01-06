""" Module containing GettableParameter class """
from __future__ import annotations
from typing import TYPE_CHECKING

from qm import qua

from .gettable_parameter_base import GettableParameterBase

if TYPE_CHECKING:
    from arbok_driver.read_sequence import ReadSequence
    from qm.qua._expressions import QuaVariable   

class GettableParameter(GettableParameterBase):
    """
    Gettableparameter class handling sclar results from an abstract readout
    """
    def __init__(
            self,
            name: str,
            read_sequence: ReadSequence,
            var_type: int | bool | qua.fixed,
            **kwargs
            ) -> None:
        """
        Constructor class for ReadSequence class
        Args:
            name (dict): name of the GettableParameter
            read_sequence (ReadSequence): Readout class summarizing data streams
                and variables
            var_type (int | bool | qua.fixed): Type of qua variable to use
            **kwargs
        """
        super().__init__(
            name = name,
            read_sequence = read_sequence,
            var_type = var_type,
            **kwargs
            )
        self.reset_measuerement_attributes()
        self.qua_result_var: QuaVariable | None = None

    def qua_declare_variables(self):
        """Saves acquired results to qua stream"""
        self.qua_result_var = qua.declare(self.var_type)
        self.qua_stream = qua.declare_stream()

    def qua_save_variables(self):
        qua.save(self.qua_result_var, self.qua_stream)

    def set_raw(self, *args, **kwargs) -> None:
        """Empty abstract `set_raw` method. Parameter not meant to be set"""
        raise NotImplementedError("GettableParameters are not meant to be set")

    def reset_measuerement_attributes(self):
        """Resets all job specific attributes"""
        super().reset_measuerement_attributes()
        self.qua_result_var = None
