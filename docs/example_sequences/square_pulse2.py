"""Module containing generic sequence for a simple square pulse sequence"""
from qm import qua
from arbok_driver import SubSequence, Sample, qua_helpers

class SquarePulse2(SubSequence):
    """
    Class containing parameters and sequence for a simple square pulse
    """

    def qua_sequence(self):
        """Macro that will be played within the qua.program() context"""
        qua.align(*self.sticky_elements())
        qua_helpers.arbok_go(
                sub_sequence = self,
                elements= self.sticky_elements(),
                from_volt = 'vHome',
                to_volt = 'vSquare',
                duration = self.ramp_time(),
                operation = 'unit_ramp',
                )
        qua.wait(self.t_square_pulse(), *self.sticky_elements())
        qua_helpers.arbok_go(
                sub_sequence = self,
                elements= self.sticky_elements(),
                from_volt = 'vSquare',
                to_volt = 'vHome',
                duration = self.ramp_time(),
                operation = 'unit_ramp',
                )