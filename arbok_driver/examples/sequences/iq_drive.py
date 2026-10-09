"""
Module containing a generated I/Q drive and the pulse generators behind it.

The sequence plays a qubit drive whose envelope is generated in python rather
than configured by hand. A generator returning complex samples (``I + 1j*Q``)
or a ``{'I': [...], 'Q': [...]}`` dict is recognized as an up-converted pulse,
so the same ``arbok.play`` call drives a mixInputs or MWInput element without
anything being declared at the call site.

Sweeping the drive amplitude turns this into an amplitude-Rabi measurement. By
default each amplitude is applied by scaling one waveform at runtime; with one
extra call the envelopes are pre-computed instead, one per amplitude, and the
pulse plays free of any classical logic::

    measurement.set_sweeps({drive.arbok_params.v_drive['qe1']: amplitudes})
    measurement.register_waveform_caching(drive.arbok_params.v_drive)

Both quadratures end up as one ``type: array`` waveform each, selected by a
single index, so an index can never pick the I of one amplitude and the Q of
another.
"""
from dataclasses import dataclass

import numpy as np

from arbok_driver import arbok, ParameterClass, SubSequence
from arbok_driver.arbok.play import PulseGenerator
from arbok_driver.parameter_types import List, ParameterMap, Time, Voltage

SIGMA_FRACTION = 0.25
"""Width of the Gaussian envelope, as a fraction of the pulse duration."""


def gaussian_iq_envelope(amplitude_v: float, duration_ns: int) -> np.ndarray:
    """Generates a Gaussian envelope on I, nothing on Q.

    The samples are complex (``I + 1j*Q``) with a vanishing imaginary part,
    which is what marks them as an up-converted pulse. This drives a rotation
    about the x axis of the rotating frame.

    Args:
        amplitude_v (float): Peak envelope amplitude in volts at the DAC.
        duration_ns (int): Pulse length in ns (1 sample per ns).

    Returns:
        np.ndarray: Complex envelope, one sample per ns.
    """
    return _gaussian(amplitude_v, duration_ns).astype(complex)


def drag_iq_envelope(
        phase_rad: float = 0.0,
        drag_coefficient: float = 0.5,
        ) -> PulseGenerator:
    """Builds a generator for a phase rotated DRAG envelope.

    The in-phase component is a Gaussian, the quadrature component its scaled
    derivative, and the pair is rotated by ``phase_rad`` in the complex plane -
    so both quadratures carry signal and the rotation axis is free. DRAG
    suppresses leakage into levels outside the computational subspace.

    A generator is called as ``(amplitude_v, duration_ns)``, which leaves no
    room for pulse shape arguments. Those are bound here instead, so one shape
    per rotation axis can be built once and reused::

        X_HALF = drag_iq_envelope()
        Y_HALF = drag_iq_envelope(phase_rad = np.pi/2)

    Args:
        phase_rad (float): Phase of the drive, setting the rotation axis in
            the equatorial plane. 0 drives about x, pi/2 about y.
        drag_coefficient (float): Weight of the derivative component, in units
            of the envelope width. 0 falls back to a plain Gaussian.

    Returns:
        PulseGenerator: Callable(amplitude_v, duration_ns) -> complex samples.
    """
    def envelope(amplitude_v: float, duration_ns: int) -> np.ndarray:
        in_phase = _gaussian(amplitude_v, duration_ns)
        ### np.gradient keeps the length, so both quadratures stay in step
        quadrature = drag_coefficient * np.gradient(in_phase)
        return (in_phase + 1j*quadrature) * np.exp(1j*phase_rad)
    return envelope


def _gaussian(amplitude_v: float, duration_ns: int) -> np.ndarray:
    """Returns a Gaussian of ``duration_ns`` samples, peaking at its centre."""
    sigma = SIGMA_FRACTION * duration_ns
    time_ns = np.arange(duration_ns) - (duration_ns - 1)/2
    return amplitude_v * np.exp(-time_ns**2 / (2*sigma**2))


@dataclass(frozen = True)
class IQDriveParameters(ParameterClass):
    drive_elements: List
    t_drive: Time
    v_drive: ParameterMap[str, Voltage]


class IQDrive(SubSequence):
    """
    Class playing a generated I/Q drive on one or more qubit elements.

    The envelope comes from a python generator, so the pulse does not have to
    exist in the hardware config. Sweeping ``v_drive`` sweeps the drive
    amplitude; see the module docstring for caching the envelopes.
    """
    PARAMETER_CLASS = IQDriveParameters
    arbok_params: IQDriveParameters

    def __init__(
            self,
            parent,
            name: str,
            sequence_config: dict | None = None,
            pulse_generator: PulseGenerator | None = None,
            ):
        """
        Constructor method for the 'IQDrive' class.

        Args:
            parent: Measurement or sequence this sequence is added to.
            name (str): Name of the sequence.
            sequence_config (dict | None): Config holding the parameters.
            pulse_generator (PulseGenerator | None): Envelope generator,
                called as ``(amplitude_v, duration_ns)``. Defaults to
                :func:`gaussian_iq_envelope`; pass
                ``drag_iq_envelope(phase_rad = ...)`` for another axis.
        """
        self.pulse_generator = pulse_generator or gaussian_iq_envelope
        super().__init__(parent, name, sequence_config)

    def fpga_sequence(self):
        """Plays the generated envelope on every drive element."""
        arbok.play(
            elements = list(self.arbok_params.drive_elements.get()),
            target = self.arbok_params.v_drive,
            operation = self.pulse_generator,
            duration = self.arbok_params.t_drive,
        )


iq_drive_conf = {
    "sequence": IQDrive,
    "parameters": {
        'drive_elements': {'type': List, 'value': ['qe1']},
        ### A generated pulse is as long as its samples, so the duration is
        ### fixed - waveform caching is incompatible with a swept duration
        't_drive': {'type': Time, 'value': int(40)},  # 40cc = 160ns
        'v_drive': {
            'type': Voltage,
            'elements': {
                'qe1': 0.1,
            }
        },
    }
}
