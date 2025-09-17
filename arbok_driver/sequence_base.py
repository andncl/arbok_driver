""" Module containing BaseSequence class """
from __future__ import annotations
from typing import TYPE_CHECKING, Optional
import copy
import types
import warnings
import logging
from functools import reduce
from anytree import RenderTree
from qcodes.instrument import InstrumentModule

from qm import SimulationConfig, generate_qua_script, qua, QuantumMachinesManager
from qm.simulate.credentials import create_credentials

from .device import Device
from .sequence_parameter import SequenceParameter
from . import utils
if TYPE_CHECKING:
    from .measurement import Measurement
    from .sub_sequence import SubSequence

class SequenceBase(InstrumentModule):
    """
    Class describing a subsequence of a QUA programm (e.g Init, Control, Read). 
    """
    def __init__(
            self,
            parent,
            name: str,
            device: Device,
            sequence_config: Optional[dict | None] = None,
            check_step_requirements: Optional[bool] = False,
            **kwargs
            ):
        """
        Constructor class for `SequenceBase` class
        
        Args:
            name (str): Name of the program
            device (Device): Device class describing phyical device
            sequence_config (dict): Dictionary containing all device parameters
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(parent, name, **kwargs)
        self.parent.add_submodule(self.name, self)
        setattr(self.parent, self.short_name, self)

        self.device = device
        self.elements = self.device.elements
        self.sequence_config = sequence_config
        self.check_step_requirements = check_step_requirements

        self._sub_sequences = []
        self._sub_sequence_dict = {}
        self._gettables = []
        self._qua_program_as_str = None
        self._init(**kwargs)
        self.add_qc_params_from_config(self.sequence_config)

    def _init(self, **kwargs):
        """A method to do initialisation when the __init__ constructor isn't
            required.
           
            Args:
            **kwargs: Arbitrary keyword arguments.
           """
        pass

    @staticmethod
    def config_template():
        """
        The user can get an example config template.
        This feature is useful if building from scratch or for UI 
        prompting.
            
        Returns:
            A dictionary with an example config template. 
        """
        return {}

    def qua_declare(self):
        """Contains raw QUA code to initialize the qua variables"""
        for sub_sequence in self.sub_sequences:
            sub_sequence.qua_declare()

    def qua_before_sweep(self):
        """Contains raw QUA code that is being executed before sweeps"""
        for sub_sequence in self.sub_sequences:
            sub_sequence.qua_before_sweep()

    def qua_before_sequence(self):
        """Contains raw QUA code that is being executed before the sequence"""
        for sub_sequence in self.sub_sequences:
            sub_sequence.qua_before_sequence()

    def qua_sequence(self):
        """Contains raw QUA code to define the pulse sequence"""
        for sub_sequence in self.sub_sequences:
            sub_sequence.qua_sequence()

    def qua_after_sequence(self):
        """Contains raw QUA code that is being executed after the sequence"""
        for sub_sequence in self.sub_sequences:
            sub_sequence.qua_after_sequence()

    def qua_stream(self):
        """Contains raw QUA code to define streams"""
        for sub_sequence in self.sub_sequences:
            sub_sequence.qua_stream()

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
        # return 'hi'
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

    def get_qua_program_as_str(self) -> str:
        """Returns the qua program as str. Will be compiled if it wasnt yet"""
        if self._qua_program_as_str is None:
            self.get_qua_program()
        return self._qua_program_as_str

    def get_qua_program(self, simulate = False, config = None):
        """
        Composes the entire sequence by searching recursively through init, 
        sequence and stream methods of all subsequences and their subsequences.
        The respective qua sequence will only be added once the recursive
        scans have reached the lowest level of sequences (e.g sequences have no
        sub-sequences anymore)

        Args:
            simulate (bool): Flag whether program is simulated
        Returns:
            program: Program compiled into QUA language
        """
        with qua.program() as prog:
            self.get_qua_code(simulate)
        self._qua_program_as_str = generate_qua_script(prog, config)
        return prog

    def get_qua_code(self, simulate = False):
        """
        Composes the entire qua sequence in qua code. Only execurte with
        qm.qua.program() environment
        
        Args:
            simulate (bool): True if program is generated for simulation
        """
        if self.measurement is None:
            raise ReferenceError(
                "The sub sequence {self.name} is not linked to a sequence")
        self.qua_declare_sweep_vars()
        self.qua_declare()

        ### An infinite loop starting with a pause is defined to sync the QM
        ### with the client
        with qua.infinite_loop_():
            if not simulate:
                qua.pause()

            ### Check requirements are set to True if the sequence is simulated
            if simulate:
                for qua_var in self.measurement.step_requirements:
                    qua.assign(qua_var, True)
            ### The sequences are run in the order they were added
            ### Before_sweep methods are run before the sweep loop
            self.qua_before_sweep()
            # self.recursive_qua_generation(seq_type = 'before_sweep')

            ### qua_sequence methods of sub_sequences are called recursively
            ### If parent sequence is present the sweep generation is added
            if hasattr(self.measurement, 'sweeps'):
                self.recursive_sweep_generation(
                    self.measurement.sweeps)
            else:
                self.qua_sequence()

        ### Stream processing is added after the sequences
        with qua.stream_processing():
            self.qua_stream()

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

    def _add_param(self, param_name: str, param_dict: dict):
        """
        Adds parameter based on the given parameter configuration
        
        Args:
            param_name (str): Name of the parameter
            param_dict (dict): Must contain 'unit' key and optionally 'value'
                or 'elements' for element wise defined parameters
        """
        logging.debug("Adding %s to %s", param_name, self.name)
        param_dict = self._reshape_param_dict(param_name, param_dict)
        if 'elements' in param_dict:
            self._add_element_params(param_name, param_dict)
            return
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

            self._add_param(
                param_name = f'{param_name}_{element}',
                param_dict = param_dict_copy
                )

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
            raise KeyError(f"Config for parameter {param_name} contains"
                           "'elements' key. Error in preparation. Check" \
                           "`_add_element_params` method.")

    def run_remote_simulation(self, host, port, duration: int):
        """
        Simulates the MW sequence on a remote simulator on the host

        Args:
            host (str): Host address
            duration (int): Amount of cycles (4ns/cycle) to simulate

        Returns:
            SimulatedJob: QM job containing simulation results
        """
        qmm = QuantumMachinesManager(
            host = host,
            port = port,
            credentials=create_credentials()
        )
        simulated_job = qmm.simulate(
            self.device.config,
            self.get_qua_program(simulate = True),
            SimulationConfig(duration=duration)
            )

        devices = simulated_job.get_simulated_devices()
        utils.plot_qmm_simulation_results(devices)
        return simulated_job

    def find_parameters_from_keywords(
        self,
        keys: str | list,
        elements: list[str] = None
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
        sequence_config: dict = None,
        namespace_to_add_to: dict = None,
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
            device = self.device,
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
            namespace_to_add_to: dict = None) -> None:
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
        namespace_to_add_to: dict = None
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
                    "ignored. "
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

    def find_parameters(self, key: str, elements: list = None) -> dict:
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

    def find_parameter_from_str_path(self, path: str):
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

    def set_params_with_unit_to_value(self, unit: str, value: any):
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
