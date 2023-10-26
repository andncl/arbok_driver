""" Module containing BaseSequence class """

import copy
from typing import Optional
import logging

import numpy as np

from qcodes.instrument import InstrumentModule, Instrument
from qcodes.validators import Arrays

from qm import SimulationConfig, generate_qua_script
from qm.QuantumMachinesManager import QuantumMachinesManager
from qm.simulate.credentials import create_credentials
from qm.qua import (
    program, infinite_loop_, pause, stream_processing,
    declare, for_, assign, fixed
)

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
            param_config: Optional[dict | None] = None,
            **kwargs
            ):
        """
        Constructor class for `SequenceBase` class
        
        Args:
            name (str): Name of the program
            sample (Sample): Sample class describing phyical device
            param_config (dict): Dictionary containing all device parameters
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(name, **kwargs)
        self.sample = sample
        self.elements = self.sample.elements
        self.param_config = param_config

        self._parent_sequence = None
        self._gettables = []
        self._qua_program_as_str = None
        self.add_qc_params_from_config(self.param_config)

    def qua_declare(self):
        """Contains raw QUA code to initialize the qua variables"""
        return

    def qua_sequence(self):
        """Contains raw QUA code to define the pulse sequence"""
        return

    def qua_stream(self):
        """Contains raw QUA code to define streams"""
        return

    @property
    def gettables(self) -> list:
        """
        List of `GettableParameter`s that can be registered for acquisition
        in a `program`
        """
        return self._gettables

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
        self.add_submodule(new_sequence.name, new_sequence)

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
        with program() as prog:
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
        with infinite_loop_():
            if not simulate:
                pause()
            self.recursive_sweep_generation(
                copy.copy(self.parent_sequence.sweeps))
        with stream_processing():
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
                setpoints = np.array(setpoints)
                logging.debug(
                    "Adding qua %s variable for %s on subsequence %s",
                    type(param.get()), param.name, param.instrument.name
                )
                param.qua_sweeped = True
                param.vals= Arrays()
                param.set(np.array(setpoints))
                if param.var_type == float:
                    param.qua_var = declare(fixed)
                    param.qua_sweep_arr = declare(
                        fixed, value = setpoints*param.scale
                    )
                elif param.var_type == int:
                    param.qua_var = declare(int)
                    param.qua_sweep_arr = declare(
                        int, value = np.array(setpoints, dtype = int)
                    )
                else:
                    raise TypeError("Type not supported. Must be float or int")

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
            # this condition gets triggered if we arrive at the innermost loop
            self.recursive_qua_generation('sequence')
            return
        new_sweeps = sweeps[:-1]
        current_sweep = sweeps[-1]
        idx = declare(int)
        logging.debug( "Adding qua loop for %s",
            [par.name for par in current_sweep.parameters])
        with for_(idx, 0, idx < current_sweep.length, idx + 1):
            for param in current_sweep.parameters:
                assign(param.qua_var, param.qua_sweep_arr[idx])
            self.recursive_sweep_generation(new_sweeps)
        return

    def recursive_qua_generation(self, seq_type: str):
        """
        Recursively runs all QUA code stored in submodules of the given sequence
        Differentiates between 'declare', 'stream' and `sequence`.

        Args:
            seq_type (str): Type of qua code containing method to look for
        """
        if not self.submodules:
            getattr(self, 'qua_' + str(seq_type))()
            return
        for subsequence in self.submodules.values():
            if not subsequence.submodules:
                getattr(subsequence, 'qua_' + str(seq_type))()
            else:
                subsequence.recursive_qua_generation(seq_type)

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
            logging.debug("No params added to %s (no param_config)", self.name)
            return
        for param_name, param_dict in config.items():
            logging.debug("Adding %s to %s", param_name, self.name)
            if 'elements' in param_dict:
                for element, value in param_dict['elements'].items():
                    if element in self.sample.elements:
                        scale = self.sample.divider_config[element]['division']
                    else:
                        scale = 1
                    self.add_parameter(
                        name  = f'{param_name}_{element}',
                        config_name = param_name,
                        unit = param_dict["unit"],
                        initial_value = value,
                        parameter_class = SequenceParameter,
                        element = element,
                        get_cmd = None,
                        set_cmd = None,
                        scale = scale,
                        var_type = float
                    )
            elif 'value' in param_dict:
                self.add_parameter(
                    name  = param_name,
                    config_name = param_name,
                    unit = param_dict["unit"],
                    initial_value = param_dict["value"],
                    parameter_class = SequenceParameter,
                    element = None,
                    set_cmd = None,
                    var_type = int
                )
            else:
                raise KeyError(f"""The config of parameter {param_name} does not
                              have elements or value""")

    def run_remote_simulation(self, host, duration: int):
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
            port = 443,
            credentials=create_credentials()
        )
        simulated_job = qmm.simulate(
            self.sample.config,
            self.get_qua_program(simulate = True),
            SimulationConfig(duration=duration)
            )

        samples = simulated_job.get_simulated_samples()
        utils.plot_opx_simulation_results(samples)
        return simulated_job

    def find_parameters_from_keywords(self, keys: str | list):
        """
        Returns a list containing all parameters of the seqeunce with names that
        contain one of names in the 'keys' list.
        TODO:   - raise error if no params were found

        Args:
            keys (str, list): string with parameter name sub-string or list of those
        Returns:
            List of parameters containing substrings from keys in their name
        """
        if isinstance(keys, str):
            keys = [keys]
        elif not isinstance(keys, list):
            raise ValueError(
                f"key has to be of type list or str, is {type(keys)}")

        param_list = []
        for item in keys:
            param_list.append(
                [p for p_name, p in self.parameters.items() if item in p_name])
        return np.swapaxes(np.array(param_list), 0, 1).tolist()
