""" Module with Sweep class """

from .sequence_parameter import SequenceParameter

class Sweep:
    """ Class characterizing a parameter sweep along one axis in the OPX """
    def __init__(self, param_dict: dict, register_all = False):
        """ Constructor class of Sweep class
        
        Args: 
            param_dict (dict): Dict with parameters as keys and arrays as
                setpoints for sweep
        """
        self._param_dict = param_dict
        self._config_to_register = None
        self._parameters = None
        self._length = None
        self.register_all = register_all
        self.configure_sweep()

    @property
    def parameters(self):
        """ List containing all varied parameters """
        return self._parameters

    @property
    def length(self):
        """ Number of samples for parameters on the given axis """
        return self._length
    
    @property
    def config(self) -> dict:
        """Config dict for parameter sweep. Keys are params, values setpoints"""
        return self._param_dict
    
    @property
    def config_to_register(self) -> list:
        """ Parameters that will be registered in QCoDeS measurement """
        return self._config_to_register
    
    @config_to_register.setter
    def config_to_register(self, param_list: list) -> None:
        if all(param in self.parameters for param in param_list):
            self._config_to_register = param_list
        else: 
            raise KeyError("""Some of the given parameters are not within the 
                           swept parameters""")

    def configure_sweep(self):
        """ Configures the sweep from the given dictionairy """
        self.check_input_dict()
        self._parameters = []
        self._config_to_register = {}
        for i, parameter in enumerate(self._param_dict.keys()):
            self._parameters.append(parameter)
            if self.register_all:
                self._config_to_register[parameter] = self.config[parameter]
            elif i == 0:
                self._config_to_register[parameter] = self.config[parameter]

    def check_input_dict(self):
        """ Validates equal sizes of input arrays """
        if not all(isinstance(param, SequenceParameter) for param in self._param_dict.keys()):
            raise TypeError("All given parameter must be of SequenceParameter")
        list_iter = iter(self._param_dict.values())
        length = len(next(list_iter))
        if not all(len(l) == length for l in list_iter):
            raise ValueError('not all lists have same length!')
        self._length = length
