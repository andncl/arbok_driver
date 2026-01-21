"""Module containing abstract class for experiments"""
from abc import ABC, abstractmethod
import copy
from arbok_driver.device import Device

class Experiment(ABC):
    """
    Abstract class describing a type of experiment to run on the QM.
    This enforces a certain order of sequences that only requires certain
    input parameters or configurations to be set.
    E.g. for a rabi experiment, the order of sequences is:
        1. Initialization of quantum state
        2. Rabi pulse
        3. Readout of quantum state
    
    Attributes:
        name (str): Name of the experiment to run
        sequences (dict): Sequences to be run within program uploaded to the QM
    """
    _name: str
    def __init__(
            self,
            device: Device,
            configs_to_prepare: dict | None = None
            ) -> None:
        """
        Constructor class for 'Experiment' class.

        Args:
            device (Device): The device object containing configurations and sequences.
        """
        self.device: Device = device
        self.configs: dict = copy.deepcopy(device.default_sequence_configs)
        if configs_to_prepare is not None:
            self._prepare_configs(configs_to_prepare)

    @property
    @abstractmethod
    def sequences_config(self) -> dict:
        """Sequences to be run within program uploaded to the OPX"""
        pass

    @property
    def name(self) -> str:
        """Name of the experiment to run"""
        return self._name

    def __call__(self) -> dict:
        """Returns the sequences to be run"""
        return self.sequences_config

    def _prepare_configs(self, configs_to_prepare: dict):
        """
        Prepare configurations for the experiment by updating the default configs.

        Args:
            configs_to_prepare (dict): List of configurations to prepare.
        """
        if not isinstance(configs_to_prepare, dict):
            raise TypeError(
                f"{self.name}'s 'configs_to_prepare' must be of type dict"
                f" is type: {type(configs_to_prepare)}."
            )
        for name, config in configs_to_prepare.items():
            if isinstance(config, dict):
                self.configs[name] = config
            elif isinstance(config, str):
                try:
                    self.configs[name] = self.configs[config]
                except KeyError as e:
                    raise KeyError(
                        f"Default config '{config}' not found in default configs."
                        ) from e
            elif config is None:
                if name not in self.configs:
                   self.configs[name] = {}
