import copy
from typing import Union

from qm import qua, SimulationConfig, generate_qua_script
from qm import QuantumMachinesManager

from qcodes.instrument import Instrument
from qcodes.parameters import Parameter
from qcodes.dataset import Measurement

from .sequence import Sequence
from .sample import Sample
from . import utils

class Program(Instrument):
    """
    Class containing all functionality to manage and run modular sequences on a 
    physical OPX instrument
    TODO: Add ask_raw and write_raw abstract methods
    """
    def __init__(
            self,
            name: str,
            sample: Sample,
            param_config: Union[dict, None] = None,
            **kwargs
            ) -> None:
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
        self.qmm = None
        self.opx = None
        self.qm_job = None
        self.result_handles = None
        self.stream_mode = "pause_each"

        self._sequences = []

    @property
    def sequences(self):
        """Sequences to be run within program uploaded to the OPX"""
        return self._sequences

    def connect_opx(self, host_ip: str):
        """
        Creates QuantumMachinesManager and opens a quantum machine on it with
        the given IP address
        
        Args:
            host_ip (str): Ip address of the OPX
        """
        self.qmm = QuantumMachinesManager(host = host_ip)
        self.opx = self.qmm.open_qm(self.sample.config)

    def add_sequence(self, new_sequence: Sequence):
        """
        Adds `Sequence` to the program and adds it as a QCoDeS sub-module
        
        Args:
            new_sequence (Sequence): Sequence to be added
        """
        self._sequences.append(new_sequence)
        new_sequence.program = self
        self.add_submodule(new_sequence.name, new_sequence)

    def get_qua_program(self, simulate = False) -> qua.program:
        """
        Compiles all qua code from its sequences and writes their loops
        
        Args:
            simulate (bool): True if the program is meant to be simulated

        Reterns:
            qua_program: Program from qm context manager
        """
        with qua.program() as qua_program:
            for sequence in self._sequences:
                sequence.qua_declare_sweep_vars()
                sequence.recursive_qua_generation(seq_type = 'declare')
            for sequence in self._sequences:
                with qua.infinite_loop_():
                    if not simulate:
                        #if sequence.input_streams is not None:
                        #    sequence.advance_input_streams()
                        qua.pause()
                    sequence.recursive_sweep_generation(
                        copy.copy(sequence.sweeps))
            with qua.stream_processing():
                sequence.recursive_qua_generation(seq_type = 'stream')
        return qua_program

    def run(self, qua_program):
        """
        Sends the qua program for execution to the OPX and sets the programs 
        result handles 
        
        Args:
            qua_program (program): QUA program to be executed
        """
        self.qm_job = self.opx.execute(qua_program)
        self.result_handles = self.qm_job.result_handles
        if self.stream_mode == "pause_each":
            self.qm_job.resume()

    def _register_qc_params_in_measurement(self, measurement: Measurement):
        """
        Configures QCoDeS measurement object from the arbok program
        
        Args:
            measurement (Object): QCoDeS measurement object
            shots (int): Amount of repetitions to average
        """
        if not hasattr(self, 'iteration'):
            iteration = ShotNumber(name='iteration', instrument=self)
            self.add_parameter(iteration)

        measurement.register_parameter(self.iteration)
        for gettable in self.gettables:
            measurement.register_parameter(
                gettable, setpoints = (self.iteration,) )
        return measurement

    def print_qua_program_to_file(
            self, file_name: str, qua_program = None, add_config: bool = False):
        """
        Creates file with 'filename' and prints the QUA code to this file
        
        Args:
            file_name (str): File name of target file
            add_config (bool): Whether config is added to output file
        """
        if qua_program is None:
            print("Generating qua program from sequences")
            qua_program = self.get_qua_program()
        with open(file_name, 'w', encoding="utf-8") as file:
            if self.sample is not None and add_config:
                file.write(generate_qua_script(
                    qua_program, self.sample.config
                    ))
            else:
                file.write(generate_qua_script(qua_program))

    def run_infinite_average(self, measurement: Measurement, shots: int):
        """ 
        Runs QCoDeS measurement and returns the resulting dataset
        
        Args:
            measurement (Measurement): qcodes measurement object
            shots (int): amount of repetitions to be performed for averaging  
        Returns:
            dataset: QCoDeS dataset
        """
        self._register_qc_params_in_measurement(measurement)
        with measurement.run() as datasaver:
            for shot in range(shots):
                self.iteration.set(shot)
                add_result_args = ((self.iteration, self.iteration.get()),)
                for gettable in self.gettables:
                    add_result_args += ((gettable, gettable.get_raw(),),)
                datasaver.add_result(*add_result_args)
            dataset = datasaver.dataset
        return dataset

    def run_local_simulation(self, duration: int, nr_controllers: int = 1):
        """
        Simulates the given program of the sequence for `duration` cycles
        TODO: Move to SequenceBase and add checks if OPX is connected
        Args:
            duration (int): Simulation duration in cycles

        Returns:
            simulated_job (SimulatedJob): QM job with waveform simulation result
            nr_controllers (int): Nr of controllers to fetch simulation results
        """
        if not self.qmm:
            raise ConnectionError(
                "No QMM found! Connect an OPX via `connect_OPX`")
        simulated_job = self.qmm.simulate(
            self.sample.config,
            self.get_qua_program(simulate = True),
            SimulationConfig(duration=duration))

        samples = simulated_job.get_simulated_samples()
        for i in range(nr_controllers):
            con_samples = getattr(samples, f'con{i+1}')
            utils.plot_qmm_simulation_results(con_samples)
        return simulated_job

    def ask_raw(self, cmd: str) -> str:
        """Abstract method from qcodes Instrument"""
        raise NotImplementedError

    def write_raw(self, cmd: str) -> str:
        """Abstract method from qcodes Instrument"""
        raise NotImplementedError

class ShotNumber(Parameter):
    """ Parameter that keeps track of averaging during measurement """
    def __init__(self, name, instrument):
        super().__init__(name, instrument = instrument)
        self._count = 0

    def get_raw(self): return self._count
    def set_raw(self, x): self._count = x
