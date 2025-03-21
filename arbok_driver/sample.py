from .utils import get_module
""" Module containing Samples class """

class Sample():
    """
    Class describing the used sample by its config and the used sequence. 
    """

    _master_config_path = None
    master_config = None

    def __init__(
            self, name: str,
            opx_config: dict,
            divider_config: dict,
            param_config = None,):
        """
        Constructor class for 'Sample' class.

        Args:
            name (str): Name of the used sample
            config (dict): OPX configuration file for sample
            self.elements (list): List of all quantum elements
        """
        self.name = name
        self.config = opx_config
        self.param_config = param_config
        self.divider_config = divider_config
        self.elements = list(self.config['elements'].keys())

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
            raise AttributeError(f"Dictionary 'config' not found in the file {self._master_config_path}")
        self.master_config = mc.config

    def reload_master_config(self):
        """
        If the master config path is set, force reloading
        """
        if self._master_config_path is not None:
            mcp = self.master_config_path
            self.master_config_path = mcp