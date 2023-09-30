import copy
from typing import Union

from qm.QuantumMachinesManager import QuantumMachinesManager
from qm.qua import program, infinite_loop_, pause, stream_processing
from qm import SimulationConfig

from qcodes.parameters import Parameter
from qcodes.validators import Arrays
from qcodes.dataset import Measurement

from .sub_sequence import SubSequence
from .sample import Sample

class Program(SubSequence):
    """
    Class containing all functionality to manage and run modular sequences on a 
    physical OPX instrument
    """
    def __init__(self, name: str, sample: Sample, *args,
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
        super().__init__(name, sample, param_config, *args, **kwargs)

        self.qmm = None
        self.opx = None
        self.qm_job = None
        self.result_handles = None

        self.stream_mode = "pause_each"
    
    def connect_opx(self, host_ip: str):
        """
        Creates QuantumMachinesManager and opens a quantum machine on it with
        the given IP address
        
        Args:
            host_ip (str): Ip address of the OPX
        """
        self.qmm = QuantumMachinesManager(host = host_ip)
        self.opx = self.qmm.open_qm(self.sample.config)

    def run(self, program):
        """
        Sends the program for execution to the OPX and sets the programs 
        result handles 
        
        Args:
            program (program): QUA program to be executed
        """
        self.qm_job = self.opx.execute(program)
        self.result_handles = self.qm_job.result_handles
        if self.stream_mode == "pause_each":
            self.qm_job.resume()

    def get_running_qm_job(self):
        """ Finds qm_job on the connected opx and returns it. Also sets program 
        attributes qm_job and result_handles """
        # FIXME: not really working .. retreived job is not functional after 
        #   restarting python environment
        self.qm_job = self.opx.get_running_job()
        self.result_handles = self.qm_job.result_handles
        return self.qm_job

    def prepare_gettables(self):
        """
        Sets validators of the `SequenceParameter`s and `GettableParameters`.
        `GettableParameters` are QCoDeS ParameterWithSetpoints. Those are
        defined with setpoints whose validators have to align with their 
        setpoints.
        """
        setpoints = ()
        for sweep in self.sweeps:
            for param, setpoints in sweep.config_to_register.items():
                param.vals = Arrays(shape=(len(setpoints),))
                setpoints += param
        for i, gettable in enumerate(self.gettables):
            gettable.batch_size = self.sweep_size()
            gettable.can_resume = True if i==(len(self.gettables)-1) else False
            gettable.setpoints = setpoints
            gettable.vals = Arrays(
                shape = (sweep.length for sweep in self.sweeps))
        self.sweeps.reverse()

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

    def run_qc_measurement(self, measurement: Measurement, shots: int):
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
    
    def run_local_simulation(self, duration: int):
        """
        Simulates the given program of the sequence for `duration` cycles

        Args:
            duration (int): 

        Returns:
            simulated_job (SimulatedJob): QM job with waveform simulation result
        """
        if not self.qmm:
            raise ConnectionError(
                "No QMM found! Connect an OPX via `connect_OPX`")
        simulated_job = self.qmm.simulate(
            self.sample.config,
            self.get_program(simulate = True),
            SimulationConfig(duration=duration))
     
        samples = simulated_job.get_simulated_samples()
        self._plot_simulation_results(samples)
        return simulated_job
    
class ShotNumber(Parameter):
    """ Parameter that keeps track of averaging during measurement """
    def __init__(self, name, instrument):
        super().__init__(name, instrument = instrument)
        self._count = 0

    def get_raw(self): return self._count
    def set_raw(self, x): self._count = x
