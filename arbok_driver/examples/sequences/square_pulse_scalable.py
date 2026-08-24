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

    def fpga_sequence(self):
        """Hardware-agnostic scalable square pulse."""
        elements = self.arbok_params.sticky_elements.hw_var
        arbok.align(*elements)
        arbok.play(
            elements=elements,
            reference=self.arbok_params.v_home,
            target=self.arbok_params.v_square,
            duration=self.arbok_params.t_ramp,
            operation='unit_ramp',
        )
        arbok.wait(self.arbok_params.t_square_pulse.hw_var, *elements)
        arbok.play(
            elements=elements,
            reference=self.arbok_params.v_square,
            target=self.arbok_params.v_home,
            duration=self.arbok_params.t_ramp,
            operation='unit_ramp',
        )

    def qua_sequence(self):
        """Legacy QUA-specific implementation."""
        qua.align(*self.arbok_params.sticky_elements.hw_var)
        arbok.ramp(
            elements= self.arbok_params.sticky_elements.hw_var,
            reference = self.arbok_params.v_home,
            target = self.arbok_params.v_square,
            duration = self.arbok_params.t_ramp,
            operation = 'unit_ramp',
            )
        qua.wait(
            self.arbok_params.t_square_pulse.hw_var,
            *self.arbok_params.sticky_elements.hw_var
            )
        arbok.ramp(
            elements= self.arbok_params.sticky_elements.hw_var,
            reference = self.arbok_params.v_square,
            target = self.arbok_params.v_home,
            duration = self.arbok_params.t_ramp,
            operation = 'unit_ramp',
            )
