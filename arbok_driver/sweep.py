""" Module with Sweep class """
from __future__ import annotations
from collections.abc import Callable
from typing import TYPE_CHECKING
import warnings
import logging

import numpy as np
from qm import qua
from qm.qua.lib import Cast
from qcodes.parameters import Parameter
from qcodes.validators import Arrays

from .parameters.sequence_parameter import SequenceParameter
if TYPE_CHECKING:
    from .measurement import Measurement
    from qm.qua._expressions import QuaVariable, QuaVariableInputStream
    from numpy import ndarray

class Sweep:
    """ Class characterizing a parameter sweep along one axis in the OPX """

    _length: int
    _input_streams: list[QuaVariableInputStream]
    _can_be_parameterized: bool
    snake_scan: bool
    dim_parameter: SequenceParameter

    def __init__(
            self, measurement : Measurement,
            param_dict: dict,
            register_all = False
            ):
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
        self.measurement: Measurement = measurement
        self.register_all: bool = register_all
        self._config: dict[SequenceParameter, ndarray] = param_dict
        self._inputs_are_streamed: bool = False
        self.snake_scan: bool = False
    
        self._parameters: list[SequenceParameter] = []
        self.inferred_parameters: list[SequenceParameter] = []
        self._config_to_register: dict[SequenceParameter, ndarray] = {}

        self.configure_sweep()
        self._check_if_parametrizable()

    @property
    def parameters(self) -> list[SequenceParameter]:
        """ List containing all varied parameters """
        return self._parameters

    @property
    def qua_variables(self) -> tuple(QuaVariable):
        """ Tuple containing all qua variables of parameters """
        return tuple(par.qua_var for par in self.parameters)

    @property
    def qua_sweep_arrays(self) -> tuple(ndarray):
        """ Tuple containing all qua sweep arrays of parameters """
        return tuple(par.qua_sweep_arr for par in self.parameters)

    @property
    def length(self) -> int:
        """Length of sweep array for parameters on the given axis """
        return self._length

    @property
    def input_streams(self):
        """Returns all input streams if the sweep is set up to be streamed"""
        return tuple(par.input_stream for par in self.parameters)

    @property
    def inputs_are_streamed(self) -> bool:
        """Whether sweep is fed by input stream"""
        return self._inputs_are_streamed
    
    @inputs_are_streamed.setter
    def inputs_are_streamed(self, value: bool) -> None:
        if isinstance(value, bool):
            for param in self.parameters:
                param.has_input_stream = value
                print(f"Enabling input stream on {param.register_name}")
            self._inputs_are_streamed = value
        else:
            raise ValueError("Must be True or False.")

    @property
    def can_be_parameterized(self):
        """
        Whether sweep can be parameterized with start, stop and step for memory
        saving. If the user has not set this value, it will be checked by the
        entries of the given arrays
        """
        self._can_be_parameterized = self._check_if_parametrizable()
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
                return
        else:
            raise ValueError("can_be_parameterized must be of type bool")

    @property
    def config(self) -> dict[SequenceParameter, ndarray]:
        """Config dict for parameter sweep. Keys are params, values setpoints"""
        return self._config

    @property
    def config_to_register(self) -> dict:
        """ Parameters that will be registered in QCoDeS measurement """
        return self._config_to_register

    def configure_sweep(self) -> None:
        """
        Configures the sweep from the given dictionairy
        TODO: This breaks the input stream implementation, needs to be fixed
              i am quite sure this can be done more elegantly!
              perhaps not even using set_sweeps but a different method on measurement
        """
        self.check_input_dict()

        self._parameters = []
        self.inferred_parameters = []
        self._config_to_register = {}
        for i, parameter in enumerate(self.config.keys()):
            self._parameters.append(parameter)
            ### Remove scalar validators and setup the sweep_validator
            setpoints = parameter.convert_to_real_units(
                self.config[parameter])
            while parameter.remove_validator(): pass
            parameter.vals = Arrays(shape = (len(setpoints),))
            parameter.validate(setpoints)
            parameter.set(setpoints)
            if i == 0:
                self.dim_parameter = parameter
                self._config_to_register[parameter] = setpoints
            else:
                self.inferred_parameters.append(parameter)
                parameter.is_controlled_by.add(self.dim_parameter)
                self.dim_parameter.has_control_of.add(parameter)

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
            if param.var_type not in (int, bool, qua.fixed):
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
        if self.length < 5:
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

    def qua_generate_parameter_sweep(
            self, next_action: Callable, next_sweep) -> None:
        """
        Runs a qua loop based on the configured method. Currently three
        different methods are available:
            1) From input stream
            2) From parametrized array (start, stop, step)
            3) From an explicitly defined qua array
        If the next (inner) sweep uses snaking, its direction variable is reset
        before entering that sweep so it starts in the correct direction.
        """
        if next_sweep is not None and next_sweep.snake_scan:
            qua.assign(next_sweep._snake_forward, False)

        if self.inputs_are_streamed:
            self._qua_input_stream_loop(next_action)
        elif self.can_be_parameterized:
            self._qua_parmetrized_loop(next_action)
        else:
            self._qua_explicit_array_loop(next_action)

    def declare_snake_variable(self) -> None:
        """
        Declares the QUA boolean variable that tracks sweep direction.
        Initialized to False; toggled at the start of each sweep execution,
        so the first pass runs forward (True).
        """
        self._snake_forward = qua.declare(bool, False)

    def _qua_toggle_and_branch(
            self, sweep_idx_var, forward_body: Callable, reverse_body: Callable
            ) -> None:
        """
        Reusable snake-scan branching. Toggles direction, then executes
        either forward_body or reverse_body depending on sweep direction.
        Both callables receive the raw sweep_idx_var; the caller is
        responsible for computing the effective index inside.

        When snake_scan is False, simply calls forward_body directly.
        """
        if not self.snake_scan:
            forward_body(sweep_idx_var)
            return

        with qua.if_(self._snake_forward):
            forward_body(sweep_idx_var)
        with qua.else_():
            reverse_body(sweep_idx_var)

    def _reverse_idx(self, sweep_idx_var):
        """Returns the QUA expression for the reversed index."""
        return self.length - 1 - sweep_idx_var

    def _qua_input_stream_loop(self, next_action: Callable) -> None:
        """Runs a qua for loop for an array that is imported from a stream"""
        warnings.warn("Input streaming is not fully supported")
        for param in self.parameters:
            qua.wait(int(1e6)) # TODO: Check if this is still necessary!
            qua.advance_input_stream(param.input_stream)
            logging.debug(
                "Assigning %s with length %s (input stream)",
                param.name, self.length)

        sweep_idx_var = qua.declare(int)
        if self.snake_scan:
            qua.assign(self._snake_forward, ~self._snake_forward)

        qua.assign(sweep_idx_var, 0)
        with qua.while_(sweep_idx_var < self.length):
            def assign_forward(idx):
                for param in self.parameters:
                    qua.assign(param.qua_var, param.input_stream[idx])

            def assign_reverse(idx):
                rev = self._reverse_idx(idx)
                for param in self.parameters:
                    qua.assign(param.qua_var, param.input_stream[rev])

            self._qua_toggle_and_branch(
                sweep_idx_var, assign_forward, assign_reverse)
            next_action()
            self._advance_step_counter(sweep_idx_var)

    def _qua_parmetrized_loop(self, next_action: Callable) -> None:
        """
        Runs a qua for loop from parametrized qua_arange. Start, stop and step
        are calculated from the input array.
        """
        parameters_sss = self._parameterize_sweep()

        sweep_idx_var = qua.declare(int)
        if self.snake_scan:
            qua.assign(self._snake_forward, ~self._snake_forward)

        qua.assign(sweep_idx_var, 0)
        with qua.while_(sweep_idx_var < self.length):
            for param in self.parameters:
                if not param.can_be_parameterized:
                    qua.assign(
                        param.qua_var, param.qua_sweep_arr[sweep_idx_var])

            def assign_forward(idx):
                for param, sss in parameters_sss.items():
                    self._qua_calc_param_value(param, sss, idx, reverse=False)

            def assign_reverse(idx):
                for param, sss in parameters_sss.items():
                    self._qua_calc_param_value(param, sss, idx, reverse=True)

            self._qua_toggle_and_branch(
                sweep_idx_var, assign_forward, assign_reverse)

            qua.align()
            next_action()
            self._advance_step_counter(sweep_idx_var)

    def _qua_calc_param_value(self, param, sss, sweep_idx_var, reverse: bool):
        """
        Assigns the parameter's QUA variable to the correct value for the
        current sweep index. When reversed, counts backwards from stop.

        Written explicitly to avoid multiplications by -1 on the FPGA.
        """
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
                    sss['start'] + Cast.mul_fixed_by_int(
                        sss['step'], sweep_idx_var))
            else:
                qua.assign(
                    param.qua_var,
                    sss['stop'] - Cast.mul_fixed_by_int(
                        sss['step'], sweep_idx_var))
        else:
            raise TypeError(
                "Only int and fixed qua types are supported for param sweeps")

    def _qua_explicit_array_loop(self, next_action):
        """Runs a qua for loop from explicitly defined qua arrays"""
        for param in self.parameters:
            logging.debug(
                "Assigning %s to %s (loop)",
                    param.name, param.qua_sweep_arr)

        sweep_idx_var = qua.declare(int)
        if self.snake_scan:
            qua.assign(self._snake_forward, ~self._snake_forward)

        qua.assign(sweep_idx_var, 0)
        with qua.while_(sweep_idx_var < self.length):
            def assign_forward(idx):
                for param in self.parameters:
                    qua.assign(param.qua_var, param.qua_sweep_arr[idx])

            def assign_reverse(idx):
                rev = self._reverse_idx(idx)
                for param in self.parameters:
                    qua.assign(param.qua_var, param.qua_sweep_arr[rev])

            self._qua_toggle_and_branch(
                sweep_idx_var, assign_forward, assign_reverse)
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
        if param.var_type is int:
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

    def remove_parameter_dependencies(self) -> None:
        """
        Removes all qcodes parameter dependencies set by is_controlled_by
        and has_control_of methods.
        """
        for parameter in self.inferred_parameters:
            self.dim_parameter.has_control_of.remove(parameter)
            parameter.is_controlled_by.remove(self.dim_parameter)