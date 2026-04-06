"""
Module containing sequence that moves home from control point
"""
from dataclasses import dataclass

from qm import qua
from arbok_driver import SubSequence, arbok, ParameterClass
from arbok_driver.parameter_types import (
    Time, List
)

@dataclass(frozen=True)
class GoFromToParameters(ParameterClass):
    t_wait_post_control: Time
    gate_elements: List
    readout_elements: List
    qubit_elements: List

class FromControlPoint(SubSequence):
    """
    Class containing parameters and seq. for sequence moving from control ppint
    """
    PARAMETER_CLASS = GoFromToParameters
    arbok_params: GoFromToParameters

    def __init__(
            self,
            parent,
            name: str,
            sequence_config: dict | None = None
        ):
        """
        Constructor method for 'FromControlPoint' class
        
        Args:
            name (str): name of sequence
            device  (Device): Device class for physical device
            seq_config (dict): config containing pulse parameters
        """
        self.seq_config = sequence_config
        super().__init__(parent, name, self.seq_config)
        self.elements = list(self.arbok_params.gate_elements.get())
        self.elements += list(self.arbok_params.qubit_elements.get())
        self.elements += list(self.arbok_params.readout_elements.get())

    def qua_sequence(self):
        """QUA sequence to perform voltage ramp from control to home point"""
        qua.align(*self.elements)
        arbok.reset_sticky_elements(
            self.arbok_params.gate_elements.get()
        )
        qua.wait(self.arbok_params.t_wait_post_control.qua, *self.elements)
        qua.align(*self.elements)
