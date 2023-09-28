""" Module containing Sequence class """

import warnings
import copy
from typing import List, Union, Optional
import logging as lg

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

from arbok_driver.sample import Sample
from arbok_driver.sequence_parameter import SequenceParameter

class Sequence(Instrument):
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
        self._parent = None
        self.settables = []
        self.setpoints_grid = []
        self.gettables = []
        self.sweep_len = 1
        self.param_config = param_config

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

    def sweep_size(self) -> int:
        """ Returns the sweep size from the settables via the setpoints_grid"""
        sweep_size = 1
        for sweep_list in self.setpoints_grid:
            sweep_size *= len(sweep_list[0])
        return sweep_size

    @property
    def parent(self) -> InstrumentBase:
        return self._parent

    @property
    def root_instrument(self) -> InstrumentBase:
        if self._parent is None:
            return self
        return self._parent.root_instrument

    def add_subsequence(self, new_sequence):
        """
        Adds a subsequence to the entire programm. Subsequences are added as 
        QCoDeS 'Submodules'. Sequences are executed in order of them being added.

        Args:
            new_sequence (Sequence): Subsequence to be added
            verbose (bool): Flag to trigger debug printouts
            
        """
        new_sequence._parent = self
        self.add_submodule(new_sequence.name, new_sequence)

    def set_settables(self, *args):
        """ Prepares and sets the settables """
        for arg in args:
            if isinstance(arg, SequenceParameter):
                self.settables.append([arg])
            elif isinstance(arg, list):
                self.settables.append(arg)
        return

    def set_setpoints_grid(self, *args):
        """ Prepares and sets the setpoints grid """
        for arg in args:
            if isinstance(arg[0], (list, np.ndarray)):
                self.setpoints_grid.append(arg)
            else:
                self.setpoints_grid.append([arg])



    def get_program(self, simulate = False):
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
                if not simulate: #not simulate: #not simulate:
                    pause()
                self.recursive_sweep_generation(
                    copy.copy(self.settables),
                    copy.copy(self.setpoints_grid)
                    )

            with stream_processing():
                self.recursive_qua_generation(seq_type = 'stream')
        return prog

    def qua_declare_sweep_vars(self):
        """ Declares all sweep variables """
        lg.info("Start declaring")
        for i, sweep in enumerate(self.settables):
            if not isinstance(sweep, list):
                self.settables[i] = [sweep]
                self.setpoints_grid[i] = [self.setpoints_grid[i]]
            self.sweep_len *= len(self.setpoints_grid[i][0])
            for j, par in enumerate(sweep):
                lg.info("Adding qua %s variable for %s", type(par.get()), par.name)
                par.qua_sweeped = True
                par.vals= Arrays()
                par.set(self.setpoints_grid[i][j])
                if par.get().dtype == float:
                    par.qua_var = declare(fixed)
                    par.qua_sweep_arr = declare(fixed, value = self.setpoints_grid[i][j])
                elif par.get().dtype == int:
                    par.qua_var = declare(int)
                    par.qua_sweep_arr = declare(int, value = self.setpoints_grid[i][j])
                else:
                    raise TypeError(
                        "Type not supported. Must be float or int")

    def recursive_sweep_generation(self, settables, setpoints_grid):
        """
        Recursively generates QUA parameter sweeps by introducing one nested QUA
        loops per swept parameter. The last given settables and its corresponding
        setpoints list is in the innermost loop.
        TODO: Reimplement a fast version of this for non-paired parameter 
            sweeps
        Args:
            settables (list): List of QCodes parameter names to sweep
            setpoints_grid (list): List of QCodes parameter set values
            simulate (bool): Flag whether program is simulated
        """
        if len(settables) == 0:
            # this condition gets triggered if we arrive at the innermost loop
            self.recursive_qua_generation('sequence')
            return
        elif len(settables) == len(setpoints_grid) and len(settables) > 0:
            lg.info("Adding qua loop for %s", [par.name for par in settables[-1]])
            new_settables = settables[:-1]
            new_setpoints_grid = setpoints_grid[:-1]
            idx = declare(int)
            with for_(idx, 0, idx < len(setpoints_grid[-1][0]), idx + 1):
                for par in settables[-1]:
                    assign(par.qua_var, par.qua_sweep_arr[idx])
                self.recursive_sweep_generation(new_settables, new_setpoints_grid)
            return
        else:
            raise ValueError(
                "settables and setpoints_grid must have same dimensions")

    def recursive_qua_generation(self, seq_type):
        """
        Recursively runs all QUA code stored in submodules of the given sequence

        Args:
            seq_type (str): Type of qua code containing method to look for
        """
        if seq_type == 'declare' and len(self.settables) != 0:
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
        
        Args:
            config (dict): Configuration containing all sequence parameters
        """
        if config is None:
            print(f"No params addded to {self.name}")
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
                warnings.warn("Parameter " + str(param_name) +
                              " is not of type float int or list")

    def run_remote_simulation(self, host, duration: int):
        """
        Simulates the MW sequence on a remote simulator on the host

        Args:
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
                           self.get_program(simulate = True),
                           SimulationConfig(duration=duration))

        samples = simulated_job.get_simulated_samples()
        self._plot_simulation_results(samples)
        return simulated_job

    def arbok_go(
            self, to_volt: Union[str, List], operation: str,
            from_volt: Optional[Union[str, List]] = None,
            duration = None
        ):
        """ 
        Helper function that `play`s a qua operation on the respective elements 
        specified in the sequence config.
        
        Args:
            seq (Sequence): Sequence
            from_volt (str, List): voltage point to come from
            to_volt (str, List): voltage point to move to
            duration (str): duration of the operation 
            operation (str): Operation to be played -> find in OPX config
        """
        # if duration is None:
        #     duration = lambda: 0 # minimum of 20 ns (5 cycles)
        # elif duration < 5:
        #     raise ValueError("Cant be shorter than 5 cycles (20 ns)")

        if from_volt is None:
            from_volt = ['vHome']

        origin_param_sets = self._find_parameters_from_keywords(from_volt)
        target_param_sets = self._find_parameters_from_keywords(to_volt)

        for target_list, origin_list in zip(target_param_sets, origin_param_sets):
            
            target_v = sum([par() for par in target_list])
            origin_v = sum([par() for par in origin_list])
            play(
                operation*amp( target_v - origin_v ),
                target_list[0].element,
                duration = duration()
                )

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

    def _plot_simulation_results(self, simulated_samples):
        """ Visualizes analog and digital channel simulation results """
        fig, [a, b] = plt.subplots(2, sharex= True)
        for channel, data in simulated_samples.con1.analog.items():
            a.plot(data, label = channel)
        for channel, data in simulated_samples.con1.digital.items():
            b.plot(data, label = channel)

        ncols_a = int((len(a.lines)-1)/10) + 1
        a.legend(bbox_to_anchor=(1.0, 1.0), loc='upper left', fontsize = 8,
                 title = 'analog', ncols = ncols_a)
        a.grid()
        a.set_ylabel("Voltage in V")
        a.set_title("simulated analog/digital outputs", loc = 'right')

        ncols_b = int((len(b.lines)-1)/10) + 1
        b.legend(bbox_to_anchor=(1.0, 1.0), loc='upper left', fontsize = 8,
                 title = 'digital', ncols = ncols_b)
        b.grid()
        b.set_xlabel("Time in ns")
        b.set_ylabel("Digital Signal")
        fig.subplots_adjust(wspace=0, hspace=0)
