"""Module containing generic CPMG sequence"""
from dataclasses import dataclass
from qm import qua
from arbok_driver import SubSequence, ParameterClass
from arbok_driver.parameter_types import Int, List

from .x_strict import Xstrict
from .y_strict import Ystrict

@dataclass(frozen=True)
class StateProjParameters(ParameterClass):
    gate_elements: List
    qubit_elements: List
    projection: Int

class StateProjection(SubSequence):
    """
    Class containing parameters and sequence cpmg sequence
    """
    PARAMETER_CLASS = StateProjParameters
    arbok_params: StateProjParameters

    def __init__(
            self,
            parent,
            name: str,
            target_qubit: str,
            sequence_config: dict | None = None,
    ):
        """S
        Constructor method for 'StateProjection' class

        Args:
            name (str): name of sequence
            device  (Device): Device class for physical device
            config (dict): config containing pulse parameters
        """
        self.target_qubit = target_qubit
        config = {
            'parameters':{
                'projection':{'value': 2, 'type': Int},
            }
        }
        super().__init__(parent, name, config)
        self.elements = list(self.arbok_params.gate_elements.get())
        self.elements += list(self.arbok_params.qubit_elements.get())

        self.add_submodule('x', Xstrict(
            self, 'x', target_qubit, control_pulse = 'control_pi2'))
        self.add_submodule('x_minus', Xstrict(
            self, 'x_minus', target_qubit, control_pulse = 'control_minus_pi2'))
        self.add_submodule('x_pi', Xstrict(
            self, 'x_pi', target_qubit, control_pulse = 'control_pi'))
        self.add_submodule('y', Ystrict(
            self, 'y', target_qubit, control_pulse = 'control_pi2'))
        self.add_submodule('y_minus', Ystrict(
            self, 'y_minus', target_qubit, control_pulse = 'control_minus_pi2'))

        self.single_qubit_gates = self.sub_sequences
        self._sub_sequences = []

    def qua_declare(self):
        """
        Declares all sequence variables, a sweep index and the half wait time
        for before and after the Y pulse. Further the pi/2 and pi times for
        each qubit are saved in variables
        """
        super().qua_declare()
        if not self.arbok_params.projection.qua_sweeped:
            self.arbok_params.projection.qua_var = qua.declare(
                int, int(self.arbok_params.projection.qua))
        for sub_sequence in self.single_qubit_gates:
            sub_sequence.qua_declare()

    def qua_before_sequence(self):
        """
        Qua code being executed before the sequence. Calculating pulse times for
        respective single qubit gates
        """
        for sub_sequence in self.single_qubit_gates:
            sub_sequence.qua_before_sequence()

    def qua_sequence(self):
            self._qua_state_projection()

    def _qua_state_projection(self):
        """QUA sequence for state projection"""
        qua.align(*self.elements)
        with qua.switch_(self.arbok_params.projection.qua_var, unsafe=True):
            ### Positive X direction
            with qua.case_(0):
                self.y.qua_gate()
            ### Negative X direction
            with qua.case_(1):
                self.y_minus.qua_gate()
            ### Positive Y direction
            with qua.case_(2):
                self.x.qua_gate()
            ### Negative Y direction
            with qua.case_(3):
                self.x_minus.qua_gate()
            ### Positive Z direction
            with qua.case_(4):
                pass
            ### Negative Z direction
            with qua.case_(5):
                self.x_pi.qua_gate()
