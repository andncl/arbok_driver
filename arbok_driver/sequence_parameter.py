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

    validator = None
    sweep_validator = None
    unit = ''
    qua_type = int
    var_type = None
    input_stream = None
    qua_sweeped = False
    qua_sweep_arr = None
    qua_var = None
    value = None
    can_be_parameterized = False
    scale = 1

    def __init__(self, *args, var_type = None, element = None, **kwargs):
        """
        Constructor for 'SequenceParameter' class

        Args:
            elements (list): Elements that should be influenced by parameter
            config_name (str): Name of the parameter in the sequence config dict
                essentially name without the element
        """
        try:
            super().__init__(*args, **kwargs)
        except Exception as e:
            raise ValueError(
                f"Error initializing SequenceParameter: {kwargs['name']}: {e}"
                ) from e
        self.element = element
        if var_type is not None:
            self.var_type = var_type

    @property
    def sequence_path(self) -> str:
        """Returns the path through all parent sequences above"""
        return f"{self.instrument.get_sequence_path()}_{self.name}"

    @property
    def full_name(self) -> str:
        """Returns the full name of the parameter"""
        return self.sequence_path

    def convert_to_real_units(self, value):
        """
        Converts the value of the parameter to real units

        Args:
            value (float|int): Value to be converted

        Returns:
            float|int: Converted value
        """
        return value

    def __call__(self,
                 value: Optional[float | int | ndarray] = None
                 ) -> Optional[float | int | ndarray]:
        return self.call_method(value)

    def call_method(self,
                 value: Optional[float | int | ndarray] = None
                 ) -> Optional[float | int | ndarray]:
        """
        Method being executed when SequenceParameter is called.
        
        Args:
            value (Optional[float | int]): Value if given sets

        Returns:
            float|int|np.ndarray: Parameter value if no input value is given
        """
        if self.qua_var is not None:
            return self.qua_var
        if value is None:
            return self.get_raw()
        else:
            self.set(value)

    def reset(self) -> None:
        """
        In case we have switched to a sweep state, reset the validator to a scalar.
        """
        while self.remove_validator():
            pass
        self.add_validator(self.validator)

    def qua_declare(self, setpoints):
        """
        Declares the parameter inside qua code as variable and sets its class
        attributes accordingly. Note: This method can only be called inside the
        qua.program() context manager

        Args:
            setpoints (list, numpy.array): Setpoints for parameter sweep
        """
        logging.debug(
            "Adding qua %s variable for %s on subsequence %s (stream %s)",
            type(self.get()), self.name, self.instrument.name, self.input_stream
        )
        if self.var_type == int:
            setpoints = np.array(setpoints, dtype = int)
        else: 
            setpoints = np.array(setpoints)
        self.qua_sweeped = True
        self.vals= Arrays()

        self.qua_var = qua.declare(self.var_type)
        if self.can_be_parameterized:
            pass
        elif self.input_stream is None:
            self.qua_sweep_arr = qua.declare(
                self.var_type, value = setpoints*self.scale
            )
        else:
            self.input_stream = qua.declare_input_stream(
                t = self.var_type,
                name = self.sequence_path,
                size = int(setpoints)
            )

    def add_stream_param_to_sequence(self):
        """Adds input stream to sequence"""
        if self.input_stream is not None:
            sequence = self.instrument.measurement
            sequence.add_input_stream_parameter(self)
        else:
            raise ValueError(
                f"Parameter {self.name} has no input stream to add"
            )
