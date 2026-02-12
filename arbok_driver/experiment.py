"""Module containing abstract class for experiments"""
from abc import ABC, abstractmethod
from typing import Mapping
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
    """
    _name: str
    def __init__(self, **configs_to_prepare: str | Mapping[str, dict] | None):
        self.configs: dict = {}
        self.configs_to_prepare: Mapping = configs_to_prepare

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

    def get_sequences_config(self, device: Device) -> dict:
        self.configs = self.get_device_specific_subsequences_dict(device)
        return self.sequences_config

    def get_device_specific_subsequences_dict(self, device: Device):
        """
        Prepare configurations for the experiment by updating the default configs.

        Args:
            device (dict): Device to use for default sequences
        """
        configs = device.default_sequence_configs
        if not isinstance(self.configs_to_prepare, dict):
            raise TypeError(
                f"{self.name}'s 'configs_to_prepare' must be of type dict"
                f" is type: {type(self.configs_to_prepare)}."
            )
        for name, config in self.configs_to_prepare.items():
            if isinstance(config, dict):
                configs[name] = config
            elif isinstance(config, str):
                default_name = config
                if default_name in configs:
                    configs[name] = configs[config]
                else:
                    raise KeyError(
                        f"Default config '{config}' not found in default configs."
                        f" Of device: {device.name}"
                        )
            elif config is None:
                if name not in configs:
                   configs[name] = {}
        return configs
