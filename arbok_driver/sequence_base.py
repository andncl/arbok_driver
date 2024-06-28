""" Module containing BaseSequence class """

import copy
from typing import Optional
import logging
import warnings

import numpy as np

from qcodes.instrument import Instrument
from qcodes.validators import Arrays, Numbers, Ints

from qm import SimulationConfig, generate_qua_script, qua
from qm.QuantumMachinesManager import QuantumMachinesManager
from qm.simulate.credentials import create_credentials

from .sample import Sample
from .sequence_parameter import SequenceParameter
from . import utils

class SequenceBase(Instrument):
    """
    Class describing a subsequence of a QUA programm (e.g Init, Control, Read). 
    """
    def __init__(
            self,
            name: str,
            sample: Sample,
            sequence_config: Optional[dict | None] = None,
            **kwargs
            ):
        """
        Constructor class for `SequenceBase` class
        
        Args:
            name (str): Name of the program
            sample (Sample): Sample class describing phyical device
            sequence_config (dict): Dictionary containing all device parameters
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(name, **kwargs)
        self.sample = sample
        self.elements = self.sample.elements
        self.sequence_config = sequence_config

        self._parent_sequence = None
        self._sub_sequences = []
        self._gettables = []
        self._qua_program_as_str = None
        self.add_qc_params_from_config(self.sequence_config)

    def qua_declare(self):
        """Contains raw QUA code to initialize the qua variables"""
        return

    def qua_before_sweep(self):
        """Contains raw QUA code that is being executed before sweeps"""
        return
    
    def qua_before_sequence(self):
        """Contains raw QUA code that is being executed before the sequence"""
        return

    def qua_sequence(self):
        """Contains raw QUA code to define the pulse sequence"""
        return

    def qua_after_sequence(self):
        """Contains raw QUA code that is being executed after the sequence"""
        return

    def qua_stream(self):
        """Contains raw QUA code to define streams"""
        return

    @property
    def sub_sequences(self) -> list:
        """
        List of `SubSequences`s that build the given sequence
        """
        return self._sub_sequences

    @property
    def gettables(self) -> list:
        """
        List of `GettableParameter`s that can be registered for acquisition
        in a `program`
        """
        return self._gettables

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
        if not isinstance(config, dict):
            raise ValueError(
                f"Conf for {self.name} must be of type dict, is {type(config)}")
        if 'parameters' in config:
            config = config['parameters']
            logging.info(
                "Set para subset of given conf file as param conf for in %s",
                self.name
                )
        for param_name, param_dict in config.items():
            self._add_param(param_name, param_name, param_dict)

    def get_qua_program_as_str(self) -> str:
        """Returns the qua program as str. Will be compiled if it wasnt yet"""
        if self._qua_program_as_str is None:
            self.get_qua_program()
        return self._qua_program_as_str

    def add_subsequence(self, new_sequence) -> None:
        """
        Adds a subsequence to the entire programm. Subsequences are added as 
        QCoDeS 'Submodules'. Sequences are executed in order of them being added.

        Args:
            new_sequence (Sequence): Subsequence to be added
            verbose (bool): Flag to trigger debug printouts
        """
        new_sequence.parent_sequence = self
        if new_sequence.name not in self.submodules.keys():
            self.add_submodule(new_sequence.name, new_sequence)
            self._sub_sequences.append(new_sequence)
        else:
            warnings.warn(
                f"{new_sequence.name} already in subsequences, sequence added again"
                )
            self._sub_sequences.append(new_sequence)

    def get_qua_program(self, simulate = False):
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
        self._qua_program_as_str = generate_qua_script(prog)
        return prog

    def get_qua_code(self, simulate = False):
        """
        Composes the entire qua sequence in qua code. Only execurte with
        qm.qua.program() environment
        
        Args:
            simulate (bool): True if program is generated for simulation
        """
        if self.parent_sequence is None:
            raise ReferenceError(
                "The sub sequence {self.name} is not linked to a sequence")
        self.qua_declare_sweep_vars()
        self.recursive_qua_generation(seq_type = 'declare')

        ### An infinite loop starting with a pause is defined to sync the QM
        ### with the client
        with qua.infinite_loop_():
            if not simulate:
                qua.pause()

            ### The sequences are run in the order they were added
            ### Before_sweep methods are run before the sweep loop
            self.recursive_qua_generation(seq_type = 'before_sweep')

            ### qua_sequence methods of sub_sequences are called recursively
            ### If parent sequence is present the sweep generation is added
            if hasattr(self.parent_sequence, 'sweeps'):
                self.recursive_sweep_generation(self.parent_sequence.sweeps)
            else:
                self.recursive_qua_generation(seq_type = 'sequence')

        ### Stream processing is added after the sequences
        with qua.stream_processing():
            self.recursive_qua_generation(seq_type = 'stream')

    def print_qua_program_to_file(self, file_name: str):
        """Creates file with 'filename' and prints the QUA code to this file"""
        with open(file_name, 'w', encoding="utf-8") as file:
            file.write(self.get_qua_program_as_str())

    def qua_declare_sweep_vars(self) -> None:
        """ Declares all sweep variables as QUA with their correct type """
        logging.debug("Start declaring QUA variables in %s", self.name)
        for sweep in self.parent_sequence.sweeps:
            for param, setpoints in sweep.config.items():
                if isinstance(param, SequenceParameter):
                    logging.debug("Declaring %s as %s",
                                    param.name, param.var_type)
                    param.qua_declare(setpoints)

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
            self.recursive_qua_generation('before_sequence')
            self.recursive_qua_generation('sequence')
            self.recursive_qua_generation('after_sequence')
            return
        new_sweeps = sweeps[:-1]
        current_sweep = sweeps[-1]
        # if self.parent_sequence is self and len(sweeps) == len(self.sweeps):
        #     self.qua_before_sweep()
        logging.debug("Adding qua loop for %s",
            [par.name for par in current_sweep.parameters])

        current_sweep.qua_generate_parameter_sweep(
            lambda: self.recursive_sweep_generation(new_sweeps)
            )
        return

    def recursive_qua_generation(self, seq_type: str):
        """
        Recursively runs all QUA code stored in submodules of the given sequence
        Differentiates between 'declare', 'stream' and `sequence`.

        Args:
            seq_type (str): Type of qua code containing method to look for
        """
        method_name = f"qua_{seq_type}"
        if hasattr(self, method_name):
            getattr(self, 'qua_' + str(seq_type))()

        ### The innermost sequence is reached. Run the sequence code
        if not self.submodules:
            logging.debug(
                "Reached low level seq running qua_%s code of %s",
                seq_type, self.name)
            getattr(self, method_name)()
            return

        ### If the given seqeunce has subsequences, run the recursion of those
        for subsequence in self._sub_sequences:
            if not subsequence.submodules:
                if hasattr(subsequence, method_name):
                    getattr(subsequence, method_name)()
            else:
                subsequence.recursive_qua_generation(seq_type)

    def reset(self) -> None:
        """
        On reset, ensure param validators are no longer sweep_validators
        """
        for k, param in self.parameters.items():
            if isinstance(param, SequenceParameter):
                self.parameters[k].reset()
        for sub in self.sub_sequences:
            sub.reset()

    def _add_param(self, param_name: str, cfg_name: str, param_dict):
        """
        Adds parameter based on the given parameter configuration
        
        Args:
            param_name (str): Name of the parameter
            param_dict (dict): Must contain 'unit' key and optionally 'value'
                or 'elements' for element wise defined parameters
        """
        logging.debug("Adding %s to %s", param_name, self.name)
        if 'elements' in param_dict:
            for element, value in param_dict['elements'].items():
                scale = 1
                if element in self.sample.divider_config:
                    scale = self.sample.divider_config[element]['division']
                    param_dict['validator'] = Numbers(-1/scale, 1/scale)
                new_param_dict = {'value' : value, 'scale' : scale, 'label' : f"{element}: {param_dict['label']}", 'type' : param_dict['type']}
                self._add_param(f'{param_name}_{element}', cfg_name, new_param_dict)
        elif 'value' in param_dict:
            # set defaults and merge in changes
            appl_dict = {'element' : None, 'scale' : 1, 'validator' : param_dict['type'].validator, 'qua_type' : param_dict['type'].qua_type,
                            'unit' : param_dict['type'].unit, 'label' : param_dict['type'].label}
            appl_dict.update(param_dict)
            self.add_parameter(
                name  = param_name,
                config_name = cfg_name,
                unit = appl_dict["unit"],
                initial_value = appl_dict["value"],
                parameter_class = appl_dict["type"],
                element = appl_dict['element'],
                get_cmd = None,
                set_cmd = None,
                scale = appl_dict['scale'],
                vals = appl_dict['validator'],
                var_type = appl_dict['qua_type'],
                label = appl_dict['label']
            )
        else:
            raise KeyError(
                f"The config of parameter {param_name} does not have "
                    "elements or value"
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
        qmm = QuantumMachinesManager(
            host = host,
            port = port,
            credentials=create_credentials()
        )
        simulated_job = qmm.simulate(
            self.sample.config,
            self.get_qua_program(simulate = True),
            SimulationConfig(duration=duration)
            )

        samples = simulated_job.get_simulated_samples()
        utils.plot_qmm_simulation_results(samples)
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
            elements = list(self.sample.elements)
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
            elements = self.sample.elements
        for element in elements:
            if hasattr(self, f"{key}_{element}"):
                parameters[element] = getattr(self, f"{key}_{element}")
        return parameters

    def find_parameter(self, key: str, element: str):
        """Returns parameter with a certain key for a given element"""
        parameter = getattr(self, f"{key}_{element}")
        return parameter

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
                logging.debug("Setting param %s to %s", param_name, value)
                param(value)