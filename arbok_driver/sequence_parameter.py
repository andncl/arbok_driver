""" Module containing SequenceParameter class """
from typing import Optional
import logging

from numpy import ndarray
import numpy as np
from qcodes.parameters import Parameter
from qcodes.validators import Arrays
from qm import qua

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
        self.input_stream = None

    @property
    def sequence_path(self):
        """Returns the path through all parent sequences above"""
        return f"{self.instrument.get_sequence_path()}{self.name}"

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

    def qua_declare(self, setpoints):
        """
        Declares the parameter inside qua code as variable and sets its class
        attributes accordingly. Note: This method can only be called inside the
        qua.program() context manager
        TODO: Fix doctring!

        Args:
            setpoints (list, numpy.array): Setpoints for parameter sweep
        """
        logging.debug(
            "Adding qua %s variable for %s on subsequence %s (stream %s)",
            type(self.get()), self.name, self.instrument.name, self.input_stream
        )
        setpoints = np.array(setpoints)
        self.qua_sweeped = True
        self.vals= Arrays()

        self.qua_var = qua.declare(self.var_type)
        if self.input_stream is None:
            self.set(np.array(setpoints))
            self.qua_sweep_arr = qua.declare(
                self.var_type, value = setpoints*self.scale
            )
        else:
            self.input_stream = qua.declare_input_stream(
                t = self.var_type,
                name = self.sequence_path,
                size = int(setpoints)
            )
    
