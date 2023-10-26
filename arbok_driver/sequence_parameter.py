""" Module containing SequenceParameter class """
from typing import Optional
from numpy import ndarray
from qcodes.parameters import Parameter

class SequenceParameter(Parameter):
    """
    A parameter wrapper that adds the respective element as attribute

    TODO: Write get_raw abstract method without crashing sequence compilation
    """
    def __init__(self, element, config_name, var_type, *args, **kwargs):
        """
        Constructor for 'SequenceParameter' class

        Args:
            elements (list): Elements that should be influenced by parameter
            batched (bool): Is the variab
            config_name (str): Name of the parameter in the sequence config dict
                essentially name without the element
        """
        super().__init__(*args, **kwargs)
        self.element = element
        self.config_name = config_name
        self.qua_sweeped = False
        self.qua_sweep_arr = None
        self.qua_var = None
        self.value = None
        self.var_type = var_type

    def __call__(self, 
                 value: Optional[float | int | ndarray] = None
                 ) -> Optional[float | int | ndarray]:
        """
        Method being executed when SequenceParameter is called.
        
        Args:
            value (Optional[float | int]): Value if given sets

        Returns:
            float|int|np.ndarray: Parameter value if no input value is given
        """
        if self.qua_sweeped:
            if value is None:
                return self.qua_var
            else:
                raise ValueError(
                    "Parameter holds a QUA variable, you cant set it") 
        if value is None:
            return self.get_raw()
        if isinstance(value, (int, float, ndarray)):
            self.set(value)
        else:
            raise ValueError("Value to be set must be int, float or np.ndarray")
