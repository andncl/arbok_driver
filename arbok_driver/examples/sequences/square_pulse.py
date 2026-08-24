"""Module containing generic sequence for a simple square pulse sequence"""
from dataclasses import dataclass
from qm import qua
from arbok_driver import arbok, ParameterClass, SubSequence
from arbok_driver.parameter_types import Amplitude, String, Time

@dataclass(frozen = True)
class SquarePulseParameters(ParameterClass):
    amplitude: Amplitude
    element: String
    t_ramp: Time
    t_square_pulse: Time

class SquarePulse(SubSequence):
    """
    Class containing parameters and sequence for a simple square pulse
    """
    PARAMETER_CLASS = SquarePulseParameters
    arbok_params: SquarePulseParameters

    def fpga_sequence(self):
        """Hardware-agnostic square pulse sequence."""
        element = self.arbok_params.element.hw_var
        arbok.align()
        arbok.play(
            elements=[element],
            target=self.arbok_params.amplitude,
            operation='ramp',
            duration=self.arbok_params.t_ramp,
        )
        arbok.wait(self.arbok_params.t_square_pulse.hw_var, element)
        arbok.play(
            elements=[element],
            target=self.arbok_params.amplitude,
            operation='ramp',
            duration=self.arbok_params.t_ramp,
        )

    def qua_sequence(self):
        """Legacy QUA-specific implementation."""
        qua.align()
        qua.play(
            pulse = 'ramp'*qua.amp(self.arbok_params.amplitude.hw_var),
            element = self.arbok_params.element.hw_var,
            duration = self.arbok_params.t_ramp.hw_var
            )
        qua.wait(
            self.arbok_params.t_square_pulse.hw_var,
            self.arbok_params.element.hw_var)
        qua.play(
            pulse = 'ramp'*qua.amp(self.arbok_params.amplitude.hw_var),
            element = self.arbok_params.element.hw_var,
            duration = self.arbok_params.t_ramp.hw_var
            )
