""" Module with Sweep class """
import warnings
import logging

import numpy as np
from qm import qua
from qualang_tools import loops
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
        self._inputs_are_streamed = None
        self._input_streams = None
        self._can_be_parameterized = None
        self.register_all = register_all
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
        """ Number of samples for parameters on the given axis """
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
            while parameter.remove_validator(): # remove validators and setup the sweep_validator
                pass
            parameter.add_validator(parameter.sweep_validator)
            parameter.validate(self._param_dict[parameter])
            if self.register_all:
                self._config_to_register[parameter] = self.config[parameter]
            elif i == 0:
                value = self.config[parameter]
                if isinstance(value, (list, np.ndarray)):
                    self._config_to_register[parameter] = value
                elif isinstance(value, int):
                    ### creates a mock set of values (stream array indices)
                    self._config_to_register[parameter] = np.arange(value)
                else:
                    raise ValueError(
                        "Keys in sweep dictionairies must be of type int, list"
                        f"or numpy.ndarray, is:  {type(value)}")
            if isinstance(self.config[parameter], int):
                parameter.input_stream = True
                parameter.add_stream_param_to_sequence()
        if all(param.input_stream is not None for param in self.parameters):
            self._inputs_are_streamed = True
        else:
            self._inputs_are_streamed = False

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

    def qua_generate_parameter_sweep(self, next_action: callable) -> None:
        """
        Runs a qua loop based on the configured method. Currently three
        different methods are available:
            1) From input stream
            2) From parametrized array (start, stop, step)
            3) From an explicitly defined qua array
        """
        if self.inputs_are_streamed:
            self._qua_input_stream_loop(next_action)
        elif self.can_be_parameterized:
            self._qua_parmetrized_loop(next_action)
        else:
            self._qua_explicit_array_loop(next_action)

    def _qua_input_stream_loop(self, next_action: callable) -> None:
        """Runs a qua for loop for an array that is imported from a stream"""
        warnings.warn("Input streaming is not fully supported")
        for param in self.parameters:
            qua.advance_input_stream(param.input_stream)
            logging.debug(
                "Assigning %s with length %s (input stream)",
                param.name, self.length)
        with qua.for_each_(
            self.qua_variables, self.input_streams):
            next_action()

    def _qua_parmetrized_loop(self, next_action: callable) -> None:
        """
        Runs a qua for loop from parametrized qua_arange. Start, stop and step
        are calculated from the input array

        Args:
            next_action (callable): Next action to be executed after the loop
        """
        ### Define start, stop and step for all params that can be parameterized
        parameters_sss = self._parameterize_sweep()

        ### Assigns start values to all parameters that can be parameterized
        for param, sss in parameters_sss.items():
            qua.assign(param.qua_var, sss['start'])

        ### Declaring sweep index variable and respective loop for sweep
        sweep_idx_var = qua.declare(int)
        with qua.for_(
                        var = sweep_idx_var,
                        init = 0,
                        cond = sweep_idx_var < self.length,
                        update = sweep_idx_var + 1
            ):
            for param in self.parameters:
                if not param.can_be_parameterized:
                    qua.assign(
                        param.qua_var, param.qua_sweep_arr[sweep_idx_var])
            qua.align()

            ### This is where either the whole sequence or the next sweep is run
            next_action()

            ### After the sequence the parameter variable is incremented by step
            for param, sss in parameters_sss.items():
                if param.can_be_parameterized:
                    qua.assign(param.qua_var, param.qua_var + sss['step'])

    def _qua_explicit_array_loop(self, next_action):
        """Runs a qua for loop from explicitly defined qua arrays"""
        for param in self.parameters:
            logging.debug(
                "Assigning %s to %s (loop)",
                    param.name, param.qua_sweep_arr)
        with qua.for_each_(self.qua_variables, self.qua_sweep_arrays):
            next_action()

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
                    param, param.get_raw())
                parameters_sss[param] = {
                    'start': start,
                    'stop': stop,
                    'step': step
                    }
                length_of_array = len(np.arange(start, stop, step))
                warnings.warn(
                    f"\n\tYour input array of length {len(param.get())} "
                    f"for {param.name} will be parametrized with\n\t"
                    f"start {start}, step {step}, stop {stop}"
                    f" of length {length_of_array}. \n\tCheck output!"
                    )
        return parameters_sss