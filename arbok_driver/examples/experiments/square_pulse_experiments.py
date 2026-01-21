"""
Module containing a simple child class of Experiment containing a single
sub-sequence of type SquarePulse
"""
from arbok_driver import Device, Experiment
from arbok_driver.examples.configurations import square_pulse_conf

class SquarePulseExperiment(Experiment):
    """Experiment containing only a single sub-sequence of type SquarePulse"""
    _name = 'square_pulse_experiment'
    def __init__(
        self,
        device: Device,
    ):
        super().__init__(device)

    @property
    def sequences_config(self):
        """Sequences-dict to contruct experiment"""
        return {
            'square_pulse': {'config': square_pulse_conf}
        }

class SquarePulseExperimentWithDefaults(Experiment):
    """
    Experiment containing only a single sub-sequence of type SquarePulse
    that can be given as argument or can be loaded from the measurements defaults
    """
    _name = 'square_pulse_experiment'
    def __init__(
        self,
        device: Device,
        square_pulse_config: dict | None = None
    ):
        super().__init__(
            device,
            configs_to_prepare = {
                'square_pulse': square_pulse_config
            })

    @property
    def sequences_config(self):
        """Sequences-dict to contruct experiment"""
        return {
            'square_pulse': self.configs['square_pulse']
        }