"""
Module containing the ArbokDriver class for managing and running sequences
on a physical OPX instrument.
"""
from __future__ import annotations
from typing import TYPE_CHECKING
import copy

import numpy as np
import xarray as xr
from qm import SimulationConfig, generate_qua_script
from qm.quantum_machines_manager import QuantumMachinesManager
from qcodes.instrument import Instrument
from qcodes.dataset import load_or_create_experiment
from sqlalchemy.orm import Session

from . import utils
from .measurement import Measurement
from .sqlalchemy_classes import SqlRun

if TYPE_CHECKING:
    from .device import Device
    from .experiment import Experiment
    from .measurement_runners.measurement_runner_base import MeasurementRunnerBase
    from .sqlalchemy_classes import SqlRun

class ArbokDriver(Instrument):
    """
    Class containing all functionality to manage and run modular sequences on a 
    physical OPX instrument
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
        self._measurements = []
        self.add_parameter('iteration', get_cmd = None, set_cmd =None)

        self.database_engine = None
        self.minio_filesystem = None
        self.station = None

    @property
    def measurements(self) -> list[Measurement]:
        """Measurements to be run within program uploaded to the OPX"""
        return self._measurements

    def reset_measurements(self) -> None:
        """
        Resets all measurements in the program
        TODO: delete instances of those measurements
        """
        for measurement in self._measurements:
            print(f"Deleting measurement: {measurement.short_name}")
            del measurement
        self._measurements = []
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
            **kwargs: Arbitrary keyword arguments for QMM instanciation
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

    def add_measurement(self, new_measurement: Measurement):
        """
        Adds a class which inherits `Measurement` to the program and adds it
        as a QCoDeS sub-module
        
        Args:
            new_measurement (Measurement): The instance which inherits
            Measurement to be added
        """
        self._measurements.append(new_measurement)

    def run(self, qua_program, **kwargs):
        """
        Sends the qua program for execution to the OPX and sets the programs 
        result handles 
        
        Args:
            qua_program (program): QUA program to be executed
        """
        self.qm_job = self.opx.execute(qua_program, **kwargs)
        self.result_handles = self.qm_job.result_handles

    def print_qua_program_to_file(
            self,
            path: str,
            qua_program,
            add_config: bool = False
            ) -> None:
        """
        Creates file with 'filename' and prints the QUA code to this file
        
        Args:
            file_name (str): File name of target file
            qua_program (program): QUA program to be printed
            add_config (bool): Whether config is added to output file
        """
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
            experiment: Experiment,
            qc_measurement_name: str | None = None,
            name: str = 'measurement',
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
        measurement.qc_experiment = load_or_create_experiment(
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
        ) -> tuple[MeasurementRunner, Measurement]:
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

    def check_db_engine_and_bucket_connected(self):
        """
        Checks if database engine and s3 bucket are connected
        Raises error if not connected
        TODO: ping both TCP connections to check if still alive
        """
        if self.database_engine is None:
            raise ConnectionError(
                "No database engine connected! Please connect a database "
                "engine to the arbok_driver before running measurements.")
        if self.minio_filesystem is None:
            raise ConnectionError(
                "No MinIO filesystem connected! Please connect a MinIO filesystem to the "
                "arbok_driver before running measurements.")

    def get_run_from_id(self, run_id: int) -> SqlRun:
        """
        Fetches a run from the connected arbok database engine based on the
        given run ID
        
        Args:
            run_id (int): ID of the run to be fetched
        Returns:
            run (arbok_driver.sqlalchemy_classes.SqlRun): detached run instance
        """
        if self.database_engine is None:
            raise ConnectionError(
                "No database engine connected! Please connect a database "
                "engine to the arbok_driver before fetching runs.")
        with Session(self.database_engine) as session:
            sql_run = session.get(SqlRun, run_id)
        return sql_run

    def get_data_from_id(self, run_id: int) -> xr.Dataset:
        """
        Fetches data from the connected database engine based on the
        given run ID
        
        Args:
            run_id (int): ID of the run to fetch data from
        Returns:
            xr_dataset (xarray.Dataset): Lazy loaded xarray dataset. Will only
                load data when using .load() or .compute() methods!
        """
        sql_run = self.get_run_from_id(run_id)
        minio_name = f"{sql_run.run_id}_{sql_run.uuid}"
        store = self.minio_filesystem.get_mapper(f'dev/{minio_name}/data.zarr')
        xr_dataset = xr.open_zarr(store, consolidated = True)
        return xr_dataset
