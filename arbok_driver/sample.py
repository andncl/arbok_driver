""" Module containing Samples class """

class Sample():
    """
    Class describing the used sample by its config and the used sequence. 
    """
    def __init__(self, name = "dummy_sample", config = {}):
        """
        Constructor class for 'Sample' class.

        Args:
            name (str): Name of the used sample
            config (dict): OPX configuration file for sample
            self.elements (list): List of all quantum elements
        """
        self.name = name
        self.config = config
        self.elements = self.config['elements'].keys()