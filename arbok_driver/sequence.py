"""Module containing sequence class"""
import math
import logging
from collections import Counter

import numpy as np
from qm import qua
from qcodes.validators import Arrays, Numbers
import matplotlib.pyplot as plt
import time

from .gettable_parameter import GettableParameter
from .sequence_parameter import SequenceParameter
from .sample import Sample
from .sequence_base import SequenceBase
from .sweep import Sweep
from .qua_callback import QuaCallback

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
        self.pause_id = None

    def _init_vars(self) -> None:
        """
        Put variables into a reasonable init state
        """
        self.callback_list = []
        self._gettables = []
        self._sweep_size = 1
        self.shot_tracker_qua_var = None
        self.shot_tracker_qua_stream = None
        self._step_requirements = []
        self._input_stream_parameters = []

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

    def get_pause_id(self):
        """
        On pause get the pause id which will indicate the reason for pausing
        """
        if self.pause_id is None:
            self.pause_id = getattr(
                self.driver.qm_job.result_handles,
                f"{self.name}_pause_id"
            )
        while not self.driver.qm_job.is_paused():
            time.sleep(0.001)
        pid = self.pause_id.fetch_all()[0]
        return pid

    def add_callback(self, callback_instance, pause_id_qua_var, pause_id_qua_stream):
        """
        Add a class to the callback list and set its qua pause id

        Args :
            callback_instance A class instance which inherits from QuaCallback
        """
        if not issubclass(type(callback_instance), QuaCallback):
            raise TypeError(type(callback_instance), " should inherit QuaCallback")
        if callback_instance not in self.callback_list:
            self.callback_list.append(callback_instance)
            callback_instance.id = len(self.callback_list) - 1
            callback_instance.pause_id_qua_var = pause_id_qua_var
            callback_instance.pause_id_qua_stream = pause_id_qua_stream

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
        self.pause_id_qua_var = qua.declare(int, value = -2) # pause ID variable
        self.pause_id_qua_stream = qua.declare_stream()
        self.shot_tracker_qua_var = qua.declare(int, value = 0)
        self.shot_tracker_qua_stream = qua.declare_stream()
        self._qua_declare_input_streams()
        for cb in self.callback_list:
            cb.pause_id_qua_var = self.pause_id_qua_var
            cb.pause_id_qua_stream = self.pause_id_qua_stream

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

        if int_params:
            qua.advance_input_stream(self._qua_int_input_stream)
            for i, param in enumerate(int_params):
                qua.assign(param.qua_var, self._qua_int_input_stream[i])
        if bool_params:
            qua.advance_input_stream(self._qua_bool_input_stream)
            for i, param in enumerate(bool_params):
                qua.assign(param.qua_var, self._qua_bool_input_stream[i])
        if fixed_params:
            qua.advance_input_stream(self._qua_fixed_input_stream)
            for i, param in enumerate(fixed_params):
                qua.assign(param.qua_var, self._qua_fixed_input_stream[i])

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
        self.pause_id_qua_stream.buffer(1).save(self.name + "_pause_id")
        self.shot_tracker_qua_stream.buffer(1).save(self.name + "_shots")

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
                name = f"{self.name}_int_input_stream",
                data = int_vals
            )
        if bool_vals:
            self.driver.qm_job.insert_input_stream(
                name = f"{self.name}_bool_input_stream",
                data = bool_vals
            )
        if fixed_vals:
            self.driver.qm_job.insert_input_stream(
                name = f"{self.name}_fixed_input_stream",
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

    def plot_current_histograms(self, gettables: list = None, bins: int = 50):
        """
        Plots current histograms for all gettables

        Args:
            gettables (list, GettableParameter): Parameter or list of parameters
                to plot histograms for
            bins (int): Number of bins for histogram
        """
        gettable_list = []
        if gettables is None:
            gettable_list = self.gettables
        elif isinstance(gettables, GettableParameter):
            gettable_list = [gettables]
        else:
            raise ValueError(
                f"""gettables must be of type GettableParameter or list with
                Gettable parameters is: {type(gettables)}"""
                )
        fig, ax = plt.subplots(
            len(self.gettables),
            figsize = (5, 3*len(self.gettables))
            )

        ALPHA = 0.8
        for i, gettable in enumerate(gettable_list):
            current_gettable = getattr(
                gettable.instrument, f"{gettable.name}")
            current_vals = np.array(current_gettable.get_all(), dtype = float)
            ax[i].hist(
                current_vals,
                bins = bins,
                label = current_gettable.name,
                alpha = ALPHA,
                color = 'black'
                )
            ax[i].set_xlabel("SET read current histogram")
            ax[i].set_ylabel("counts")
            ax[i].grid()
            ax[i].legend()
        fig.tight_layout()
        return fig, ax
