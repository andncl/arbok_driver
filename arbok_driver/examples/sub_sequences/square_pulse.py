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

class SquarePulse(SubSequence):
    """
    Class containing parameters and sequence for a simple square pulse
    """
    PARAMETER_CLASS = SquarePulseParameters

    def qua_sequence(self):
        """Macro that will be played within the qua.program() context"""
        qua.align()
        qua.play(
            pulse = 'ramp'*qua.amp(self.amplitude()),
            element = self.element(),
            duration = self.t_ramp()
            )
        qua.wait(self.t_square_pulse(), self.element())
        qua.play(
            pulse = 'ramp'*qua.amp(self.amplitude()),
            element = self.element(),
            duration = self.t_ramp()
            )
