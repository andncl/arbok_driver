'''Module containing ReadSequence implementing coulomb peaks measurement'''
from dataclasses import dataclass
from qm import qua
from arbok_driver import Device, ReadSequence, parameter_types, qua_helpers

@dataclass(frozen=True)
class CoulombPeaksParameters:
    t_wait_after_ramp: parameter_types.Time

class CoulombPeaks(ReadSequence):
    """
    Class containing parameters and sequence for Coulomb peaks measurement of
    a generic SET
    """

    def __init__(
            self,
            parent,
            name: str,
            device: Device,
            sequence_config: dict | None,
            reset_gates_only: bool = False
    ):
        """
        Constructor method for 'MixedDownUpInit' class

        Args:
            name (str): name of sequence
            device  (Device): Device class for physical device
            seq_config (dict): config containing pulse parameters
            reset_gates_only (bool): True to reset the gates only, not present
                or false to reset SET too
        """
        super().__init__(
            parent = parent,
            name = name,
            device = device,
            sequence_config = sequence_config
        )
        self.g_elements = list(self.gate_elements())
        self.elements = list(self.gate_elements()) + list(self.set_elements())
        self.qua_rep_index = None
        self.gates_only = reset_gates_only

    def qua_declare(self):
        super().qua_declare()
        self.qua_rep_index = qua.declare(int)

    def qua_sequence(self):
        qua.align(*self.elements)

        ### Go from the set 'home' voltage point to the 'level' voltage point
        qua_helpers.arbok_go(
            sub_sequence= self,
            elements = self.elements,
            from_volt = 'v_home',
            to_volt = 'v_set_level',
            operation = 'unit_ramp',
        )
        with qua.for_(
            var = self.qua_rep_index,
            init = 0,
            cond = self.qua_rep_index < 4,
            update = self.qua_rep_index + 1
        ):
            qua.wait(self.t_wait_after_ramp(), *self.elements)
        qua.align(*self.elements)

        ### Measure the SET current
        for _, readout in self.readout_groups["read"].items():
            readout.qua_measure_and_save()

        qua.align(*self.elements)
        qua.wait(self.t_wait_before_chop(), *self.elements)

        ### Chopped readout with one iteration to get the peak derivative
        for _, readout in self.readout_groups["chop"].items():
            readout.qua_measure_and_save()
        qua.align(*self.elements)

        ### Go back to the set 'level' voltage point to the 'home' voltage point
        qua_helpers.arbok_go(
            sub_sequence = self,
            elements = self.elements,
            from_volt = 'v_set_level',
            to_volt = 'v_home',
            operation = 'unit_ramp',
        )
        if self.gates_only:
            qua_helpers.reset_elements(self.g_elements, self)
        else:
            qua_helpers.reset_elements(self.elements, self)
