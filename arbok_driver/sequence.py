"""Module containing sequence class"""
import math
import logging
from collections import Counter

import numpy as np
from qm import qua
from qcodes.validators import Arrays

from .gettable_parameter import GettableParameter
from .sequence_parameter import SequenceParameter
from .sample import Sample
from .sequence_base import SequenceBase
from .sub_sequence import SubSequence
from .sweep import Sweep

class Sequence(SequenceBase):
    """Class describing a Sequence in an OPX driver"""
    def __init__(
            self,
            parent,
            name: str,
            sample: Sample,
            sequence_config: dict | None = None,
            ) -> None:
        """
        Constructor method for Sequence

        Args:
            name (str): Name of the sequence
            sample (Sample): Sample object describing the device in use
            sequence_config (dict): Config containing all sequence params and
                their initial values and units0
            **kwargs: Key word arguments for InstrumentModule
        """
        super().__init__(parent, name, sample, sequence_config)
        self.driver = parent
        self.parent_sequence = self
        self._init_vars()
        self._reset_sweeps_setpoints()

    def _init_vars(self) -> None:
        """
        Put variables into a reasonable init state
        """
        self._gettables = []
        self._sweep_size = 1
        self.shot_tracker_qua_var = None
        self.shot_tracker_qua_stream = None
        self._step_requirements = []
        self._input_stream_parameters = []
        self._input_stream_type_shapes = {'int': 0, 'bool': 0, 'qua.fixed': 0}
        self.debug_input_streams = False

    def _reset_sweeps_setpoints(self) -> None:
        """
        Reset _sweeps and _setpoints_foir_gettables
        """
        self._sweeps = []
        self._setpoints_for_gettables = ()

    def reset(self) -> None:
        """
        On reset, call super to reset then,
        reset local params, sweeps and gettables
        """
        super().reset()
        self._reset_sweeps_setpoints()
        self._init_vars()

    @property
    def sweeps(self) -> list:
        """List of Sweep objects for `SubSequence`"""
        return self._sweeps

    @property
    def gettables(self) -> list:
        """List of `GettableParameter`s for data acquisition"""
        return self._gettables

    @property
    def sweep_size(self) -> int:
        """Product of sweep axes sizes"""
        self._sweep_size = int(
            math.prod([sweep.length for sweep in self.sweeps]))
        return self._sweep_size

    @property
    def sweep_dims(self) -> int:
        """Dimensionality of sweep axes"""
        self._sweep_dims = (sweep.length for sweep in self.sweeps)
        return self._sweep_size

    @property
    def input_stream_parameters(self) -> list:
        """Registered input stream parameters"""
        return self._input_stream_parameters

    @property
    def step_requirements(self) -> list:
        """Registered input stream parameters"""
        return self._step_requirements

    @input_stream_parameters.setter
    def input_stream_parameters(self, parameters: list) -> None:
        """
        Setter for input stream parameters

        Raises:
            TypeError: If not all parameters are of type SequenceParameter
            ValueError: If not all parameters are unique
        """
        if not all(isinstance(p, SequenceParameter) for p in parameters):
            raise TypeError(
                "All input stream parameters must be of type SequenceParameter"
                )
        if len(parameters) != len(set(parameters)):
            raise ValueError(
                "All input stream parameters must be unique"
                )
        self._input_stream_parameters = parameters

    def qua_declare(self):
        """Contains raw QUA code to declare variables"""
        self.shot_tracker_qua_var = qua.declare(int, value = 0)
        self.shot_tracker_qua_stream = qua.declare_stream()
        self._qua_declare_input_streams()

    def qua_before_sweep(self):
        """
        Qua code to be executed before the sweep loop but after the qua.pause
        statement that aligns the measurement results
        """
        qua.assign(self.shot_tracker_qua_var, 0)
        stream_params = self.input_stream_parameters
        int_params = [p for p in stream_params if p.var_type == int]
        bool_params = [p for p in stream_params if p.var_type == bool]
        fixed_params = [p for p in stream_params if p.var_type == qua.fixed]

        index = qua.declare(int) if self.debug_input_streams else None

        if int_params:
            self._qua_advance_assign_save_input_streams(
                'int', int_params, self._qua_int_input_stream, index)
        if bool_params:
            self._qua_advance_assign_save_input_streams(
                'bool', bool_params, self._qua_bool_input_stream, index)
        if fixed_params:
            self._qua_advance_assign_save_input_streams(
                'fixed', fixed_params, self._qua_fixed_input_stream, index)

    def _qua_advance_assign_save_input_streams(
        self, var_type, input_params, input_stream, index = None):
        """
        Takes the given paramters to stream and the respective input stream and
        advances the input stream, assigns the values to the parameters and
        and saves the values to the respective output streams if debug flag

        Args:
            input_params (list): List of values to be streamed
            input_stream (qua stream): Input stream to advance
            index (qua variable): Index variable for debug output
        """
        qua.advance_input_stream(input_stream)
        for i, param in enumerate(input_params):
            qua.assign(param.qua_var, input_stream[i])
        if self.debug_input_streams:
            input_stream_out = qua.declare_stream()
            setattr(self, f"debug_{var_type}_input_stream", input_stream_out)
            with qua.for_(index, 0, index < len(input_params), index + 1):
                qua.save(input_stream[index], input_stream_out)

    def qua_before_sequence(self, simulate: bool = False):
        """
        Qua code to be executed before the inner sequence
        """
        if simulate:
            for qua_var in self.step_requirements:
                qua.assign(qua_var, True)

    def qua_after_sequence(self):
        """
        Qua code to be executed after the sequence loop and the code it contains
        """
        qua.align()
        self.qua_check_step_requirements(self.qua_increment_shot_tracker)
        qua.align()

    def qua_increment_shot_tracker(self):
        """Increments the shot tracker variable by one and saves it to stream"""
        qua.assign(
            self.shot_tracker_qua_var,
            self.shot_tracker_qua_var + 1
            )
        qua.save(self.shot_tracker_qua_var, self.shot_tracker_qua_stream)

    def qua_stream(self):
        """Contains raw QUA code to define streams"""
        self.shot_tracker_qua_stream.buffer(1).save(self.name + "_shots")
        if self.debug_input_streams:
            for var_type in ['int', 'bool', 'fixed']:
                stream_name = f"debug_{var_type}_input_stream"
                if hasattr(self, stream_name):
                    stream = getattr(self, stream_name)
                    stream.buffer(
                        self._input_stream_type_shapes[var_type]).save_all(
                            stream_name)

    def set_sweeps(self, *args) -> None:
        """
        Sets the given sweeps from its dict type arguments. Each argument
        creates one sweep axis. Each dict key, value pair is sweept concurrently
        along this axis.

        Args:
            *args (dict): Arguments of type dict with SequenceParameters as keys
                and np arrays as setpoints. All values (arrays) must have same
                length!
        """
        if not all(isinstance(sweep_dict, dict) for sweep_dict in args):
            raise TypeError("All arguments need to be of type dict")
        self._reset_sweeps_setpoints()
        for sweep_dict in args:
            logging.debug("Adding parameter sweep for %s", sweep_dict.keys())
            self._sweeps.append(Sweep(self, sweep_dict))
        for sweep in self.sweeps:
            for param, _ in sweep.config_to_register.items():
                self._setpoints_for_gettables += (param,)
        print(
            f"Declared {len(self.sweeps)}-dimensional parameter sweep"
            f" of size {self.sweep_size} {[s.length for s in self.sweeps]}"
        )

    def register_gettables(self, *args) -> None:
        """
        Registers GettableParameters that will be retreived during measurement

        Args:
            *args (GettableParameter): Parameters to be measured
        """
        self._check_given_gettables(args)
        self._gettables = list(args)
        self._configure_gettables()
        self.sweeps.reverse()

    def insert_single_value_input_streams(self, value_dict: dict) -> None:
        """
        Compresses all input streams to single array stream

        Args:
            value_dict (dict): Dictionary containing all input stream parameters
                (SequenceParameters)and their values

        Raises:
            KeyError: If not all input stream parameters that were added to the
                input_stream_parameters attribute are given in value_dict
            ValueError: If the given value_dict contains invalid types
        """
        if Counter(value_dict.keys()) != Counter(self.input_stream_parameters):
            raise KeyError(
                "Given value dict must contain all input stream parameters"
                f"given are: {[p.name for p in value_dict.keys()]}."
                "\n Required are: "
                f"{[p.name for p in self.input_stream_parameters]}"
                f"{len(value_dict)}/{len(self.input_stream_parameters)}"
                )
        int_vals, bool_vals, fixed_vals = [], [], []
        for param in self.input_stream_parameters:
            if param.var_type == int:
                int_vals.append(int(value_dict[param]*param.scale))
            elif param.var_type == qua.fixed:
                fixed_vals.append(float(value_dict[param]*param.scale))
            elif param.var_type == bool:
                bool_vals.append(bool(value_dict[param]))
            else:
                raise ValueError(
                    f"Parameter {param.name} has invalid type {param.var_type}"
                    )
        if int_vals:
            self.driver.qm_job.insert_input_stream(
                name = f"{self.short_name}_int_input_stream",
                data = int_vals
            )
        if bool_vals:
            self.driver.qm_job.insert_input_stream(
                name = f"{self.short_name}_bool_input_stream",
                data = bool_vals
            )
        if fixed_vals:
            self.driver.qm_job.insert_input_stream(
                name = f"{self.short_name}_fixed_input_stream",
                data = fixed_vals
            )

    def _configure_gettables(self) -> None:
        """
        Configures all gettables to be measured. Sets batch_size, can_resume,
        setpoints and vals
        """
        for i, gettable in enumerate(self.gettables):
            gettable.batch_size = self.sweep_size
            gettable.can_resume = True if i==(len(self.gettables)-1) else False
            gettable.setpoints = self._setpoints_for_gettables
            gettable.vals = Arrays(
                shape = tuple(sweep.length for sweep in self.sweeps))

    def _check_given_gettables(self, gettables: list) -> None:
        """
        Check validity of given gettables

        Args:
            gettables (list): List of GettableParameters

        Raises:
            TypeError: If not all gettables are of type GettableParameter
            AttributeError: If not all gettables belong to self
        """
        all_gettable_parameters = all(
            isinstance(gettable, GettableParameter) for gettable in gettables)
        all_gettables_from_self = all(
            gettable.sequence.parent_sequence == self for gettable in gettables)
        if not all_gettable_parameters:
            raise TypeError(
                f"All args need to be GettableParameters, Are: {gettables}")
        if not all_gettables_from_self:
            raise AttributeError(
                f"Not all GettableParameters belong to {self.name}")

    def _qua_declare_input_streams(self) -> None:
        if not self.input_stream_parameters:
            return
        for qua_type in [bool, int, qua.fixed]:
            self._qua_declare_input_stream_type(qua_type)

    def _qua_declare_input_stream_type(
        self, type: int | bool | qua.fixed) -> None:
        length = 0
        for param in self.input_stream_parameters:
            if param.var_type == type:
                length += 1
                param.qua_var = qua.declare(param.var_type)
                param.qua_sweeped = True
        if length > 0:
            input_stream = qua.declare_input_stream(
                type,
                name = f"{self.short_name}_{type.__name__}_input_stream",
                size = length
            )
            setattr(self, f"_qua_{type.__name__}_input_stream", input_stream)
            self._input_stream_type_shapes[type.__name__] = length

    def get_sequence_path(self):
        """Returns its name since sequence is the top level sequence"""
        return self.name

    def add_input_stream_parameter(self, parameter) -> None:
        """Adds given parameter to input stream parameters"""
        if not isinstance(parameter, SequenceParameter):
            raise TypeError(
                "Parameter must be of type SequenceParameter, "
                f"is: {type(parameter)}"
                )
        self._input_stream_parameters.append(parameter)

    def advance_input_streams(self, new_value_dict: dict) -> None:
        """
        Advances all input streams by one step with the new given values

        Args:
            new_value_dict (dict): Dictionary containing all parameters and
                their new values
        """
        if Counter(new_value_dict.keys()) != Counter(self.input_stream_parameters):
            raise KeyError(
                "Given value dict must contain all input stream parameters"
                f"given are: {new_value_dict.keys()}.\n Required are: "
                f"{self.input_stream_parameters}"
                )
        for parameter in self.input_stream_parameters:
            self.driver.qm_job.advance_input_stream(
                name = parameter.full_name
            )

    def qua_check_step_requirements(
        self, action: callable, requirements_list: list = None):
        """
        Checks if the qua variables corresponding to the given save requirements
        are true and save results to GettableParameters. Otherwise continue
        without saving.
        This is useful for feedback sequences or conditional operations.
        """
        if requirements_list is None:
            requirements_list = self.step_requirements
        if len(requirements_list) == 0:
            action()
        else:
            with qua.if_(requirements_list[0]):
                self.qua_check_step_requirements(action, requirements_list[1:])

    def find_parameter_from_sub_sequence(self, attr_path: str) -> SequenceParameter:
        """Returns the parameter from a given path"""
        keyword_list = attr_path.split(".")
        current_attr = self
        for attr in keyword_list:
            try:
                current_attr = getattr(current_attr, attr)
            except AttributeError as exc:
                raise AttributeError(
                    f"Attribute {attr} not found in {self.name}"
                    ) from exc
        if callable(current_attr):
            return current_attr()
        else:
            return current_attr

    def reshape_results_from_sweeps(self, results: np.ndarray) -> np.ndarray:
        """
        Reshapes the results array to the shape of the setpoints from sweeps

        Args:
            results (np.ndarray): Results array

        Returns:
            np.ndarray: Reshaped results array
        """
        return results.reshape(tuple((reversed(s.length) for s in self.sweeps)))

    def add_step_requirement(self, requirement) -> None:
        """Adds a bool qua variable as a step requirement for the sequence"""
        logging.debug('Adding step requirement: %s', requirement)
        self._step_requirements.append(requirement)

    def _add_subsequence(
        self,
        name: str,
        subsequence: SubSequence | str,
        sequence_config: dict = None,
        insert_sequences_into_name_space: dict = None,
        **kwargs) -> None:
        """Adds a subsequence to the sequence"""
        if subsequence == 'default':
            subsequence = SubSequence
        if not issubclass(subsequence, SubSequence):
            raise TypeError(
                "Subsequence must be of type SubSequence or str: 'default'")
        seq_instance = subsequence(
            parent = self,
            name = name,
            sample = self.sample,
            sequence_config = sequence_config,
            **kwargs
            )
        setattr(self, name, seq_instance)
        if insert_sequences_into_name_space is not None:
            name_space = insert_sequences_into_name_space
            name_space[name] = seq_instance
        return seq_instance
