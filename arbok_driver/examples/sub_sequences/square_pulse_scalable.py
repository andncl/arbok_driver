"""Module containing generic sequence for a simple square pulse sequence"""
from dataclasses import dataclass
from qm import qua
from arbok_driver import arbok, ParameterClass, SubSequence
from arbok_driver.parameter_types import (
    List, Time, ParameterMap, Voltage)

@dataclass(frozen = True)
class SquarePulseParameters(ParameterClass):
    sticky_elements: List
    t_ramp: Time
    t_square_pulse: Time
    v_home: ParameterMap[str, Voltage]
    v_square: ParameterMap[str, Voltage]

class SquarePulseScalable(SubSequence):
    """
    Class containing parameters and sequence for a simple square pulse
    """
    PARAMETER_CLASS = SquarePulseParameters
    arbok_params: SquarePulseParameters
    def qua_sequence(self):
        """Macro that will be played within the qua.program() context"""
        qua.align(*self.arbok_params.sticky_elements.qua)
        arbok.ramp(
            elements= self.arbok_params.sticky_elements.qua,
            from_volt = self.arbok_params.v_home,
            to_volt = self.arbok_params.v_square,
            duration = self.arbok_params.t_ramp,
            operation = 'unit_ramp',
            )
        print("HIa", self.arbok_params.sticky_elements.qua)
        qua.wait(
            self.arbok_params.t_square_pulse.qua,
            *self.arbok_params.sticky_elements.qua
            )
        arbok.ramp(
            elements= self.arbok_params.sticky_elements.qua,
            from_volt = self.arbok_params.v_square,
            to_volt = self.arbok_params.v_home,
            duration = self.arbok_params.t_ramp,
            operation = 'unit_ramp',
            )
