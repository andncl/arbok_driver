""" Module containing Devices class """
import warnings
from .utils import get_module

class Device():
    """
    Class describing the used device by its config and the used sequence. 
    """

    _master_config_path = None
    master_config = None

    def __init__(
            self, name: str,
            opx_config: dict,
            divider_config: dict,
            master_config = None,
            ):
        """
        Constructor class for 'Device' class.

        Args:
            name (str): Name of the used device
            opx_config (dict): Configuration dictionary for the OPX
            divider_config (dict): Configuration dictionary for the divider
            master (dict): Configuration dictionary for universally accessible
                parameters across all sub-sequences as well as default
                sequence configurations.
        """
        self.name = name
        self.config = opx_config
        self.elements = list(self.config['elements'].keys())
        self.divider_config = divider_config
        if master_config is None:
            master_config = {}
            warnings.warn("No master_config provided.")
        if 'parameters' in master_config:
            self.param_config = master_config['parameters']
        else:
            self.param_config = {}
            warnings.warn(
                "No parameters found in master_config."
            )
        if 'default_sequence_configs' in master_config:
            self.default_sequence_configs = master_config['default_sequence_configs']
        else:
            self.default_sequence_configs = {}
            warnings.warn(
                "No default_sequence_configs found in master_config."
            )

    @property
    def master_config_path(self):
        """
        Getter for master_config.

        Returns:
            str: The current configuration dictionary.
        """
        return self._master_config_path

    @master_config_path.setter
    def master_config_path(self, config_path):
        """
        Setter for master_config_path.
        Validates and sets the configuration path as a string.

        Args:
            config_path (str): A dictionary containing configuration data.

        Raises:
            ValueError: If the config is not a string.
        """
        if not isinstance(config_path, str):
            raise ValueError("master_config_path must be a str.")
        self._master_config_path = config_path
        mc = get_module('mc', config_path)
        if not hasattr(mc, 'config'):
            raise AttributeError(
                "Dictionary 'config' not found in the file: "
                f"{self._master_config_path}"
                )
        self.master_config = mc.config
        # check if sequences_config is in the mc if not then put empty format.
        if hasattr(mc, 'sequences_config'):
            self.sequences_config = mc.sequences_config
        else:
            self.sequences_config = {
                'spin_init': {
                    'sequence': None,
                    'config': None
                },
                'spin_readout': {
                    'sequence': None,
                    'config': None
                }
            }

    def reload_master_config(self):
        """
        If the master config path is set, force reloading
        """
        if self._master_config_path is not None:
            mcp = self.master_config_path
            self.master_config_path = mcp
