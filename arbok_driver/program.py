import copy
from typing import Union
import math

from qm.QuantumMachinesManager import QuantumMachinesManager
from qm.qua import program, infinite_loop_, pause, stream_processing
from qm import SimulationConfig

from qcodes.instrument import Instrument
from qcodes.parameters import Parameter
from qcodes.validators import Arrays
from qcodes.dataset import Measurement

from .sequence_base import SequenceBase
from .sample import Sample
from .sweep import Sweep
from .gettable_parameter import GettableParameter

class Program(Instrument, SequenceBase):
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
        #super(Instrument, self).__init__(name, *args, **kwargs)
        super(SequenceBase, self).__init__(name, sample, param_config, *args, **kwargs)
        self.qmm = None
        self.opx = None
        self.qm_job = None
        self.result_handles = None
        self.stream_mode = "pause_each"

        self._sweeps = []
        self._gettables = []
        self._sweep_size = 1

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
        for sweep in self.sweeps:
            for param, setpoints in sweep.config_to_register.items():
                param.vals = Arrays(shape=(len(setpoints),))

    def register_gettables(self, *args) -> None:
        """
        Registers GettableParameters that will be retreived during measurement
        
        Args:
            *args (GettableParameter): Parameters to be measured
        """
        if not all(isinstance(param, GettableParameter) for param in args):
            raise TypeError("All arguments need to be of type dict")
        if not all(param.root_instrument == self for param in args):
            raise AttributeError(
                f"Not all GettableParameters belong to {self.name}")
        self._gettables = list(args)

        gettable_setpoints = ()
        for sweep in self.sweeps:
            gettable_setpoints += tuple(sweep.config_to_register.keys())
        for i, gettable in enumerate(self.gettables):
            gettable.batch_size = self.sweep_size
            gettable.can_resume = True if i==(len(self.gettables)-1) else False
            gettable.setpoints = gettable_setpoints
            gettable.vals = Arrays(
                shape = tuple(sweep.length for sweep in self.sweeps))
        self.sweeps.reverse()

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
            self.get_qua_program(simulate = True),
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
