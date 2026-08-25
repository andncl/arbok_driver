""" Module containing BaseSequence class """
from __future__ import annotations
from abc import ABC
from typing import TYPE_CHECKING, Optional
import copy
import types
import warnings
import logging
from functools import reduce
from anytree import RenderTree
from qcodes.instrument import InstrumentModule

from .parameters.sequence_parameter import SequenceParameter
from .parameter_class import ParameterClass, EmptyParameterClass
from .parameter_types import ParameterMap
from . import utils

if TYPE_CHECKING:
    from .backend import Backend
    from .device import Device
    from .sub_sequence import SubSequence

class SequenceBase(InstrumentModule, ABC):
    """
    Class describing a subsequence of a QUA programm (e.g Init, Control, Read). 
    """
    PARAMETER_CLASS: type[ParameterClass]
    _enforce_parameter_class: bool = False
    def __init__(
            self,
            parent,
            name: str,
            sequence_config: Optional[dict | None] = None,
            check_step_requirements: Optional[bool] = False,
            **kwargs
            ):
        """
        Constructor class for `SequenceBase` class
        
        Args:
            name (str): Name of the program
            sequence_config (dict): Dictionary containing all device parameters
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(parent, name, **kwargs)
        self.parent.add_submodule(self.name, self)
        setattr(self.parent, self.short_name, self)

        self.device: Device = self.parent.device
        self.elements = self.device.elements
        self.sequence_config = sequence_config
        self.check_step_requirements = check_step_requirements

        self._sub_sequences = []
        self._sub_sequence_dict = {}
        self._gettables = []
        self._parameter_maps: dict = {}
        self._qua_program_as_str = None
        self.add_qc_params_from_config(self.sequence_config)
        self._hardware_config: dict = {}

    def __init_subclass__(cls, **kwargs) -> None:
        """Enforces child classes to define PARAMETER_CLASS class attribute"""
        super().__init_subclass__(**kwargs)
        if cls._enforce_parameter_class:
            if 'PARAMETER_CLASS' not in cls.__dict__:
                cls.PARAMETER_CLASS = EmptyParameterClass
        cls._enforce_parameter_class = True

    @classmethod
    def config_template(cls)  -> dict | None:
        """
        The user can get an example config template.
        This feature is useful if building from scratch or for UI 
        prompting.
            
        Returns:
            A dictionary with an example config template. 
        """
        return {}

    @property
    def backend(self) -> Backend:
        """The active hardware backend, resolved from the driver."""
        from .arbok_driver import ArbokDriver
        if isinstance(self.parent, ArbokDriver):
            return self.parent.backend
        return self.parent.backend

    @property
    def hardware_config(self) -> dict:
        """
        Hardware configuration used to compile the program. Some operations in
        arbok automatically introduce new pulses and waveforms. Therefore the
        config you set on the device can be extended at compile time.
        """
        return self._hardware_config

    @property
    def opx_config(self) -> dict:
        """Backwards-compatible alias for hardware_config."""
        return self._hardware_config

    def qua_before_sweep(self) -> None:
        """Contains code that is being executed before sweeps."""
        for sub_sequence in self.sub_sequences:
            sub_sequence.qua_before_sweep()

    def qua_sequence(self) -> None:
        """Dispatches sequence hook to all child sub_sequences."""
        for sub_sequence in self.sub_sequences:
            sub_sequence._dispatch('sequence')

    # ──────────────────────────────────────────────────────────────────────
    # Backend-keyed dispatch
    # ──────────────────────────────────────────────────────────────────────

    def _dispatch(self, hook: str) -> None:
        """Dispatch a lifecycle hook to the best matching method.

        Resolution order (first match wins):
        1. fpga_{hook}__{backend.name}  — backend-specific override
        2. fpga_{hook}                  — user override (not the default)
        3. qua_{hook}                   — legacy (QuaBackend only)
        4. fpga_{hook} default          — iterates child sub_sequences
        """
        from .sub_sequence import SubSequence

        backend_name = self.backend.name
        backend_method_name = f'fpga_{hook}__{backend_name}'
        fpga_method_name = f'fpga_{hook}'
        qua_method_name = f'qua_{hook}'

        # 1. Backend-specific override (e.g. fpga_sequence__qua)
        if hasattr(type(self), backend_method_name):
            method = getattr(self, backend_method_name)
            self._call_hook(method, hook)
            return

        # 2. User override of fpga_ method
        fpga_on_class = getattr(type(self), fpga_method_name, None)
        fpga_default = getattr(SubSequence, fpga_method_name, None)
        has_fpga_override = (
            fpga_on_class is not None and fpga_on_class is not fpga_default
        )

        if has_fpga_override:
            method = getattr(self, fpga_method_name)
            self._call_hook(method, hook)
            return

        # 3. Legacy qua_ override (deprecated, QuaBackend only)
        qua_on_class = getattr(type(self), qua_method_name, None)
        qua_default = getattr(SubSequence, qua_method_name, None)
        has_qua_override = (
            qua_on_class is not None and qua_on_class is not qua_default
        )

        if has_qua_override:
            from .backends.qua_backend import QuaBackend
            if not isinstance(self.backend, QuaBackend):
                raise NotImplementedError(
                    f"'{self.name}' only defines qua_{hook}() "
                    f"which is not compatible with "
                    f"{type(self.backend).__name__}. "
                    f"Implement fpga_{hook}() or "
                    f"fpga_{hook}__{backend_name}() for this backend."
                )
            method = getattr(self, qua_method_name)
            self._call_hook(method, hook)
            return

        # 4. Default fpga_ (iterates children)
        method = getattr(self, fpga_method_name)
        self._call_hook(method, hook)

    def _call_hook(self, method, hook: str) -> None:
        """Call a hook method, wrapping with step_requirements if needed."""
        if self.check_step_requirements and hook == 'sequence':
            self.measurement.qua_check_step_requirements(method)
        else:
            method()

    @property
    def sub_sequences(self) -> list[SubSequence]:
        """
        List of `SubSequences`s that build the given sequence
        """
        return self._sub_sequences

    @property
    def sub_sequence_dict(self) -> dict:
        """
        List of `SubSequences`s that build the given sequence
        """
        structure_dict = {}
        for sub_sequence in self._sub_sequences:
            if len(sub_sequence.sub_sequences) > 0:
                sub_dict = sub_sequence.sub_sequence_dict
                structure_dict[sub_sequence.short_name] = sub_dict
            else:
                structure_dict[sub_sequence.short_name] = {}
        return structure_dict # {self.short_name: structure_dict}

    @property
    def gettables(self) -> list:
        """
        List of `GettableParameter`s that can be registered for acquisition
        in a `program`
        """
        return self._gettables

    def add_subsequence(self, new_sequence) -> None:
        """Adds a subsequence to self"""
        self._sub_sequences.append(new_sequence)

    def get_parameters_and_maps(
            self, param_names: list[str]
            ) -> dict[str, SequenceParameter | ParameterMap]:
        param_dict = {}
        for param_name in param_names:
            if param_name in self.parameters:
                param_dict[param_name] = self.parameters[param_name]
            elif param_name in self._parameter_maps:
                param_dict[param_name] = self._parameter_maps[param_name]
        return param_dict

    def add_qc_params_from_config(self, config):
        """ 
        Creates QCoDeS parameters for all entries of the config 
        TODO: Use custom Parameter types for times -> setting in ns ! (cycles)
                use validator to check if ns are a multiple of 4 (1 cycle)
        TODO: if voltage add scale = 0.5 and validate if |v| <= 0.5

        Args:
            config (dict): Configuration containing all sequence parameters
        """
        if config is None:
            logging.info("No params added to %s (no sequence_config)", self.name)
            return
        elif not isinstance(config, dict):
            raise ValueError(
                f"Conf for {self.name} must be of type dict, is {type(config)}")
        if 'parameters' in config:
            config = config['parameters']
            logging.info(
                "Set param subset of given conf file as param conf for in %s",
                self.name
                )
        for param_name, param_dict in config.items():
            self._add_param(param_name, param_dict)

    def draw_sub_sequence_tree(self) -> None:
        """
        Draws a tree of the subsequences of the sequence with their names and
        types
        """
        root_node = utils.dict_to_anytree(self.short_name, self.sub_sequence_dict)
        for pre, _, node in RenderTree(root_node):
            print(f"{pre}{node.name}")

    def get_program_as_str(self, recompile: bool = False) -> str:
        """Returns the compiled program as a string."""
        if self._qua_program_as_str is None or recompile:
            self.compile_program()
        return self._qua_program_as_str

    def get_qua_program_as_str(self, recompile: bool = False) -> str:
        """Deprecated alias for get_program_as_str()."""
        return self.get_program_as_str(recompile)

    def compile_program(self, simulate=False, config=None):
        """
        Compiles the FPGA program by recursively composing all subsequence
        hooks (declare, before_sequence, sequence, after_sequence, stream).

        Uses the active backend's program_context() to create the program
        handle and generate_program_script() for the string representation.

        Args:
            simulate (bool): Flag whether program is compiled for simulation
            config: Optional override config

        Returns:
            program: Compiled program handle (backend-specific)
        """
        from .arbok.context import set_active_backend
        self._hardware_config = copy.deepcopy(self.measurement.device.config)
        self.measurement._hardware_config = self._hardware_config
        backend = self.backend
        set_active_backend(backend)
        try:
            with backend.program_context() as prog:
                self.compile_fpga_code(simulate)
            self._qua_program_as_str = backend.generate_program_script(
                prog, self._hardware_config)
        finally:
            set_active_backend(None)
        return prog

    def get_qua_program(self, simulate=False, config=None):
        """Backwards-compatible alias for compile_program()."""
        return self.compile_program(simulate=simulate, config=config)

    def compile_fpga_code(self, simulate=False) -> None:
        """
        Composes the full FPGA sequence code within the active backend's
        program context. Calls lifecycle hooks recursively through the
        sequence tree.

        Args:
            simulate (bool): True if program is generated for simulation
        """
        if not hasattr(self, "measurement"):
            raise ReferenceError(
                "The sub sequence {self.name} is not linked to a measurement")
        backend = self.backend
        self.qua_declare_sweep_vars()
        self.qua_declare()

        with backend.infinite_loop():
            if not simulate:
                backend.pause()

            if simulate:
                for hw_var in self.measurement.step_requirements:
                    backend.assign(hw_var, True)

            self.qua_before_sweep()

            if hasattr(self.measurement, 'sweeps'):
                self.recursive_sweep_generation(
                    self.measurement.sweeps)
            else:
                self.qua_sequence()

        with backend.stream_processing():
            self.qua_stream()

    def get_qua_code(self, simulate=False) -> None:
        """Backwards-compatible alias for compile_fpga_code()."""
        self.compile_fpga_code(simulate)

    def simulate(
            self,
            duration_ns: int = 10000,
            program_save_path: str | None = None,
            **kwargs
            ):
        """
        Compiles and simulates the program for this sequence using the
        active backend's simulate() method.

        Args:
            duration_ns (int): Simulation duration in nanoseconds
            program_save_path (str | None): Optional path to save the
                compiled program script
            **kwargs: Backend-specific simulation options

        Returns:
            Backend-specific simulation result
        """
        backend = self.backend
        program = self.compile_program(simulate=True)
        if program_save_path is not None:
            self.print_qua_program_to_file(file_name=program_save_path)

        # Pass qmm for QuaBackend if available
        from .backends.qua_backend import QuaBackend
        if isinstance(backend, QuaBackend):
            qmm = self.measurement.driver.qmm
            if not qmm:
                raise ConnectionError(
                    "No QMM found! Connect an OPX via `connect_opx`")
            kwargs.setdefault("qmm", qmm)

        return backend.simulate(
            program, self._hardware_config, duration_ns=duration_ns, **kwargs
        )

    def simulate_waveforms(self) -> dict:
        """Simulate the sequence and return per-element voltage time-traces.

        Temporarily swaps the backend to SimBackend, compiles and runs the
        sequence, then restores the original backend. Works regardless of
        which backend is currently active.

        Returns:
            Dict mapping element names to numpy arrays of voltage samples
            at 1 GS/s (1 sample per nanosecond).
        """
        import numpy as np
        from .backends.sim_backend import SimBackend
        from .arbok.context import set_active_backend

        sim = SimBackend()
        driver = self.measurement.driver
        original_backend = driver.backend
        driver.backend = sim
        try:
            set_active_backend(sim)
            with sim.program_context():
                self.compile_fpga_code(simulate=True)
        finally:
            driver.backend = original_backend
            set_active_backend(None)

        all_elements = self._get_simulation_elements()
        waveforms = sim.get_waveforms()

        max_len = max((len(w) for w in waveforms.values()), default=0)
        result = {}
        for element in all_elements:
            if element in waveforms:
                arr = waveforms[element]
                if len(arr) < max_len:
                    arr = np.pad(arr, (0, max_len - len(arr)),
                                 constant_values=arr[-1] if len(arr) > 0 else 0.0)
                result[element] = arr
            else:
                result[element] = np.zeros(max_len)
        return result

    def _get_simulation_elements(self) -> list[str]:
        """Returns element list for simulation output.

        Uses this sequence's all_elements parameter if it exists,
        otherwise falls back to the measurement's all_elements.
        """
        if hasattr(self, 'all_elements') and callable(self.all_elements):
            return list(self.all_elements())
        if hasattr(self, 'measurement') and hasattr(self.measurement, 'all_elements'):
            return list(self.measurement.all_elements())
        return list(self.device.elements)

    def print_qua_program_to_file(self, file_name: str):
        """Creates file with 'filename' and prints the QUA code to this file"""
        with open(file_name, 'w', encoding="utf-8") as file:
            file.write(self.get_qua_program_as_str())

    def qua_declare_sweep_vars(self) -> None:
        """ Declares all sweep variables as QUA with their correct type """
        logging.debug("Start declaring QUA variables in %s", self.name)
        for sweep in self.measurement.sweeps:
            for param, setpoints in sweep.config.items():
                if isinstance(param, SequenceParameter):
                    logging.debug("Declaring %s as %s",
                                    param.name, param.var_type)
                    param.qua_declare(setpoints)
                else:
                    raise TypeError(
                        f"Parameter {param} is not of type SequenceParameter"
                    )
            if sweep.snake_scan:
                sweep.declare_snake_variable()

    def recursive_sweep_generation(self, sweeps):
        """
        Recursively generates QUA parameter sweeps by introducing one nested QUA
        loop per swept axis. The last given sweep and its corresponding
        setpoints are in the innermost loop.
        TODO: Reimplement a fast version of this for non-paired parameter 
            sweeps
        Args:
            sweeps (list): list of Sweep objects
        """
        if len(sweeps) == 0:
            ### this condition gets triggered if we arrive at the innermost loop
            self.qua_before_sequence()
            self.qua_sequence()
            self.qua_after_sequence()
            return
        new_sweeps = sweeps[1:]
        current_sweep = sweeps[0]
        logging.debug("Adding qua loop for %s",
            [par.name for par in current_sweep.parameters])

        # In some cases, the current sweep needs knowledge of the next sweep,
        # for example the snake variable needs to be reset each outer loop.
        next_sweep = None
        if len(new_sweeps):
            next_sweep = new_sweeps[0]
        current_sweep.qua_generate_parameter_sweep(
            lambda: self.recursive_sweep_generation(new_sweeps),
            next_sweep
            )
        return

    def reset(self) -> None:
        """
        On reset, ensure param validators are no longer sweep_validators
        """
        for k, param in self.parameters.items():
            if isinstance(param, SequenceParameter):
                self.parameters[k].reset()
        for sub in self.sub_sequences:
            sub.reset()

    def remove_subsequences(self) -> None:
        """Removes all subsequences from the sequence"""
        while len(self.sub_sequences) > 0:
            sub = self._sub_sequences.pop()
            sub.remove_subsequences()
            delattr(self, sub.short_name)
            if sub.short_name in globals():
                del globals()[sub.short_name]
        self._sub_sequences = []

    def _add_param(self, param_name: str, param_dict: dict) -> SequenceParameter | None:
        """
        Adds parameter based on the given parameter configuration
        
        Args:
            param_name (str): Name of the parameter
            param_dict (dict): Must contain 'unit' key and optionally 'value'
                or 'elements' for element wise defined parameters

        Returns:
            SequenceParameter: just created parameter
        """
        logging.debug("Adding %s to %s", param_name, self.name)
        param_dict = self._reshape_param_dict(param_name, param_dict)
        if 'elements' in param_dict:
            self._add_element_params(param_name, param_dict)
            return None
        self._check_param_dict(param_name, param_dict)
        # If the parameter already exists on another sub-sequence or measurement
        # we add the sequence name to the parameter name to avoid conflicts
        # To reference the parameter later, we also add the short name of the
        # sequence to the parameter name
        attr_exists_already = hasattr(self, param_name)
        if attr_exists_already:
            short_param_name = param_name
            param_name = f"{self.short_name}__{param_name}"
        new_param = self.add_parameter(
            name  = param_name,
            get_cmd = None,
            set_cmd = None,
            register_name = f"{self.short_name}__{param_name}",
            **param_dict
        )
        if attr_exists_already:
            setattr(self, short_param_name, new_param)
        return new_param

    def _reshape_param_dict(
            self, param_name: str, param_dict: dict
            ) -> dict:
        """
        Reshapes the parameter dict to fit the requirements of the respective
        'SequenceParameter' constructor and checks if the parameter dict is ok.

        Args:
            param_name (str): Name of the parameter
            param_dict (dict): Dictionary containing the parameter configuration
                to be reshaped

        Returns:
            dict: Reshaped parameter dict
        """
        if 'type' not in param_dict and 'parameter_class' not in param_dict:
            raise KeyError(
                f"Config for parameter '{param_name}' on '{self.full_name}'"
                " does not contain a 'type' key."
                " Please provide a type of the parameter to be added."
                " Find available ones in arbok_driver/parameter_types.py."
                " Or use a custom one.")
        if 'type' in param_dict:
            param_dict['parameter_class'] = param_dict['type']
            del param_dict['type']
        if 'value' in param_dict:
            param_dict['initial_value'] = param_dict['value']
            del param_dict['value']
        if 'label' not in param_dict:
            param_dict['label'] = param_name
        for key in ['unit', 'var_type', 'vals', 'scale']:
            if key not in param_dict:
                param_dict[key] = getattr(
                    param_dict['parameter_class'], key, None)
        return param_dict

    def _add_element_params(self, param_name: str, param_dict: dict):
        """
        Adds element wise parameter based on the given parameter configuration
        
        Args:
            param_name (str): Name of the parameter
            param_dict (dict): Must contain 'elements' key and optionally 'value'
                or 'elements' for element wise defined parameters
        """
        element_mapping = {}
        for element, value in param_dict['elements'].items():
            element_param_dict = {
                'element' : element,
                'value' : value,
                'label' : f"{element}: {param_dict['label']}",
                }
            if element in self.device.divider_config:
                scale = self.device.divider_config[element]['division']
                element_param_dict['scale'] = scale

            param_dict_copy = copy.deepcopy(param_dict)
            del param_dict_copy['label']
            param_dict_copy.update(element_param_dict)
            del param_dict_copy['elements']

            element_mapping[element] = self._add_param(
                param_name = f'{param_name}_{element}',
                param_dict = param_dict_copy
                )
        self._parameter_maps[param_name] = ParameterMap(element_mapping)

    def _check_param_dict(self, param_name: str, param_dict: dict) -> None:
        """
        Checks if the given parameter dict is valid. Raises an error if not.
        
        Args:
            param_dict (dict): Dictionary containing the parameter configuration
        """
        if 'parameter_class' not in param_dict:
            raise ValueError(
                f"Parameter {param_name} does not contain a 'parameter_class'")
        if 'label' not in param_dict:
            raise ValueError(
                f"Parameter {param_name} does not contain a 'label' key")
        if 'initial_value' not in param_dict and 'elements' not in param_dict:
            raise ValueError(
                f"Parameter {param_name} does not contain an 'value'"
                " key")
        if 'elements' in param_dict:
            raise KeyError(
                f"Config for parameter {param_name} contains"
                "'elements' key. Error in preparation. Check" \
                "`_add_element_params` method."
                )

    def run_remote_simulation(self, host, port, duration: int):
        """
        Simulates the MW sequence on a remote simulator on the host

        Args:
            host (str): Host address
            duration (int): Amount of cycles (4ns/cycle) to simulate

        Returns:
            SimulatedJob: QM job containing simulation results
        """
        from qm import SimulationConfig, QuantumMachinesManager
        from qm.simulate.credentials import create_credentials
        qmm = QuantumMachinesManager(
            host=host,
            port=port,
            credentials=create_credentials()
        )
        simulated_job = qmm.simulate(
            self.opx_config,
            self.compile_program(simulate=True),
            SimulationConfig(duration=duration)
        )

        devices = simulated_job.get_simulated_devices()
        utils.plot_qmm_simulation_results(devices)
        return simulated_job

    def find_parameters_from_keywords(
        self,
        keys: str | list,
        elements: list[str] | None = None
        ) -> dict:
        """
        Returns a list containing all parameters of the seqeunce with names that
        contain one of names in the 'keys' list.
        TODO:   - raise error if no params were found

        Args:
            keys (str | list): string with parameter name sub-string or list of
                those
            elements (list)
        Returns:
            Dict of parameters containing substrings from keys in their name
                with element as key
        """
        if elements is None:
            elements = list(self.device.elements)
        if isinstance(keys, str):
            keys = [keys]
        elif not isinstance(keys, list):
            raise ValueError(
                f"key has to be of type list or str, is {type(keys)}")
        element_dict = {element: {} for element in elements}
        for element in elements:
            for key in keys:
                param = getattr(self, f"{key}_{element}")
                element_dict[element][key] = param
        return element_dict

    def _add_subsequence(
        self,
        name: str,
        sequence_config: dict,
        namespace_to_add_to: dict | None= None,
        **kwargs
        ) -> SubSequence:
        """
        Adds a subsequence to the sequence
        
        Args:
            name (str): Name of the subsequence
            sequence_config (dict): Config containing all measurement params
            namespace_to_add_to (dict): Name space to insert the
                subsequence into (e.g locals(), globals()) defaults to None
        """
        if 'sequence' not in sequence_config:
            raise KeyError(
                f"The given config for {self.full_name}__{name} does not contain a "
                "'sequence' key with a subsequence type to configure for."
                )
        subsequence = sequence_config['sequence']
        if not issubclass(subsequence, SequenceBase):
            raise TypeError(
                "Subsequence must be of type SubSequence")
        seq_instance = subsequence(
            parent = self,
            name = name,
            sequence_config = sequence_config,
            **kwargs
            )
        setattr(self, name, seq_instance)
        if namespace_to_add_to is not None:
            name_space = namespace_to_add_to
            name_space[name] = seq_instance
        return seq_instance

    def _add_subsequences_from_dict(
            self,
            default_sequence,
            subsequence_dict: dict,
            namespace_to_add_to: dict | None = None) -> None:
        """
        Adds subsequences to the sequence from a given dictionary

        Args:
            default_sequence (SubSequence): Default subsequence to be used if
                no sequence is given in the subsequence_dict. Since is meant to
                be SubSequence which is a child of SequenceBase, therefore it
                cant be directly referenced here but is given from the
                respective child
            subsequence_dict (dict): Dictionary containing the subsequences
            namespace_to_add_to (dict): Name space to insert the
                subsequence into (e.g locals(), globals()) defaults to None
                    """
        if type(self) is SequenceBase:
            raise TypeError(
                "Method is meant to be used in SubSequence or Measurement!")
        if isinstance(subsequence_dict, types.SimpleNamespace):
            subsequence_dict = vars(subsequence_dict)
        for name, seq_conf  in subsequence_dict.items():
            ### Check whether a subsequence is configured or empty
            if seq_conf is None:
                raise ValueError(
                    f"Conf for {name} is None, please provide dict. E.g: "
                    r"{'sequence': SubSequence, 'config': {}}"
                    )
            if 'sub_sequences' in seq_conf:
                ### If empty SubSequence, create one deeper nesting layer
                if any(k in seq_conf.keys() for k in ['sequence', 'config']):
                    raise KeyError(
                        f"Subsequence {name} contains 'sub_sequences' key but "
                        "also 'sequence' or 'config' keys. If you give "
                        f"sub_sequences, {name} has to be empty."
                    )
                sequence_config = {
                    'sequence': default_sequence,
                    'parameters': {},
                    }
                kwargs = seq_conf.get('kwargs', {})
                seq_instance = self._add_subsequence(
                    name = name,
                    sequence_config = sequence_config,
                    namespace_to_add_to = namespace_to_add_to,
                    **kwargs
                    )
                seq_instance.add_subsequences_from_dict(
                    seq_conf["sub_sequences"], namespace_to_add_to)
            elif any(k in seq_conf.keys() for k in ['sequence', 'config']):
                self._prepare_adding_subsequence(
                    name, seq_conf, namespace_to_add_to)
            elif not seq_conf:
                pass
            else:
                raise KeyError(
                    f"Someting is wrong with the conf for {name}. "
                    f"Check the config {seq_conf}."
                    )

    def _prepare_adding_subsequence(
        self,
        name: str,
        seq_conf: dict,
        namespace_to_add_to: dict | None = None
        ) -> None:
        ### Check if config available and of type dict
        sub_seq_conf = {'parameters': {}}
        if 'config' in seq_conf:
            if not isinstance(sub_seq_conf, dict):
                raise ValueError(
                    f"Subsequence config ({name}) must be of type dict,"
                    f" is {type(sub_seq_conf)}")
            if 'parameters' not in seq_conf['config']:
                raise KeyError(
                    f"Config for {self.full_name}__{name} does not contain "
                    "'parameters' key."
                )
            if 'sequence' not in seq_conf['config']:
                raise ValueError(
                    f"Config for {self.full_name}__{name} does not specify "
                    "the SubSequence it configures. E.g 'sequence key is missing'"
                )
            sub_seq_conf = seq_conf['config']
        ### Check if kwargs available and of type dict
        if 'kwargs' in seq_conf:
            kwargs = seq_conf['kwargs']
            if not isinstance(kwargs, dict):
                raise ValueError(
                    f"Kwargs must be of type dict, is {type(kwargs)}")
        else:
            kwargs = {}
        ### Check if sequence is available and of type SequenceBase
        if 'sequence' in seq_conf:
            if 'sequence' in sub_seq_conf:
                warnings.warn(
                    "If both 'config' and 'sequence' are given, 'sequence' "
                    "will be used and the seq given in 'config' will be "
                    f"ignored. Sequence {name}: " 
                    f"{sub_seq_conf['sequence'].__name__} -> "
                    f"{seq_conf['sequence'].__name__}",
                )
            sub_seq_conf['sequence'] = seq_conf['sequence']
        _ = self._add_subsequence(
            name = name,
            sequence_config = sub_seq_conf,
            namespace_to_add_to = namespace_to_add_to,
            **kwargs
            )

    def find_parameters(self, key: str, elements: list | None = None) -> dict:
        """
        Finds all parameters generated from elements and a the given key.
        Similar to `find_parameters_from_keywords` but returns a non nested
        dict with elements as keys and SequenceParameters as key. This function
        gets its elements straigt from the given quantum machines config,
        therefore only params with elements that are known to the hardware are
        returned.

        Args:
            key (str): Name of the searched parameters
            elements (list): List of elements to be searched for

        Returns:
            dict: Dict with all found SequenceParameters and elements as keys
        """
        parameters = {}
        if elements is None:
            elements = self.device.elements
        for element in elements:
            if hasattr(self, f"{key}_{element}"):
                parameters[element] = getattr(self, f"{key}_{element}")
        return parameters

    def find_parameter(self, key: str, element: str):
        """Returns parameter with a certain key for a given element"""
        parameter = getattr(self, f"{key}_{element}")
        return parameter
                                                                                                                            
    def get_attribute_by_path(self, path):                                                                                                               
        """Access a nested attribute using a dot-separated string.
        Args:
            path: a dot delimited path to get the variable from.
        Returns:
            The variable matching the string path
        """                                                                                   
        return reduce(getattr, path.split('.'), self)     

    def find_parameter_from_str_path(
            self, path: str | list[str]) -> SequenceParameter:
        """
        Returns the parameter from the given path

        Args:
            path (str): Path to the parameter

        Returns:
            SequenceParameter: Parameter at the given path
        """
        if isinstance(path, str):
            path = path.split('__')
        if not isinstance(path, list):
            raise ValueError(
                f"path has to be of type list or str, is {type(path)}")
        if len(path) == 1:
            return getattr(self, path[0])
        else:
            return getattr(self, path[0]).find_parameter_from_str_path(path[1:])

    def ask_raw(self, *args):
        """Overwrites abstract method"""
        raise NotImplementedError("This driver does not support `ask_raw`")

    def set_raw(self, *args):
        """Overwrites abstract method"""
        raise NotImplementedError("This driver does not support `set_raw`")

    def set_params_with_unit_to_value(self, unit: str, value: any) -> None:
        """
        Sets all parameters with the given unit to the given value

        Args:
            unit (str): Unit of the parameters to be set
            value (any): Value to be set
        """
        for param_name, param in self.parameters.items():
            if param.unit == unit:
                print(f"Setting param {param_name} to {value}")
                logging.debug("Setting param %s to %s", param_name, value)
                param(value)
