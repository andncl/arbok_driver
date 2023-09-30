""" Module containing Sequence class """

import warnings
import copy
from typing import List, Union, Optional
import logging
import math

import matplotlib.pyplot as plt
import numpy as np

from qcodes.instrument import Instrument, InstrumentBase
from qcodes.validators import Arrays

from qm import SimulationConfig
from qm.QuantumMachinesManager import QuantumMachinesManager
from qm.simulate.credentials import create_credentials
from qm.qua import (
    program, infinite_loop_, pause, stream_processing, 
    declare, for_, assign, play, amp, fixed
)

from qualang_tools.loops import from_array

from .gettable_parameter import GettableParameter
from .sample import Sample 
from .sequence_parameter import SequenceParameter
from .sweep import Sweep
from . import utils

class SubSequence(Instrument):
    """
    Class describing a subsequence of a QUA programm (e.g Init, Control, Read). 
    """
    def __init__(self, name: str, sample: Sample,
                 param_config: Union[dict, None] = None, **kwargs):
        """
        Constructor class for `Program` class
        
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

        self._parent = None
        self._sweeps = []
        self._gettables = []
        self._sweep_size = 1

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
    def parent(self) -> InstrumentBase:
        return self._parent

    @property
    def root_instrument(self) -> InstrumentBase:
        if self._parent is None:
            return self
        return self._parent.root_instrument

    @property
    def sweeps(self) -> list:
        """ List of Sweep objects for `SubSequence` """
        return self._sweeps
    
    @property
    def gettables(self) -> list:
        """List of `GettableParameter`s for data acquisition"""
        return self._gettables

    @property
    def sweep_size(self) -> int:
        """ Dimensionality of sweep axes """
        self._sweep_size = int(
            math.prod([sweep.length for sweep in self.sweeps]))
        return self._sweep_size
    
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
        if not all([isinstance(sweep_dict, dict) for sweep_dict in args]):
            raise TypeError("All arguments need to be of type dict")
        self._sweeps = []
        for sweep_dict in args:
            self._sweeps.append(Sweep(sweep_dict))

    def set_gettables(self, *args) -> None:
        """
        Sets GettableParameters that will be retreived during measurement
        
        Args:
            *args (GettableParameter): Parameters to be measured
        """
        if not all( isinstance(param, GettableParameter) for param in args):
            raise TypeError("All arguments need to be of type dict")
        self._gettables = list(args)

    def add_subsequence(self, new_sequence) -> None:
        """
        Adds a subsequence to the entire programm. Subsequences are added as 
        QCoDeS 'Submodules'. Sequences are executed in order of them being added.

        Args:
            new_sequence (Sequence): Subsequence to be added
            verbose (bool): Flag to trigger debug printouts
        """
        new_sequence._parent = self
        self.add_submodule(new_sequence.name, new_sequence)

    def get_qua_program(self, simulate = False):
        """
        Runs the entire sequence by searching recursively through init, 
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
            self.recursive_qua_generation(seq_type = 'declare')
            with infinite_loop_():
                if not simulate:
                    pause()
                self.recursive_sweep_generation(copy.copy(self.sweeps))
            with stream_processing():
                self.recursive_qua_generation(seq_type = 'stream')
        return prog

    def qua_declare_sweep_vars(self) -> None:
        """ Declares all sweep variables as QUA with their correct type """
        logging.debug("Start declaring QUA variables in %s", self.name)
        for sweep in self.sweeps:
            for param, setpoints in sweep.config.items():
                logging.debug(
                    "Adding qua %s variable for %s on subsequence %s",
                    type(param.get()), param.name, self.name
                )
                param.qua_sweeped = True
                param.vals= Arrays()
                param.set(setpoints)
                if param.get().dtype == float:
                    param.qua_var = declare(fixed)
                    param.qua_sweep_arr = declare(fixed, value = setpoints)
                elif param.get().dtype == int:
                    param.qua_var = declare(int)
                    param.qua_sweep_arr = declare(int, value = setpoints)
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
        if seq_type == 'declare' and len(self.sweeps) != 0:
            # TODO: When is this supposed to happen?
            self.qua_declare_sweep_vars()
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
            logging.debug("No params addded to %s", self.name)
            return
        for param_name, param_dict in config.items():
            if 'elements' in param_dict:
                for element, value in param_dict['elements'].items():
                    self.add_parameter(
                        name  = f'{param_name}_{element}',
                        config_name = param_name,
                        unit = param_dict["unit"],
                        initial_value = value,
                        parameter_class = SequenceParameter,
                        element = element,
                        get_cmd = None,
                        set_cmd = None,
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
        simulated_job = qmm.simulate(self.sample.config, 
                           self.get_qua_program(simulate = True),
                           SimulationConfig(duration=duration))

        samples = simulated_job.get_simulated_samples()
        utils.plot_opx_simulation_results(samples)
        return simulated_job

    def arbok_go(
            self, to_volt: Union[str, List], operation: str,
            from_volt: Optional[Union[str, List]] = None,
            duration = None
        ):
        """ 
        Helper function that `play`s a qua operation on the respective elements 
        specified in the sequence config.
        TODO:   - [ ] raise error if no params were found
                - [ ] raise error when target and origin dims dont match
                - [ ] only pass duration kwarg if given
                - [ ] raise error if duration is too short
                - [ ] remove from sequence -> independent helper 

        Args:
            seq (Sequence): Sequence
            from_volt (str, List): voltage point to come from
            to_volt (str, List): voltage point to move to
            duration (str): duration of the operation 
            operation (str): Operation to be played -> find in OPX config
        """
        if from_volt is None:
            from_volt = ['vHome']
        if callable(duration):
            duration = int(duration())
        origin_param_sets = self._find_parameters_from_keywords(from_volt)
        target_param_sets = self._find_parameters_from_keywords(to_volt)

        for target_list, origin_list in zip(target_param_sets, origin_param_sets):
            target_v = sum([par() for par in target_list])
            origin_v = sum([par() for par in origin_list])
            logging.debug(
                "Moving %s from %s to %s", 
                target_list[0].element, origin_v, target_v
                )
            kwargs = {
                'pulse': operation*amp( target_v - origin_v ),
                'element': target_list[0].element
                }
            if duration is not None:
                kwargs['duration'] = int(duration)
            play(**kwargs)

    def _find_parameters_from_keywords(self, keys: Union[str, List]):
        """
        Returns a list containing all parameters of the seqeunce with names that
        contain one of names in the 'keys' list.

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


