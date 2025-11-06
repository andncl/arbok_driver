""" Module with Sweep class """
from __future__ import annotations
from typing import TYPE_CHECKING
import warnings
import logging

import numpy as np
from qm import qua
from qcodes.parameters import Parameter

from .sequence_parameter import SequenceParameter
if TYPE_CHECKING:
    from .measurement import Measurement

class Sweep:
    """ Class characterizing a parameter sweep along one axis in the OPX """

    _config_to_register = None
    _parameters = None
    _length = None
    _inputs_are_streamed = None
    _input_streams = None
    _can_be_parameterized = None
    snake_scan = False # Assume by default non snake scanning

    def __init__(self, measurement : Measurement, param_dict: dict, register_all = False):
        """
        Constructor class of Sweep class

        Args:
            paret_sequence (SequenceBase): Parent sequence of the sweep
            param_dict (dict): Dict with parameters as keys and arrays as
                setpoints for sweep. If snake_scan is present in the dict,
                use it.
            register_all (bool): Whether all parameters should be registered in
                the QCoDeS measurement
        """
        self.measurement = measurement
        self.register_all = register_all
        self._config = param_dict
        if 'snake' in self._config: # check if the user defined the snake state
            self.snake_scan = self._config['snake']
            del self._config['snake']
        self.configure_sweep()
        self._check_if_parametrizable()

    @property
    def parameters(self):
        """ List containing all varied parameters """
        return self._parameters

    @property
    def qua_variables(self):
        """ Tuple containing all qua variables of parameters """
        return tuple(par.qua_var for par in self.parameters)

    @property
    def qua_sweep_arrays(self):
        """ Tuple containing all qua sweep arrays of parameters """
        return tuple(par.qua_sweep_arr for par in self.parameters)

    @property
    def length(self):
        """ Number of devices for parameters on the given axis """
        return self._length

    @property
    def input_streams(self):
        """Returns all input streams if the sweep is set up to be streamed"""
        return tuple(par.input_stream for par in self.parameters)

    @property
    def inputs_are_streamed(self):
        """Whether sweep is fed by input stream"""
        return self._inputs_are_streamed

    @property
    def can_be_parameterized(self):
        """
        Whether sweep can be parameterized with start, stop and step for memory
        saving. If the user has not set this value, it will be checked by the
        entries of the given arrays
        """
        if self._can_be_parameterized is None:
            return self._check_if_parametrizable()
        else:
            return self._can_be_parameterized

    @can_be_parameterized.setter
    def can_be_parameterized(self, value: bool):
        """Setter for can_be_parameterized"""
        if value is False:
            self._can_be_parameterized = False
            for parameter in self.parameters:
                parameter.can_be_parameterized = False
        elif value is True:
            if self._can_be_parameterized is True:
                self._can_be_parameterized = True
        else:
            raise ValueError("can_be_parameterized must be of type bool")

    @property
    def config(self) -> dict:
        """Config dict for parameter sweep. Keys are params, values setpoints"""
        return self._config

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
        for i, parameter in enumerate(self.config.keys()):
            self._parameters.append(parameter)
            ### Remove scalar validators and setup the sweep_validator
            while parameter.remove_validator():
                pass
            parameter.add_validator(parameter.sweep_validator)
            parameter.validate(self.config[parameter])
            ### Usually not all params are registered (issue with live plotting)
            if self.register_all:
                setpoints = parameter.convert_to_real_units(
                    self.config[parameter])
                self._config_to_register[parameter] = setpoints*parameter.scale
                parameter.set_raw(setpoints.tolist()) ### CHECK IF THIS IS OK BEFORE MERGING
            elif i == 0:
                value = self.config[parameter]
                setpoints = parameter.convert_to_real_units(self.config[parameter])
                if isinstance(value, (list, np.ndarray)):
                    if parameter.scale is None:
                        raise ValueError(
                            f"Parameter scale of '{parameter.full_name}' is None."
                            " Must be set for sweep arrays. Check the type of"
                            " the parameter in the config file. If it does not"
                            " have a type, set the scale manually."
                            )
                    parameter.set_raw(setpoints.tolist())
                    self._config_to_register[parameter] = setpoints*parameter.scale
                elif isinstance(value, int):
                    ### creates a mock set of values (stream array indices)
                    self._config_to_register[parameter] = np.arange(value)
                else:
                    raise ValueError(
                        "Keys in sweep dictionairies must be of type int, list"
                        f"or numpy.ndarray, is:  {type(value)}")
            if isinstance(self.config[parameter], int):
                parameter.input_stream = True
                #parameter.add_stream_param_to_sequence()
        if all(param.input_stream is not None for param in self.parameters):
            self._inputs_are_streamed = True
        else:
            self._inputs_are_streamed = False

    def check_input_dict(self) -> None:
        """
        Validates equal sizes of input arrays in three steps:
            1) Checks if all parameters are SequenceParameter/Parameter
            2) Checks if var_type is int, bool or qua.fixed
            3) Checks if all sweep setpoint arrays have same lengths
            4) Checks if all input streams have the same dimension
        """
        self._config = self._convert_str_keys_to_param(self._config)
        for param in self.config.keys():
            if not isinstance(param, (SequenceParameter, Parameter)):
                raise TypeError(
                    f"Key {param} in sweep config must be of type "
                    "SequenceParameter or Parameter")
            if not param.var_type in (int, bool, qua.fixed):
                raise TypeError(
                    f"Key {param.full_name} in sweep config must have a var_type"
                    f" of int, bool, or qua.fixed. Is: {param.var_type}."
                )
        param_arrays = []
        param_streams = []
        for values in self._config.values():
            if isinstance(values, np.ndarray):
                param_arrays.append(values)
            elif isinstance(values, int):
                param_streams.append(values)
            else:
                raise ValueError(
                        "Keys in sweep dictionairies must be of type int, list"
                        f" or numpy.ndarray, is:  {type(values)}")
        ### checks if all setpoint arrays have the same length
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

    def _convert_str_keys_to_param(self, param_dict: dict) -> dict:
        """
        Converts string keys to SequenceParameter objects

        Args:
            param_dict (dict): Dict with string keys

        Returns:
            dict: Dict with SequenceParameter keys
        """
        new_dict = {}
        for key, value in param_dict.items():
            if isinstance(key, str):
                new_key = self.measurement.find_parameter_from_str_path(key)
                new_dict[new_key] = value
            else:
                new_dict[key] = value
        return new_dict

    def _check_if_parametrizable(self) -> bool:
        """
        Checks whether the sweep array can be defined in terms of start, step
        and stop (memory saving).

        Returns:
            bool: Whether the sweep can be parametrized
        """
        if self.inputs_are_streamed:
            return False
        parameterizability_list = []
        for param in self.parameters:
            sweep_arr = self.config[param]
            sweep_arr_differences = np.ediff1d(sweep_arr)
            mean_step = np.mean(sweep_arr_differences)
            if np.std(sweep_arr_differences) > np.abs(0.1*mean_step):
                can_be_parameterized = False
            else:
                can_be_parameterized = True
            param.can_be_parameterized = can_be_parameterized
            parameterizability_list.append(can_be_parameterized)
        ### In case not all parameters can be parametrized, none can
        parameterizabel = any(parameterizability_list)
        if not parameterizabel:
            for param in self.parameters:
                param.can_be_parameterized = False
        return parameterizabel

    def qua_generate_parameter_sweep(self, next_action: callable, next_sweep) -> None:
        """
        Runs a qua loop based on the configured method. Currently three
        different methods are available:
            1) From input stream
            2) From parametrized array (start, stop, step)
            3) From an explicitly defined qua array
        If necessary, we need to reset the snake var for the inner loop before
        entering the snaking loop.
        """

        # Reset the snake var if necessary
        if next_sweep is not None:
            ns_sv = next_sweep.get_snake_var()
            if ns_sv is not None:
                qua.assign(next_sweep.get_snake_var(), True)

        if self.inputs_are_streamed:
            self._qua_input_stream_loop(next_action)
        elif self.can_be_parameterized:
            self._qua_parmetrized_loop(next_action)
        else:
            self._qua_explicit_array_loop(next_action)

    def get_snake_var(self):
        """
        Declare a snake_var if we are snaking and return that var if snaking.

        Returns:
            qua bool var : The snaking indicator if snaking, None otherwise
        """
        if self.snake_scan:
            if not hasattr(self, 'sweep_snake_var'):
                self.sweep_snake_var = qua.declare(bool, True)
            return self.sweep_snake_var
        return None

    def _qua_input_stream_loop(self, next_action: callable) -> None:
        """Runs a qua for loop for an array that is imported from a stream"""
        warnings.warn("Input streaming is not fully supported")
        for param in self.parameters:
            qua.wait(int(1e6))
            qua.advance_input_stream(param.input_stream)
            logging.debug(
                "Assigning %s with length %s (input stream)",
                param.name, self.length)

        sweep_idx_var = qua.declare(int)
        qua.assign(sweep_idx_var, 0)
        with qua.while_(sweep_idx_var < self.length):
            for param in self.parameters:
                qua.assign(
                    param.qua_var, param.input_stream[sweep_idx_var])
            next_action()
            self._advance_step_counter(sweep_idx_var)

    def _qua_parmetrized_loop(self, next_action: callable) -> None:
        """
        Runs a qua for loop from parametrized qua_arange. Start, stop and step
        are calculated from the input array

        Args:
            next_action (callable): Next action to be executed after the loop
        """
        ### Define start, stop and step for all params that can be parameterized
        parameters_sss = self._parameterize_sweep()

        ### Declaring sweep index variable and respective loop for sweep
        sweep_idx_var = qua.declare(int)
        if self.snake_scan:
            qua.assign(self.get_snake_var(), ~self.get_snake_var())

        qua.assign(sweep_idx_var, 0)
        with qua.while_(sweep_idx_var < self.length):
            for param in self.parameters:
                if not param.can_be_parameterized:
                    qua.assign(
                        param.qua_var, param.qua_sweep_arr[sweep_idx_var])
            if not self.snake_scan:
                for param, sss in parameters_sss.items():
                    self._qua_calc_param_step(param, sss, sweep_idx_var, False)
            else:
                with qua.if_(self.get_snake_var()):
                    for param, sss in parameters_sss.items():
                        self._qua_calc_param_step(param, sss, sweep_idx_var, True)
                with qua.else_():
                    for param, sss in parameters_sss.items():
                        self._qua_calc_param_step(param, sss, sweep_idx_var, False)

            qua.align()

            ### This is where either the whole sequence or the next sweep is run
            next_action()
            self._advance_step_counter(sweep_idx_var)

    def _qua_calc_param_step(self, param, sss, sweep_idx_var, reverse):
        """
        Calculates the step within a parameter sweep.
        
        Args:
            param (SequenceParameter): Parameter to be swept
            sss (dict): Dict with start, stop and step (parameterizing sweep)
            sweep_idx_var (qua variable): Index variable for sweep
            reverse (bool): Whether the sweep is reversed (from stop to start)

        Raises:
            TypeError: If var_type is not int or fixed

        Returns:
            None
        """
        ### Note this implementation is written in a very explicit way avoiding
        ### multiplications to save lines of code. This is done to avoid
        ### multiplications in the FPGA code (e.g (-1)*x)
        if param.var_type == int:
            if not reverse:
                qua.assign(
                    param.qua_var, sss['start'] + sss['step']*sweep_idx_var)
            else:
                qua.assign(
                    param.qua_var, sss['stop'] - sss['step']*sweep_idx_var)
        elif param.var_type == qua.fixed:
            if not reverse:
                qua.assign(
                    param.qua_var,
                    sss['start'] + qua.lib.Cast.mul_fixed_by_int(
                        sss['step'], sweep_idx_var)
                    )
            else:
                qua.assign(
                    param.qua_var,
                    sss['stop'] - qua.lib.Cast.mul_fixed_by_int(
                        sss['step'],sweep_idx_var)
                    )
        else:
            raise TypeError(
                "Only int and fixed qua types are supported for param sweeps"
                )

    def _qua_explicit_array_loop(self, next_action):
        """Runs a qua for loop from explicitly defined qua arrays"""
        for param in self.parameters:
            logging.debug(
                "Assigning %s to %s (loop)",
                    param.name, param.qua_sweep_arr)

        sweep_idx_var = qua.declare(int)
        qua.assign(sweep_idx_var, 0)
        with qua.while_(sweep_idx_var < self.length):
            for param in self.parameters:
                qua.assign(
                    param.qua_var, param.qua_sweep_arr[sweep_idx_var])
            next_action()
            self._advance_step_counter(sweep_idx_var)


    def _parameterize_sweep_array(
        self, param: SequenceParameter, sweep_array: np.ndarray
        ) -> tuple[int, int, int] | tuple[float, float, float]:
        """
        Parameterizes start, stop and step from given sweep array

        Args:
            param (SequenceParameter): Sweep-parameter
            sweep_array (np.ndarray): Array to be parameterized

        Returns:
            (int, int, int) | (float, float, float): Start, stop and step
        """
        start = sweep_array[0]
        stop = sweep_array[-1]
        step = np.mean(np.ediff1d(sweep_array))
        step *= 0.999
        if param.var_type == int:
            start, stop = int(sweep_array[0]), int(sweep_array[-1] + step)
            step = round(step)

        ### This can probably done more elegantly
        length_of_array = len(np.arange(start, stop, step))
        while length_of_array != self.length:
            if length_of_array > self.length:
                stop -= step
            elif length_of_array < self.length:
                stop += step
            length_of_array = len(np.arange(start, stop, step))

        if not length_of_array == self.length:
            raise ValueError(
                "Sweep array must have same length as sweep length or one more."
                f"Is {length_of_array}, should be {self.length}"
                )
        return start, stop, step

    def _parameterize_sweep(self):
        """
        Parameterizes the sweep array in start, stop, step for all paramerters
        with sweep arrays with equal step size
        """
        parameters_sss = {}
        for param in self.parameters:
            if param.can_be_parameterized:
                start, stop, step = self._parameterize_sweep_array(
                    param, self.config[param]*param.scale)
                parameters_sss[param] = {
                    'start': start,
                    'stop': stop,
                    'step': step
                    }
                length_of_array = len(np.arange(start, stop, step))
                warnings.warn(
                    f"\n\tYour input array of length {length_of_array} "
                    f"for {param.name} will be parametrized with\n\t"
                    f"start {start}, step {step}, stop {stop}"
                    f" of length {length_of_array}. \n\tCheck output!",
                    category=ResourceWarning
                    )
        return parameters_sss

    def _advance_step_counter(self, sweep_idx_var):
        """
        Advances the sweep index variable by one step and checks if the
        step requirements are met. This is ONLY doen for the inner most sweep
        hence this will automatically stop advancement of the all outer sweeps

        Args:
            sweep_idx_var (qua variable): Sweep index variable to be advanced
        """
        def step_counter():
            qua.assign(sweep_idx_var, sweep_idx_var + 1)
        if self.measurement.sweeps[-1] == self:
            self.measurement.qua_check_step_requirements(step_counter)
        else:
            step_counter()