"""Module containing the Measurement class"""
from __future__ import annotations
from typing import TYPE_CHECKING
import math
import time
import copy
import logging
import os
from collections import Counter
import warnings


from qm import qua, generate_qua_script
import qcodes as qc
from qcodes.dataset.data_set import DataSet
import xarray

from .measurement_runners import(
    NativeMeasurementRunner,
    QCodesMeasurementRunner
)
from .gettable_parameter import GettableParameter
from .sequence_parameter import SequenceParameter
from .sequence_base import SequenceBase
from .sub_sequence import SubSequence
from .sweep import Sweep

if TYPE_CHECKING:
    from .arbok_driver import ArbokDriver
    from .arbok_driver import Device
    from arbok_driver.measurement_runners.measurement_runner_base import (
        MeasurementRunnerBase,
    )
    from qcodes.dataset import Measurement as QcMeasurement
    from xarray import Dataset as XrDataset

class Measurement(SequenceBase):
    """Class describing a Measurement in an OPX driver"""
    qc_experiment = None
    qc_measurement = None
    qc_measurement_name = None

    def __init__(
            self,
            parent,
            name: str,
            device: Device,
            sequence_config: dict | None = None,
            ) -> None:
        """
        Constructor method for Measurement

        Args:
            name (str): Name of the measurement
            device (Device): Device object describing the device in use
            sequence_config (dict): Config containing all measurement params and
                their initial values and units0
            **kwargs: Key word arguments for InstrumentModule
        """
        conf = self.merge_with_device_config(device, sequence_config)
        super().__init__(parent, name, device, conf)
        self.driver: ArbokDriver = parent
        self.measurement = self
        self._init_vars()
        self._reset_sweeps_setpoints()
        self.driver.add_measurement(self)

        self.qc_measurement: QcMeasurement | None = None

        self._is_mock: bool = False
        self._sweep_dims: tuple | None = None
        self._sweep_size: int | None = None
        self.measurement_runner: MeasurementRunnerBase | None = None

        self.shot_tracker_qua_var = None
        self.shot_tracker_qua_stream = None
        self.nr_registered_results = 0

        self.qm_job = None
        self.batch_counter = None
        ### the following are being set by the measurement runner
        self._run_id: int | None = None
        self._dataset: XrDataset | None = None

    def merge_with_device_config(self, device, sequence_config):
        """
        Merges a sequence configuration with a device's master configuration.

        If both sequence_config and device.master_config are provided, the
        device's master configuration takes precedence in case of key
        conflicts.

        Args:
            device: An object with a 'master_config' attribute (dict or None).
            sequence_config: A dictionary representing the sequence configuration,
                             or None.

        Returns:
            A new dictionary containing the merged configurations. If neither
            sequence_config nor device.master_config is provided, an empty
            dictionary is returned.
        """
        # update the master_config overrides sequence_config, if present
        s_c = {}
        if sequence_config is not None:
            s_c.update(sequence_config)
        # refresh the master config and overwrite the device config with it
        device.reload_master_config()
        if device.master_config is not None:
            s_c.update(device.master_config)
        return s_c

    def _init_vars(self) -> None:
        """
        Put variables into a reasonable init state
        """
        self._gettables = []
        self._sweep_size = 1
        self._sweep_dims = ()
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
        for _, gettable in self.gettables.items():
            gettable.reset_measuerement_attributes()

    @property
    def sweeps(self) -> list[Sweep]:
        """List of Sweep objects for `SubSequence`"""
        return self._sweeps

    @property
    def gettables(self) -> dict[str, GettableParameter]:
        """List of `GettableParameter`s for data acquisition"""
        return self._gettables

    @property
    def sweep_size(self) -> int:
        """Product of sweep axes sizes"""
        self._sweep_size = int(
            math.prod([sweep.length for sweep in self.sweeps]))
        return self._sweep_size

    @property
    def sweep_dims(self) -> tuple[int]:
        """Dimensionality of sweep axes"""
        self._sweep_dims = tuple((sweep.length for sweep in self.sweeps))
        return self._sweep_dims

    @property
    def input_stream_parameters(self) -> list[SequenceParameter]:
        """Registered input stream parameters"""
        return self._input_stream_parameters

    @property
    def step_requirements(self) -> list:
        """Registered input stream parameters"""
        return self._step_requirements

    @property
    def available_gettables(self) -> list[GettableParameter]:
        """List of all available gettables from all sub sequences"""
        return self._available_gettables

    @property
    def is_mock(self) -> bool:
        """Returns True if the measurement is a mock measurement"""
        if self.driver.is_mock:
            return True
        return self._is_mock

    @property
    def run_id(self) -> int:
        """Run id of the measurement"""
        return self._run_id
    
    def _set_run_id(self, run_id: int) -> None:
        """Sets the run id of the measurement"""
        self._run_id = run_id

    @property
    def dataset(self) -> XrDataset:
        """Xarray Dataset of the measurement"""
        return self._dataset
    
    def _set_dataset(self, dataset: XrDataset) -> None:
        """Sets the xarray dataset of the measurement"""
        self._dataset = dataset

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
        for sub_sequence in self.sub_sequences:
            sub_sequence.qua_declare()

    def qua_before_sweep(self) -> None:
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
        self, var_type, input_params, input_stream, index = None) -> None:
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
        for sub_sequence in self.sub_sequences:
            sub_sequence.qua_before_sequence()

    def qua_after_sequence(self):
        """
        Qua code to be executed after the measurement loop and the code it contains
        """
        for sub_sequence in self.sub_sequences:
            sub_sequence.qua_after_sequence()
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
        for sub_sequence in self.sub_sequences:
            sub_sequence.qua_stream()

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

    def register_gettables(
            self,
            *args,
            keywords: str | list | tuple = None,
            verbose: bool = False
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
                    found_gettables = self._find_gettables_from_keyword(keyword)
                    for g in found_gettables:
                        if verbose:
                            print(
                               f"From keyword '{keyword}' adding: '{g.full_name}'")
                    gettables.extend(found_gettables)
            else:
                raise TypeError(
                    f"Keywords must be of type str or list. Is {type(keywords)}")
        ### Remove duplicates
        gettables = list(dict.fromkeys(gettables))
        gettables = {g.name: g for g in gettables}
        self._check_given_gettables(gettables)

        self._gettables = gettables
        if len(self._gettables) == 0:
            warnings.warn(f"No gettables registered for measurement {self.name}")
        self._configure_gettables()
        print(f"Registered {len(self._gettables)} gettables for measurement")

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
        self.qua_declare()

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
            self.qua_before_sweep()
            ### The sweep loop is defined for each sub-sequence recursively
            ### Reversing the sweeps is necessary to have the outermost sweep
            ### loop first (e.g last element in the list is the innermost sweep)
            self.recursive_sweep_generation(
                copy.copy(self.sweeps)
                )
        with qua.stream_processing():
            self.qua_stream()

    def compile_qua_and_run(self, save_path: str = None) -> None:
        """Compiles the QUA code and runs it"""
        self.reset_registered_gettables()
        self.register_gettables(*list(self.gettables.values()))

        self.nr_registered_results = 0
        self.qua_program = self.get_qua_program()
        print('QUA program compiled')
        if save_path:
            # Check if the directory exists
            directory = os.path.dirname(save_path)
            if directory and not os.path.exists(directory):
                raise FileNotFoundError(
                    f"Directory '{directory}' does not exist. "
                    f"Please create the directory before saving the QUA script."
                )
            with open(save_path, 'w', encoding="utf-8") as file:
                file.write(
                    generate_qua_script(self.qua_program, self.parent.device.config))
            print('QUA program saved')

        if not self.driver.is_mock:
            self.driver.run(self.qua_program)
            self.qm_job = self.driver.qm_job
            self._add_streams_to_gettables()
            self.batch_counter = getattr(
                self.driver.qm_job.result_handles,
                f"{self.name}_shots"
            )
        print('QUA program compiled and is running')
        return self.qua_program

    def _add_streams_to_gettables(self):
        for _, gettable in self.gettables.items():
            gettable.qm_job = self.driver.qm_job
            gettable.set_qm_buffer(self.driver.qm_job)

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
        for _, gettable in self.gettables.items():
            gettable.setpoints = self._setpoints_for_gettables
            gettable.configure_from_measurement()

    def _check_given_gettables(self, gettables: dict) -> None:
        """
        Check validity of given gettables

        Args:
            gettables (list): List of GettableParameters

        Raises:
            TypeError: If not all gettables are of type GettableParameter
            AttributeError: If not all gettables belong to self
        """
        ### Replace observables with their gettables if present
        gettables = gettables.values()
        ### Check if gettables are of type GettableParameter and belong to self
        all_gettable_parameters = all(
            isinstance(gettable, GettableParameter) for gettable in gettables)
        all_gettables_from_self = all(
            gettable.measurement == self for gettable in gettables)
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
        self, qua_type: int | bool | qua.fixed) -> None:
        length = 0
        for param in self.input_stream_parameters:
            if param.var_type == qua_type:
                length += 1
                param.qua_var = qua.declare(param.var_type)
                param.qua_sweeped = True
        if length > 0:
            input_stream = qua.declare_input_stream(
                qua_type,
                name = f"{self.short_name}_{qua_type.__name__}_input_stream",
                size = length
            )
            setattr(self, f"_qua_{qua_type.__name__}_input_stream", input_stream)
            self._input_stream_type_shapes[qua_type.__name__] = length

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

    def add_step_requirement(self, requirement) -> None:
        """Adds a bool qua variable as a step requirement for the measurement"""
        logging.debug('Adding step requirement: %s', requirement)
        self._step_requirements.append(requirement)

    def add_subsequences_from_dict(
            self,
            subsequence_dict: dict,
            namespace_to_add_to: dict = None) -> None:
        """
        Adds subsequences to the sequence from a given dictionary

        Args:
            subsequence_dict (dict): Dictionary containing the subsequences
            namespace_to_add_to (dict): Name space to insert the
                subsequence into (e.g locals(), globals()) defaults to None
        """
        super()._add_subsequences_from_dict(
            default_sequence = SubSequence,
            subsequence_dict = subsequence_dict,
            namespace_to_add_to = namespace_to_add_to
        )

    def get_qc_measurement(
            self, measurement_name: str = None) -> qc.dataset.Measurement:
        """
        Creates a QCoDeS measurement from the given experiment
        
        Args:
            measurement_name (str): Name of the QCoDeS measurement
                (as it will be saved in the database)
                
        Returns:
            qc_measurement (qc.dataset.Measurement): Measurement instance
        """
        if measurement_name is None:
            if self.qc_measurement_name is None:
                raise ValueError(
                    "No measurement name given and no default set")
            measurement_name = self.qc_measurement_name
        self.qc_measurement = qc.dataset.Measurement(
            exp = self.qc_experiment, name = measurement_name)
        return self.qc_measurement

    def get_xr_dataset_and_id(self) -> tuple[XrDataset, int]:
        """
        Creates a QCoDeS dataset from the given experiment
        TODO: THIS NEEDS TO BE IN QCODES MEASUREMENT RUNNER

        Returns:
            qc_dataset (qc.dataset.Dataset): Dataset instance
        """
        dataset = self.qc_experiment.data_sets()[-1]
        meas_id = dataset.run_id
        xdata = dataset.to_xarray_dataset()
        print(f"Returning last dataset of experiment type with id {meas_id}")
        return xdata, meas_id

    def run_measurement(
            self,
            ext_sweep_list: list[dict] | None = None,
            inner_func = None,
            qua_program_save_path: str = None,
            opx_address: str = None,
            measurement_backend: str = 'qcodes',
            ) -> XrDataset:
        """
        Runs the measurement with the given sweep list based on MeasurementRunner
        class
        TODO: add default save path! 

        Args:
            ext_sweep_list (list[dict]): List of dictionaries with parameters as keys
                and np.ndarrays as setpoints. Each list entry creates one sweep axis.
                If you want to sweep params concurrently enter more entries into
                their sweep dict
            inner_func (callable): The function to be executed for each setpoint
                in the sweep list (e.g on every opx data fetch)
            qua_program_save_path (str): The file path to save the compiled
                QUA program. Defaults to None. If not given, the program is
                being auto-saved next to the database.
            opx_address (str): The address of the OPX. Defaults to None. If not
                given does not attempt to connect to the OPX.
            measurement_backend (str): The measurement backend to use. Can be either
                'qcodes' or 'native'.
        """
        if opx_address is not None:
            self.driver.connect_opx(opx_address)
        qua_prog = self.compile_qua_and_run(save_path = qua_program_save_path)
        self.measurement_runner = self.get_measurement_runner(
            ext_sweep_list, measurement_backend)
        self.measurement_runner.run_arbok_measurement(
            inner_func = inner_func)
        return self.dataset

    def get_measurement_runner(
            self,
            ext_sweep_list: list[dict] | None = None,
            measurement_backend: str = 'qcodes') -> MeasurementRunnerBase:
        """
        Returns the measurement runner for the current measurement

        Args:
            ext_sweep_list (list[dict]): List of dictionaries with parameters as keys
                and np.ndarrays as setpoints. Each list entry creates one sweep axis.
                If you want to sweep params concurrently enter more entries into
                their sweep dict
            measurement_backend (str): The measurement backend to use. Can be either
                'qcodes' or 'native'.

        Returns:
            MeasurementRunner: The measurement runner instance
        """
        if measurement_backend == 'qcodes':
            self.measurement_runner = QCodesMeasurementRunner(
                measurement = self,
                ext_sweep_list = ext_sweep_list
                )
        elif measurement_backend == 'native':
            self.measurement_runner = NativeMeasurementRunner(
                measurement = self,
                ext_sweep_list = ext_sweep_list
                )
        else:
            raise ValueError(
                f"Invalid measurement backend: {measurement_backend}. "
                "Choose either 'qcodes' or 'native'."
                )
        return self.measurement_runner

    def wait_until_result_buffer_full(self, progress_tracker: tuple = None):
        """
        Waits until the result buffer is full and updates the progress bar if given

        Args:
            progress_bar (tuple): Tuple containing the progress bar and the
                total number of results
        """
        bar_title = "[slate_blue1]Batch progress\n "
        batch_count = 0
        time_per_shot = 0
        shot_timing = "Calculate timing...\n"
        total_results = "Total results: ..."
        t0 = time.time()
        if self.is_mock:
            self._mock_wait_until_result_buffer_full(progress_tracker, bar_title)
            return
        ### Add checks if job exists and is running
        ### Also check if streams are available
        try:
            is_paused = self.driver.qm_job.is_paused()
            while batch_count < self.sweep_size and not is_paused:
                logging.debug(
                    "Waiting for buffer to fill (%s/%s), is paused: %s",
                    batch_count, self.sweep_size, is_paused
                    )
                shot_count_result = self.batch_counter.fetch_all()
                if shot_count_result is not None:
                    batch_count = shot_count_result[0]
                    total_nr_results = batch_count + self.nr_registered_results
                    total_results = f"Total results: {total_nr_results}"
                if progress_tracker is not None:
                    count = f"{batch_count}/{self.sweep_size}\n"
                    if batch_count > 0:
                        time_per_shot = 1e3*(time.time()-t0)/(batch_count)
                    shot_timing = f" {time_per_shot:.1f}ms/shot\n"
                    progress_tracker[1].update(
                        progress_tracker[0],
                        completed = batch_count,
                        description = bar_title+count+shot_timing+total_results
                    )
                    progress_tracker[1].refresh()
        except KeyboardInterrupt as exc:
            raise KeyboardInterrupt('Measurement interrupted by user') from exc
        if progress_tracker is not None:
            progress_tracker[1].update(progress_tracker[0], completed = batch_count)
        self.nr_registered_results += self.sweep_size

    def _mock_wait_until_result_buffer_full(
            self, progress_tracker: tuple, bar_title: str) -> None:
        """
        Mock implementation of wait_until_result_buffer_full for testing purposes

        Args:
            progress_tracker (tuple): Tuple containing the progress bar and the
                total number of results
            bar_title (str): Title for the progress bar
        """
        step_chunk = self.sweep_size // 10
        for i in range(10+1):
            progress_tracker[1].update(
                progress_tracker[0],
                completed = (i+1)*step_chunk,
                description = f"{bar_title}{i*step_chunk}/{self.sweep_size}"
            )
            progress_tracker[1].refresh()
            time.sleep(0.1)
