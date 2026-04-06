"""
Module containing sequence that moves to control point
"""
from dataclasses import dataclass

from qm import qua
from arbok_driver import SubSequence, arbok, ParameterClass
from arbok_driver.parameter_types import (
    ParameterMap, Time, Voltage, List
)
@dataclass(frozen=True)
class ToControlPointParameters(ParameterClass):
    qubit_elements: List
    gate_elements: List
    t_ramp_to_control: Time
    t_wait_pre_control: Time
    v_home: ParameterMap[str, Voltage]
    v_control: ParameterMap[str, Voltage]

class ToControlPoint(SubSequence):
    """
    Class containing parameters and seq. for sequence moving to control ppint
    """
    PARAMETER_CLASS = ToControlPointParameters
    arbok_params: ToControlPointParameters

    def __init__(
            self,
            parent,
            name: str,
            sequence_config: dict | None = None
        ):
        """
        Constructor method for 'ToControlPoint' class
        
        Args:
            name (str): name of sequence
            device  (Device): Device class for physical device
            seq_config (dict): config containing pulse parameters
        """
        self.seq_config = sequence_config
        super().__init__(parent, name, self.seq_config)
        self.elements = list(self.arbok_params.gate_elements.get())
        self.elements += list(self.arbok_params.qubit_elements.get())

    def qua_sequence(self):
        """QUA sequence to perform voltage ramp from home to control point"""
        qua.align(*self.elements)
        arbok.ramp(
            elements= self.arbok_params.gate_elements.get(),
            reference = self.arbok_params.v_home,
            target = self.arbok_params.v_control,
            duration = self.arbok_params.t_ramp_to_control,
            operation = 'unit_ramp',
            
            )
        qua.align(*self.elements)
        qua.wait(self.arbok_params.t_wait_pre_control.qua, *self.elements)
        qua.align(*self.elements)
