import copy
from typing import Union

import numpy as np

from qm import SimulationConfig, generate_qua_script
from qm.quantum_machines_manager import QuantumMachinesManager

import qcodes as qc

from .experiment import Experiment
from .measurement import Measurement
from .sequence_base import SequenceBase
from .device import Device
from . import utils

class ArbokDriver(qc.Instrument):
    """
    Class containing all functionality to manage and run modular sequences on a 
    physical OPX instrument
    TODO: Add ask_raw and write_raw abstract methods
    """

    def __init__(
            self,
            name: str,
            device: Device,
            **kwargs
            ) -> None:
        """
        Constructor class for `Program` class
        
        Args:
            name (str): Name of the instrument
            device (Device): Device class describing phyical device
            **kwargs: Arbitrary keyword arguments for qcodes Instrument class
        """
        super().__init__(name, **kwargs)
        self.device = device
        self.qmm = None
        self.opx = None
        self.qm_job = None
        self.result_handles = None
        self.no_pause = False
        self.is_mock = False
        self._sequences = []
        self.add_parameter('iteration', get_cmd = None, set_cmd =None)

    @property
    def sequences(self) -> list:
        """Sequences to be run within program uploaded to the OPX"""
        return self._sequences

    def reset_sequences(self) -> None:
        """
        Resets all sequences in the program
        TODO: delete instances of those sequences
        """
        self._sequences = []
        self.submodules = {}

    def connect_opx(
            self,
            host_ip: str,
            qm_config: dict = None,
            reconnect: bool = False,
            **kwargs) -> None:
        """
        Creates QuantumMachinesManager and opens a quantum machine on it with
        the given IP address
        
        Args:
            host_ip (str): Ip address of the OPX
            qm_config (dict): QM/OPX config dictionary to be used. Defaults to
                None, in which case the config from the device is used. If given
                overwrites the device config.
            reconnect (bool): Whether to reconnect to the OPX if already
                connected. Keeps QMM alive if true. Defaults to False.
            **kargs: Arbitrary keyword arguments for QMM instanciation
        """
        if not reconnect:
            self.qmm = QuantumMachinesManager(
                host = host_ip, **kwargs)
        if qm_config is not None:
            if not isinstance(qm_config, dict):
                raise ValueError(
                    "qm_config must be a dictionary, not a string")
            self.device.config = copy.deepcopy(qm_config)
        self.opx = self.qmm.open_qm(self.device.config)

    def reconnect_opx(
            self, host_ip: str, qm_config: dict = None) -> None:
        """
        Reconnects to the OPX with the given IP address and closes the previous
        connection
        
        Args:
            host_ip (str): Ip address of the OPX
            qm_config (dict): QM/OPX config dictionary to be used. Defaults to
                None, in which case the config from the device is used. If given
                overwrites the device config. 
        """
        if self.opx is not None:
            print('Closing previous connection')
            self.opx.close()
            self.qmm.close_all_quantum_machines()
        self.connect_opx(host_ip, qm_config, reconnect = True)

    def add_sequence(self, new_sequence: SequenceBase):
        """
        Adds a class which inherits `SequenceBase` to the program and adds it
        as a QCoDeS sub-module
        
        Args:
            new_sequence (SequenceBase): The instance which inherits
            SequenceBase to be added
        """
        self._sequences.append(new_sequence)

    def run(self, qua_program, **kwargs):
        """
        Sends the qua program for execution to the OPX and sets the programs 
        result handles 
        
        Args:
            qua_program (program): QUA program to be executed
        """
        self.qm_job = self.opx.execute(qua_program, **kwargs)
        self.result_handles = self.qm_job.result_handles

    def _register_qc_params_in_measurement(
            self, measurement: qc.dataset.Measurement):
        """
        Configures QCoDeS measurement object from the arbok program
        
        Args:
            measurement (Object): QCoDeS measurement object
        
        Returns:
            measurement (Object): QCoDeS measurement object
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
            self,
            path: str,
            qua_program = None,
            add_config: bool = False
            ) -> None:
        """
        Creates file with 'filename' and prints the QUA code to this file
        
        Args:
            file_name (str): File name of target file
            qua_program (program): QUA program to be printed
            add_config (bool): Whether config is added to output file
        """
        if qua_program is None:
            print("Generating qua program from sequences")
            qua_program = self.get_qua_program()
        with open(path, 'w', encoding="utf-8") as file:
            if self.device is not None and add_config:
                file.write(generate_qua_script(
                    qua_program, self.device.config
                    ))
            else:
                file.write(generate_qua_script(qua_program))

    def run_local_simulation(
            self,
            qua_program,
            duration: int,
            nr_controllers: int = 1,
            plot = True,
            **kwargs
            ):
        """
        Simulates the given program of the sequence for `duration` cycles
        TODO: Move to SequenceBase and add checks if OPX is connected
        Args:
            qua_program (program): QUA program to be simulated
            duration (int): Simulation duration in cycles
            nr_controllers (int): Number of controllers to simulate
            plot (bool): Whether to plot the simulation results
            **kwargs: Arbitrary keyword arguments for QMM simulation

        Returns:
            simulated_job (SimulatedJob): QM job with waveform simulation result
            nr_controllers (int): Nr of controllers to fetch simulation results
        """
        if not self.qmm:
            raise ConnectionError(
                "No QMM found! Connect an OPX via `connect_OPX`")
        simulated_job = self.qmm.simulate(
            self.device.config,
            qua_program,
            SimulationConfig(duration=duration),
            **kwargs
        )

        devices = simulated_job.get_simulated_devices()
        if plot:
            for i in range(nr_controllers):
                con_devices = getattr(devices, f'con{i+1}')
                utils.plot_qmm_simulation_results(con_devices)
        return simulated_job

    def get_idn(self):
        """
        Overload the get_idn method as we don't have one.
        """
        return None

    def ask_raw(self, cmd: str) -> str:
        """Abstract method from qcodes Instrument"""
        raise NotImplementedError

    def write_raw(self, cmd: str) -> str:
        """Abstract method from qcodes Instrument"""
        raise NotImplementedError

    def create_measurement_from_experiment(
            self,
            name: str,
            experiment: Experiment,
            qc_measurement_name: str | None = None
            ) -> Measurement:
        """
        Creates an arbok and QCoDeS measurement from an arbok-experiment
        
        Args:
            name (str): Name of the measurement (py. variable name compliant)
            experiment (arbok_driver.Experiment): Experiment to be run
            qc_measurement_name (str): Name of the QCoDeS measurement
                (as it will be saved in the database)

        Returns:
            measurement (arbok_driver.Measurement): Measurement instance
        """
        measurement = Measurement(
            parent = self,
            name = name,
            device = self.device,
            sequence_config = self.device.param_config
            )
        if qc_measurement_name is None:
            qc_measurement_name = experiment.name
        measurement.qc_experiment = qc.dataset.load_or_create_experiment(
            experiment.name, self.device.name)
        measurement.qc_measurement_name = qc_measurement_name
        measurement.add_subsequences_from_dict(experiment.sequences)
        return measurement

    def add_measurement_and_create_qc_measurement(
        self,
        measurement_name: str,
        arbok_experiment: 'Experiment',
        iterations: str = None,
        sweeps: dict = None,
        gettables = None,
        gettable_keywords = None,
        sweep_list: list = None,
        qc_measurement_name = None
        ) -> tuple['MeasurementRunner', Measurement]:
        """
        Adds a measurement to the arbok_driver based on the arbok_experiment and
        creates a QCoDeS measurement and experiment. Returns the measurement and
        the measurement loop function

        Args:
            measurement_name (str): Name of the measurement
            arbok_experiment (ArbokExperiment): Experiment to be run
            iterations (int): Amount of repetitions to be performed
            sweeps (list): List of sweep parameters
            gettables (str): Gettables to be registered in the measurement
            gettable_keywords (dict): Keywords to search for gettable parameters
            sweep_list (list): List of of sweep dicts for external instruments
        """
        if qc_measurement_name is None:
            qc_measurement_name = measurement_name
        meas = self.create_measurement_from_experiment(
            name = measurement_name,
            experiment = arbok_experiment,
            qc_measurement_name = qc_measurement_name
            )

        if sweeps is not None:
            meas.set_sweeps(*sweeps)

        if gettables is not None and gettable_keywords is not None:
            raise ValueError(
                "Please provide gettables OR gettable_keywords, not both")
        elif gettables is not None:
            ### Registering all gettables
            meas.register_gettables(*gettables)
        elif gettable_keywords is not None:
            ### Finding all gettables with the given keywords
            meas.register_gettables(keywords=gettable_keywords)
        else:
            ### Registers all available gettables if both are None
            meas.register_gettables(*meas.available_gettables)

        if iterations is not None:
            sweep_list_arg = [{self.iteration: np.arange(iterations)}]
        else:
            sweep_list_arg = []
        if sweep_list is not None:
            sweep_list_arg.extend(sweep_list)

        measurement_runner = meas.get_measurement_runner(sweep_list_arg)
        return measurement_runner, meas

class ShotNumber(qc.Parameter):
    """ Parameter that keeps track of averaging during measurement """
    def __init__(self, name, instrument):
        super().__init__(name, instrument = instrument)
        self._count = 0

    def get_raw(self): return self._count
    def set_raw(self, x): self._count = x
