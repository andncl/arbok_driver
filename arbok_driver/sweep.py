""" Module with Sweep class """
import numpy as np

from qcodes.parameters import Parameter
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
        """Setter for config_to_register"""
        if all(param in self.parameters for param in param_list):
            self._config_to_register = param_list
        else:
            raise KeyError(
                "Some of the given parameters are not within the swept params")

    def configure_sweep(self) -> None:
        """Configures the sweep from the given dictionairy"""
        self.check_input_dict()
        self._parameters = []
        self._config_to_register = {}
        for i, parameter in enumerate(self._param_dict.keys()):
            self._parameters.append(parameter)
            if self.register_all:
                self._config_to_register[parameter] = self.config[parameter]
            elif i == 0:
                value = self.config[parameter]
                if isinstance(value, (list, np.ndarray)):
                    self._config_to_register[parameter] = value
                elif isinstance(value, int):
                    # creates a mock set of values (stream array indices)
                    self._config_to_register[parameter] = np.arange(value)
                    parameter.input_stream = True
                else:
                    raise ValueError(
                        "Keys in sweep dictionairies must be of type int, list"
                        f"or numpy.ndarray, is:  {type(value)}")

    def check_input_dict(self) -> None:
        """
        Validates equal sizes of input arrays in three steps:
            1) Checks if all parameters are SequenceParameter/Parameter
            2) Checks if all sweep setpoint arrays have same lengths
            3) Checks if all input streams have the same dimension
        """
        param_types_valid = []
        for param in self._param_dict.keys():
            param_types_valid.append(
             isinstance(param,(SequenceParameter, Parameter))
            )
        if not all(param_types_valid):
            raise TypeError(
        "All given parameter must be of SequenceParameter or Parameter"
        )
        param_arrays = []
        param_streams = []
        for values in self._param_dict.values():
            if isinstance(values, np.ndarray):
                param_arrays.append(values)
            elif isinstance(values, int):
                param_streams.append(values)
            else:
                raise ValueError(
                        "Keys in sweep dictionairies must be of type int, list"
                        f"or numpy.ndarray, is:  {type(values)}")
        # checks if all setpoint arrays have the same length
        if param_arrays:
            list_iter = iter(param_arrays)
            length = len(next(list_iter))
            if not all(len(l) == length for l in list_iter):
                raise ValueError('not all lists have same length!')
            self._length = length
        # checks if all input streams have the same length and compares to
        # regular sweeps
        if param_streams:
            if not all(size == param_streams[0] for size in param_streams):
                raise ValueError(
                    f"not all param streams have same size! {param_streams}")
            if param_arrays:
                if self._length != param_streams[0]:
                    raise ValueError(
                        "When mixing stream variable sweeps with static sweeps,"
                        f" size of input stream ({param_streams[0]})  must be"
                        f" same as static sweep array ({self._length})"
                    )
            self._length = param_streams[0]
