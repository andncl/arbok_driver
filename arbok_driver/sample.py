""" Module containing Samples class """

class Sample():
    """
    Class describing the used sample by its config and the used sequence. 
    """
    def __init__(self, name: str, opx_config: dict, divider_config: dict):
        """
        Constructor class for 'Sample' class.

        Args:
            name (str): Name of the used sample
            config (dict): OPX configuration file for sample
            self.elements (list): List of all quantum elements
        """
        self.name = name
        self.config = opx_config
        self.divider_config = divider_config
        self.elements = list(self.config['elements'].keys())
