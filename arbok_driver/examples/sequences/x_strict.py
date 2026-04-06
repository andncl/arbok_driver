"""Module containing for strictly timed X single qubit gate"""
from dataclasses import dataclass

from qm import qua

from arbok_driver import SubSequence, ParameterClass
from arbok_driver.parameter_types import String, List

@dataclass(frozen=True)
class XstrictParameters(ParameterClass):
    gate_elements: List
    qubit_elements: List

class Xstrict(SubSequence):
    """
    Class containing parameters and sequence for X(theta) single qubit gate
    """
    PARAMETER_CLASS = XstrictParameters
    arbok_params: XstrictParameters

    def __init__(
            self,
            parent,
            name: str,
            target_qubit: str,
            control_pulse: str,
            sequence_config: dict | None = None,
    ):
        """

    Constructor method for 'X' gate class 
        
        Args:
            name (str): name of sequence
            device  (Device): Device class for physical device
            seq_config (dict): config containing pulse parameters
            target_qubit (str): Target qubit for the gate
        """
        self.target_qubit = target_qubit
        self.control_pulse = control_pulse

        super().__init__(parent, name, sequence_config)
        self.elements = list(self.arbok_params.gate_elements.get())
        self.elements += list(self.arbok_params.qubit_elements.get())


    def qua_sequence(self):
        """QUA sequence to perform qubit X gate with rotation"""
        self.qua_gate()

    def qua_gate(self):
        qua.play(pulse = self.control_pulse, element = self.target_qubit)
