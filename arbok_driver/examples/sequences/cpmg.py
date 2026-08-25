"""Module containing generic CPMG sequence"""
from dataclasses import dataclass

from qm import qua
from qm.qua._expressions import QuaVariable
from qm.qua.lib import Cast

from arbok_driver import SubSequence, arbok, ParameterClass
from arbok_driver.parameter_types import (
    Time, Int, List)

from .x_strict import Xstrict

@dataclass(frozen=True)
class CpmgParameters(ParameterClass):
    gate_elements: List
    qubit_elements: List
    repetitions: Int
    t_equator_wait: Time

class Cpmg(SubSequence):
    """
    Class containing parameters and sequence cpmg sequence
    """
    PARAMETER_CLASS = CpmgParameters
    arbok_params: CpmgParameters

    n_index: QuaVariable
    wait_time_factor: QuaVariable

    def __init__(
        self,
        parent,
        name: str,
        target_qubit: str,
        repetitions: int = 1,
        t_equator_wait: int = int(1e3),
        sequence_config: dict | None = None,
        pulse_type: str = 'control',
    ):
        """
        Constructor method for 'CPMG' class
       
        Args:
            name (str): name of sequence
            device  (Device): Device class for physical device
            config (dict): config containing pulse parameters
        """
        self.target_qubit = target_qubit
        self.pulse_type = pulse_type
        config = {
            'parameters':{
                'repetitions': {'value': repetitions, 'type': Int},
                't_equator_wait': {'value': int(t_equator_wait/4), 'type': Time},
            }
        }
        if sequence_config is None:
            sequence_config = {}
        # config.update(sequence_config)
        super().__init__(parent = parent, name = name, sequence_config = config)
        self.elements = list(self.arbok_params.gate_elements.get())
        self.elements += list(self.arbok_params.qubit_elements.get())

        self.x = self.add_submodule('x', Xstrict(
            self, 'x', self.target_qubit, control_pulse = 'control_pi'))
        self._sub_sequences = []

    def fpga_declare__qua(self):
        """QUA-backend-specific variable declarations for CPMG."""
        super().fpga_declare()
        self.x._dispatch('declare')
        self.n_index = qua.declare(int)
        self.wait_time_factor = qua.declare(qua.fixed)
        self.t_sub_equator_wait = qua.declare(int)

    def fpga_before_sequence(self):
        """Hardware-agnostic pre-sequence for CPMG."""
        self.x.fpga_sequence()  # x gate pre-sequence
        if type(self.arbok_params.repetitions.hw_var).__name__ == 'QuaVariable':
            with arbok.if_block(self.arbok_params.repetitions.hw_var == 0):
                arbok.assign(self.wait_time_factor, 1)
            with arbok.else_block():
                arbok.assign(self.wait_time_factor, 1/(self.arbok_params.repetitions.hw_var*2))
        elif isinstance(self.arbok_params.repetitions.hw_var, int):
            if self.arbok_params.repetitions.hw_var == 0:
                arbok.assign(self.wait_time_factor, 1)
            else:
                arbok.assign(self.wait_time_factor, 1/(self.arbok_params.repetitions.hw_var*2))
        else:
            raise ValueError('Repetitions must be an integer or a QuaVariable')
        arbok.align(*self.elements)
        arbok.assign(
            self.t_sub_equator_wait,
            arbok.cast_mul_int_by_fixed(
                self.arbok_params.t_equator_wait.hw_var, self.wait_time_factor)
        )

    def fpga_sequence(self):
        """Hardware-agnostic CPMG sequence."""
        self._fpga_cpmg()

    def _fpga_cpmg(self) -> None:
        """CPMG dispatch based on repetitions type."""
        if type(self.arbok_params.repetitions.hw_var).__name__ == 'QuaVariable':
            self._fpga_sequence_with_repetitions_as_variable()
        elif isinstance(self.arbok_params.repetitions.hw_var, int):
            self._fpga_sequence_with_repetitions_as_int()
        else:
            raise ValueError('Repetitions must be an integer or a QuaVariable')
        arbok.align(*self.elements)

    def _fpga_sequence_with_repetitions_as_variable(self) -> None:
        with arbok.if_block(self.arbok_params.repetitions.hw_var == 0):
            self._fpga_cpmg_zero_order()
        with arbok.else_block():
            self._fpga_cpmg_non_zero_order()

    def _fpga_sequence_with_repetitions_as_int(self) -> None:
        if self.arbok_params.repetitions.hw_var == 0:
            self._fpga_cpmg_zero_order()
        elif self.arbok_params.repetitions.hw_var == 1:
            arbok.frame_rotation(0.25, self.target_qubit)
            self._fpga_cpmg_hahn_order()
            arbok.frame_rotation(-0.25, self.target_qubit)
        else:
            self._fpga_cpmg_non_zero_order()

    def _fpga_cpmg_zero_order(self) -> None:
        arbok.wait(self.t_sub_equator_wait, self.target_qubit)

    def _fpga_cpmg_hahn_order(self) -> None:
        arbok.wait(self.t_sub_equator_wait, self.target_qubit)
        self.x.fpga_gate()
        arbok.wait(self.t_sub_equator_wait, self.target_qubit)

    def _fpga_cpmg_non_zero_order(self) -> None:
        arbok.frame_rotation(0.25, self.target_qubit)
        with arbok.for_loop(
            variable=self.n_index,
            init=0,
            condition=self.n_index < self.arbok_params.repetitions.hw_var,
            update=self.n_index + 1
        ):
            self._fpga_cpmg_hahn_order()
        arbok.frame_rotation(-0.25, self.target_qubit)

    def fpga_before_sequence__qua(self):
        """QUA-backend-specific pre-sequence for CPMG."""
        self.x.qua_before_sequence()
        ### Calculating the wait time factor to divide the wait time
        ### by (repetitions * 2) to keep total wait time constant
        ### This is either done in qua or python code (repetition static or not)
        if type(self.arbok_params.repetitions.qua).__name__ == 'QuaVariable':
            with qua.if_(self.arbok_params.repetitions.qua == 0):
                qua.assign(self.wait_time_factor, 1)
            with qua.else_():
                qua.assign(self.wait_time_factor, 1/( self.arbok_params.repetitions.qua*2 ))
        elif isinstance(self.arbok_params.repetitions.qua, int):
            if self.arbok_params.repetitions.qua == 0:
                qua.assign(self.wait_time_factor, 1)
            else:
                qua.assign(self.wait_time_factor, 1/( self.arbok_params.repetitions.qua*2 ))
        else:
            raise ValueError('Repetitions must be an integer or a QuaVariable')
        qua.align(*self.elements)
        ### Slicing the equator wait time by the factor (recycle to save memory)
        qua.assign(
            self.t_sub_equator_wait,
            Cast.mul_int_by_fixed(
                self.arbok_params.t_equator_wait.qua, self.wait_time_factor)
            )

    def fpga_sequence__qua(self):
        """QUA-backend-specific CPMG sequence."""
        self.qua_cpmg()

    def qua_cpmg(self) -> None:
        """
        Checking if repetitions are a qua variable or an integer value
        If this is known we can handle the special case of repetitions = 0
        EITHER in qua or python code
        """
        if type(self.arbok_params.repetitions.qua).__name__ == 'QuaVariable':
            self._qua_sequence_with_repetitions_as_variable()
        elif isinstance(self.arbok_params.repetitions.qua, int):
            self._qua_sequence_with_repetitions_as_int()
        else:
            raise ValueError('Repetitions must be an integer or a QuaVariable')
        qua.align(*self.elements)

    def _qua_sequence_with_repetitions_as_variable(self) -> None:
        """
        Code being exectued if repetitions is a qua variable. Here the special
        case of repetitions = 0 is handled by waiting for the equator time
        within qua code
        """
        with qua.if_(self.arbok_params.repetitions.qua == 0):
            self._cpmg_zero_order()
        with qua.else_():
            self._cpmg_non_zero_order()

    def _qua_sequence_with_repetitions_as_int(self) -> None:
        """
        Code being exectued if repetitions is an integer. Here the special
        cases of repetitions = 0 and 1 is handled in python code to simplify the
        qua code output
        """
        if self.arbok_params.repetitions.qua == 0:
            self._cpmg_zero_order()
        elif self.arbok_params.repetitions.qua == 1:
            qua.frame_rotation_2pi(0.25, self.target_qubit)
            self._cpmg_hahn_order()
            qua.frame_rotation_2pi(-0.25, self.target_qubit)
        else:
            self._cpmg_non_zero_order()

    def  _cpmg_zero_order(self) -> None:
        """
        Special case of CPMG sequence with 0 repetitions. Here the equator time
        is waited for within qua code (Ramsey case)
        """
        qua.wait(self.t_sub_equator_wait, self.target_qubit)

    def _cpmg_hahn_order(self) -> None:
        """
        Core CPMG sequence logic, executed for each repetition.
        """
        qua.wait(self.t_sub_equator_wait, self.target_qubit)
        self.x.qua_gate()
        qua.wait(self.t_sub_equator_wait, self.target_qubit)

    def _cpmg_non_zero_order(self) -> None:
        """
        Special case of CPMG sequence with 1 repetition. Here the equator time
        is waited for within qua code (Ramsey case)
        """
        qua.frame_rotation_2pi(0.25, self.target_qubit)
        with qua.for_(
            var = self.n_index,
            init = 0,
            cond = self.n_index < self.arbok_params.repetitions.qua,
            update = self.n_index + 1
            ):
            self._cpmg_hahn_order()
        qua.frame_rotation_2pi(-0.25, self.target_qubit)
