"""Module containing generic sequence for a simple square pulse sequence"""
from dataclasses import dataclass
from qm import qua
from arbok_driver import ParameterClass, SubSequence, qua_helpers
from arbok_driver.parameter_types import (
    Amplitude, List, Time, ParameterMap, Voltage)

@dataclass(frozen = True)
class SquarePulseParameters(ParameterClass):
    amplitude: Amplitude
    sticky_elements: List
    t_ramp: Time
    v_home: ParameterMap[str, Voltage]
    v_square: ParameterMap[str, Voltage]

class SquarePulse(SubSequence):
    """
    Class containing parameters and sequence for a simple square pulse
    """
    PARAMETER_CLASS = SquarePulseParameters

    def qua_sequence(self):
        """Macro that will be played within the qua.program() context"""
        qua.align(*self.sticky_elements())
        qua_helpers.arbok_go(
            sub_sequence = self,
            elements= self.sticky_elements(),
            from_volt = 'v_home',
            to_volt = 'v_square',
            duration = self.ramp_time(),
            operation = 'unit_ramp',
            )
        qua.wait(self.t_square_pulse(), *self.sticky_elements())
        qua_helpers.arbok_go(
            sub_sequence = self,
            elements= self.sticky_elements(),
            from_volt = 'v_square',
            to_volt = 'v_home',
            duration = self.ramp_time(),
            operation = 'unit_ramp',
            )
