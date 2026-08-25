'''Module containing ReadSequence implementing coulomb peaks measurement'''
from dataclasses import dataclass
from qm import qua
from qm.qua._expressions import QuaVariable
from arbok_driver import (
    arbok, ParameterClass, ReadSequence, SequenceBase
)
from arbok_driver.parameter_types import (
    Time, ParameterMap, List, Voltage
)

@dataclass(frozen=True)
class CoulombPeaksParameters(ParameterClass):
    t_wait_after_ramp: Time
    t_wait_before_chop: Time
    gate_elements: List
    set_elements: List
    v_home: ParameterMap[str, Voltage]
    v_set_level: ParameterMap[str, Voltage]

class CoulombPeaks(ReadSequence):
    """
    Class containing parameters and sequence for Coulomb peaks measurement of
    a generic SET
    """
    PARAMETER_CLASS = CoulombPeaksParameters
    arbok_params: CoulombPeaksParameters
    qua_rep_index: QuaVariable

    def __init__(
            self,
            parent: SequenceBase,
            name: str,
            sequence_config: dict,
            reset_gates_only: bool = False
    ):
        """
        Constructor method for 'MixedDownUpInit' class

        Args:
            parent (SequenceBase): Parent sequence to be added to
            name (str): name of sequence
            sequence_config (dict): config containing pulse parameters
            reset_gates_only (bool): True to reset the gates only, not present
                or false to reset SET too
        """
        super().__init__(
            parent = parent,
            name = name,
            sequence_config = sequence_config
        )
        self.g_elements = list(self.arbok_params.gate_elements.get())
        self.elements = self.g_elements + list(self.arbok_params.set_elements.get())
        self.gates_only = reset_gates_only

    def fpga_declare(self):
        super().fpga_declare()
        self.qua_rep_index = arbok.declare(int)

    def fpga_sequence(self):
        """Hardware-agnostic Coulomb peaks measurement sequence."""
        arbok.align(*self.elements)

        arbok.play(
            elements=self.elements,
            reference=self.arbok_params.v_home,
            target=self.arbok_params.v_set_level,
            operation='unit_ramp',
        )
        with arbok.for_loop(
            variable=self.qua_rep_index,
            init=0,
            condition=self.qua_rep_index < 4,
            update=self.qua_rep_index + 1
        ):
            arbok.wait(self.arbok_params.t_wait_after_ramp.hw_var, *self.elements)
        arbok.align(*self.elements)

        for _, readout in self.readout_groups["read"].items():
            readout.qua_measure_and_save()

        arbok.align(*self.elements)
        arbok.wait(self.arbok_params.t_wait_before_chop.hw_var, *self.elements)

        for _, readout in self.readout_groups["chop"].items():
            readout.qua_measure_and_save()
        arbok.align(*self.elements)

        arbok.play(
            elements=self.elements,
            reference=self.arbok_params.v_set_level,
            target=self.arbok_params.v_home,
            operation='unit_ramp',
        )
        if self.gates_only:
            arbok.reset_sticky_elements(self.g_elements)
        else:
            arbok.reset_sticky_elements(self.elements)

    def fpga_sequence__qua(self):
        """QUA-backend-specific Coulomb peaks sequence."""
        qua.align(*self.elements)

        arbok.ramp(
            elements = self.elements,
            reference = self.arbok_params.v_home,
            target = self.arbok_params.v_set_level,
            operation = 'unit_ramp',
        )
        with qua.for_(
            var = self.qua_rep_index,
            init = 0,
            cond = self.qua_rep_index < 4,
            update = self.qua_rep_index + 1
        ):
            qua.wait(self.arbok_params.t_wait_after_ramp.qua, *self.elements)
        qua.align(*self.elements)

        for _, readout in self.readout_groups["read"].items():
            readout.qua_measure_and_save()

        qua.align(*self.elements)
        qua.wait(self.arbok_params.t_wait_before_chop.qua, *self.elements)

        for _, readout in self.readout_groups["chop"].items():
            readout.qua_measure_and_save()
        qua.align(*self.elements)

        arbok.ramp(
            elements = self.elements,
            reference = self.arbok_params.v_set_level,
            target = self.arbok_params.v_home,
            operation = 'unit_ramp',
        )
        if self.gates_only:
            arbok.reset_sticky_elements(self.g_elements)
        else:
            arbok.reset_sticky_elements(self.elements)
