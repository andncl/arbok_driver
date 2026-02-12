"""Module containing generic sequence for a simple square pulse sequence"""
from dataclasses import dataclass
from qm import qua
from arbok_driver import ParameterClass, SubSequence
from arbok_driver.parameter_types import Amplitude, String, Time

@dataclass(frozen = True)
class SquarePulseParameters(ParameterClass):
    amplitude: Amplitude
    element: String
    t_ramp: Time
    t_square_pulse: Time

class SquarePulseLegacy(SubSequence):
    """
    Class containing parameters and sequence for a simple square pulse
    """
    PARAMETER_CLASS = SquarePulseParameters
    arbok_params: SquarePulseParameters
    def qua_sequence(self):
        """Macro that will be played within the qua.program() context"""
        qua.align()
        qua.play(
            pulse = 'ramp'*qua.amp(self.arbok_params.amplitude()),
            element = self.arbok_params.element(),
            duration = self.arbok_params.t_ramp()
            )
        qua.wait(
            self.arbok_params.t_square_pulse(),
            self.arbok_params.element())
        qua.play(
            pulse = 'ramp'*qua.amp(self.arbok_params.amplitude()),
            element = self.arbok_params.element(),
            duration = self.arbok_params.t_ramp()
            )
