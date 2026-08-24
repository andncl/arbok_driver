""" Module containing Devices class """
import warnings


class Device():
    """
    Class describing the used device by its config and the used sequence.
    """
    _master_config: dict
    _param_config: dict
    _default_sequence_configs: dict

    def __init__(
            self, name: str,
            hardware_config: dict | None = None,
            divider_config: dict | None = None,
            master_config: dict | None = None,
            *,
            opx_config: dict | None = None,
            ):
        """
        Constructor class for 'Device' class.

        Args:
            name (str): Name of the used device
            hardware_config (dict): Hardware configuration dictionary
            divider_config (dict): Configuration dictionary for the divider
            master_config (dict): Configuration dictionary for universally
                accessible parameters across all sub-sequences as well as
                default sequence configurations.
            opx_config (dict): Deprecated alias for hardware_config.
        """
        if opx_config is not None:
            warnings.warn(
                "Device(opx_config=...) is deprecated, use "
                "Device(hardware_config=...) instead.",
                DeprecationWarning, stacklevel=2)
            if hardware_config is None:
                hardware_config = opx_config
        if hardware_config is None:
            raise TypeError("Device() requires 'hardware_config' argument")
        self.name = name
        self.config: dict = hardware_config
        self.elements = list(self.config['elements'].keys())
        self.divider_config = divider_config
        self.master_config = master_config
        self.sub_device_name = None

    @property
    def master_config(self) -> dict:
        return self._master_config
    
    @master_config.setter
    def master_config(self, master_config: dict | None) -> None:
        """
        Update the master config from a dict

        Args:
            master_config (dict): Configuration dictionary for universally accessible
                parameters across all sub-sequences as well as default
                sequence configurations.
        """
        if master_config is None:
            master_config = {}
        if 'parameters' in master_config:
            self._param_config = master_config['parameters']
        else:
            self._param_config = {}
        if 'default_sequence_configs' in master_config:
            self._default_sequence_configs = master_config['default_sequence_configs']
        else:
            self._default_sequence_configs = {}
        self._master_config = master_config

    @property
    def param_config(self):
        return self._param_config
    
    @property
    def default_sequence_configs(self):
        return self._default_sequence_configs
