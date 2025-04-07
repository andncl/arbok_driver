"""Module containing the Measurement class"""
import math
import copy
import logging
from collections import Counter

import numpy as np
from qm import qua, generate_qua_script
import qcodes as qc
from qcodes.validators import Arrays

from .measurement_helpers import create_measurement_loop
from .gettable_parameter import GettableParameter
from .observable import ObservableBase
from .sequence_parameter import SequenceParameter
from .sample import Sample
from .sequence_base import SequenceBase
from .sub_sequence import SubSequence
from .sweep import Sweep

class Measurement(SequenceBase):
    """Class describing a Measurement in an OPX driver"""
    qc_experiment = None
    qc_measurement = None
    qc_measurement_name = None

    def __init__(
            self,
            parent,
            name: str,
            sample: Sample,
            sequence_config: dict | None = None,
            ) -> None:
        """
        Constructor method for Measurement

        Args:
            name (str): Name of the measurement
            sample (Sample): Sample object describing the device in use
            sequence_config (dict): Config containing all measurement params and
                their initial values and units0
            **kwargs: Key word arguments for InstrumentModule
        """
        conf = self.merge_with_sample_config(sample, sequence_config)
        super().__init__(parent, name, sample, conf)
        self.driver = parent
        self.measurement = self
        self._init_vars()
        self._reset_sweeps_setpoints()
        parent.add_sequence(self)

    def merge_with_sample_config(self, sample, sequence_config):
        """
        Merges a sequence configuration with a sample's master configuration.

        If both sequence_config and sample.master_config are provided, the
        sample's master configuration takes precedence in case of key
        conflicts.

        Args:
            sample: An object with a 'master_config' attribute (dict or None).
            sequence_config: A dictionary representing the sequence configuration,
                             or None.

        Returns:
            A new dictionary containing the merged configurations. If neither
            sequence_config nor sample.master_config is provided, an empty
            dictionary is returned.
        """
        # update the master_config overrides sequence_config, if present
        s_c = {}
        if sequence_config is not None:
            s_c.update(sequence_config)
        # refresh the master config and overwrite the sample config with it
        sample.reload_master_config()
        if sample.master_config is not None:
            s_c.update(sample.master_config)
        return s_c

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
        self._available_gettables = []
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

    def reset_registered_gettables(self) -> None:
        """Resets gettables to prepare for new measurement"""
        for gettable in self.gettables:
            gettable.reset_measuerement_attributes()

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

    @property
    def available_gettables(self) -> list:
        """List of all available gettables from all sub sequences"""
        return self._available_gettables

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
        Qua code to be executed before the inner measurement
        """
        if simulate:
            for qua_var in self.step_requirements:
                qua.assign(qua_var, True)

    def qua_after_sequence(self):
        """
        Qua code to be executed after the measurement loop and the code it contains
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

        ### Gettables are registered again to update their setpoints
        ### This is necessary if sweeps of different shape have been set
        #self.register_gettables(self._gettables)
        print(
            f"Declared {len(self.sweeps)}-dimensional parameter sweep"
            f" of size {self.sweep_size} {[s.length for s in self.sweeps]}"
        )

    def register_gettables(self, *args, keywords: str | list | tuple = None
                           ) -> None:
        """
        Registers GettableParameters that will be retreived during measurement.
        Gettable parameters can be given as arguments or automatically seached
        by keywords. 

        Args:
            *args (GettableParameter): Parameters to be measured
            keywords (str | list): Keywords to find gettables by name
        """
        gettables = list(args)
        if keywords is not None:
            if isinstance(keywords, str) or isinstance(keywords, tuple):
                keywords = [keywords]
            if isinstance(keywords, list):
                for keyword in keywords:
                    gettables.extend(self._find_gettables_from_keyword(keyword))
            else:
                raise TypeError(
                    f"Keywords must be of type str or list. Is {type(keywords)}")
        ### Remove duplicates
        gettables = list(dict.fromkeys(gettables))
        self._check_given_gettables(gettables)
        self._gettables = list(gettables)
        self._configure_gettables()
        self.sweeps.reverse()

    def _find_gettables_from_keyword(self, keyword: str | tuple) -> list:
        """Returns all gettables that contain the given keyword"""
        if isinstance(keyword, str):
            keyword = (keyword,)
        if not isinstance(keyword, tuple):
            raise TypeError(
                "Keyword must be of type str or tuple."
                f" Is {type(keyword)}")
        gettables = []
        for gettable in self.available_gettables:
            if all([sub_key in gettable.name for sub_key in keyword]):
                gettables.append(gettable)
        return gettables

    def get_qua_code(self, simulate = False) -> qua.program:
        """
        Compiles all qua code from its sub-sequences and writes their loops
        
        Args:
            simulate (bool): True if the program is meant to be simulated

        Reterns:
            qua_program: Program from qm context manager
        """
        ### In the first step all variables of all sub-sequences are declared
        self.qua_declare_sweep_vars()
        self.recursive_qua_generation(
            seq_type = 'declare', skip_duplicates = True)

        ### An infinite loop starting with a pause is defined to sync the
        ### client with the QMs
        with qua.infinite_loop_():
            if not simulate:
                qua.pause()

            ### Check requirements are set to True if the measurement is simulated
            if simulate:
                for qua_var in self.measurement.step_requirements:
                    qua.assign(qua_var, True)

            ### The sub-sequences are run in the order they were added
            ### Before_sweep methods are run before the sweep loop
            self.recursive_qua_generation(
                seq_type = 'before_sweep', skip_duplicates = True)

            ### The sweep loop is defined for each sub-sequence recursively
            self.recursive_sweep_generation(
                copy.copy(self.sweeps))
        with qua.stream_processing():
            self.recursive_qua_generation(seq_type = 'stream')

    def compile_qua_and_run(self, save_path: str = None) -> None:
        """Compiles the QUA code and runs it"""
        self.reset_registered_gettables()
        qua_program = self.get_qua_program()
        print('QUA program compiled')
        if save_path:
            with open(save_path, 'w', encoding="utf-8") as file:
                file.write(generate_qua_script(qua_program))
        print('QUA program saved')
        self.driver.run(qua_program)
        print('QUA program compiled and is running')

    def insert_single_value_input_streams(self, value_dict: dict) -> None:
        """
        Compresses all input streams to single array stream

        Args:
            value_dict (dict): Dictionary containing all input stream parameters
                (SequenceParameters) and their values

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

    def add_available_gettables(self, gettables: list) -> None:
        """
        Adds given gettables to the list of all gettables

        Args:
            gettables (list): List of GettableParameters
        """
        self._available_gettables.extend(gettables)

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
        ### Replace observables with their gettables if present
        gettables_without_observabels = []
        for gettable in gettables:
            if isinstance(gettable, ObservableBase):
                gettables_without_observabels.append(gettable.gettable)
            else:
                gettables_without_observabels.append(gettable)
        gettables = gettables_without_observabels
        ### Check if gettables are of type GettableParameter and belong to self
        all_gettable_parameters = all(
            isinstance(gettable, GettableParameter) for gettable in gettables)
        all_gettables_from_self = all(
            gettable.sequence.measurement == self for gettable in gettables)
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
        """Returns its name since Measurement is the top level"""
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
        """Adds a bool qua variable as a step requirement for the measurement"""
        logging.debug('Adding step requirement: %s', requirement)
        self._step_requirements.append(requirement)

    def _add_subsequence(
        self,
        name: str,
        subsequence: SubSequence,
        sequence_config: dict = None,
        insert_sequences_into_name_space: dict = None,
        **kwargs
        ) -> None:
        """
        Adds a subsequence to the sequence
        
        Args:
            name (str): Name of the subsequence
            subsequence (SubSequence): Subsequence to be added
            sequence_config (dict): Config containing all measurement params
            insert_sequences_into_name_space (dict): Name space to insert the
                subsequence into (e.g locals(), globals()) defaults to None
        """
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

    def get_qc_measurement(
            self, measurement_name: str) -> qc.dataset.Measurement:
        """
        Creates a QCoDeS measurement from the given experiment
        
        Args:
            measurement_name (str): Name of the QCoDeS measurement
                (as it will be saved in the database)
                
        Returns:
            qc_measurement (qc.dataset.Measurement): Measurement instance
        """
        self.qc_measurement = qc.dataset.Measurement(
            exp = self.qc_experiment, name = measurement_name)
        return self.qc_measurement

    def get_measurement_loop_function(self, sweep_list_arg: list) -> callable:
        """
        Returns the measurement loop function
        
        Args:
            sweep_list_arg (list): List of of sweep dicts for external instruments

        Returns:
            run_loop (callable): Measurement loop function
        """
        if self.qc_experiment is None:
            raise ValueError("No QCoDeS experiment set")
        if self.qc_measurement is None:
            _ = self.get_qc_measurement(self.qc_measurement_name)
        if self.sweeps is None:
            raise ValueError("No sweeps set")

        @create_measurement_loop(
            sequence = self,
            measurement = self.qc_measurement,
            sweep_list = sweep_list_arg)
        def run_loop():
            pass
        return run_loop
