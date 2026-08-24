"""
Module containing the ArbokDriver class for managing and running sequences
on hardware via a configurable backend.
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Any
import copy

import xarray as xr
from qcodes.instrument import Instrument
from qcodes.dataset import load_or_create_experiment
from sqlalchemy.orm import Session

from .backend import Backend
from .backends import QuaBackend
from .device import Device
from .measurement import Measurement
from .sqlalchemy_classes import SqlRun

if TYPE_CHECKING:
    from .experiment import Experiment
    from .sqlalchemy_classes import SqlRun

class ArbokDriver(Instrument):
    """
    Class containing all functionality to manage and run modular sequences on
    a hardware backend.
    """

    def __init__(
            self,
            name: str,
            device: Device,
            backend: Backend | None = None,
            **kwargs
            ) -> None:
        """
        Constructor class for `Program` class

        Args:
            name (str): Name of the instrument
            device (Device): Device class describing phyical device
            backend (Backend): Hardware backend to use. Defaults to QuaBackend.
            **kwargs: Arbitrary keyword arguments for qcodes Instrument class
        """
        super().__init__(name, **kwargs)
        if not isinstance(device, Device):
            raise TypeError(f"device must be type Device, is {type(Device)}")
        self.device: Device = device
        self.backend: Backend = backend if backend is not None else QuaBackend()
        self.is_mock: bool = False
        self._measurements: list[Measurement] = []
        self.add_parameter('iteration', get_cmd = None, set_cmd =None)

        self.database_engine = None
        self.minio_filesystem = None
        self.station = None

    # ──────────────────────────────────────────────────────────────────────
    # Backwards-compat properties — these live on QuaBackend now
    # ──────────────────────────────────────────────────────────────────────

    @property
    def qmm(self) -> Any:
        """QUA-specific: QuantumMachinesManager (lives on QuaBackend)."""
        return getattr(self.backend, 'qmm', None)

    @qmm.setter
    def qmm(self, value: Any) -> None:
        self.backend.qmm = value

    @property
    def opx(self) -> Any:
        """QUA-specific: open QuantumMachine handle (lives on QuaBackend)."""
        return getattr(self.backend, 'opx', None)

    @opx.setter
    def opx(self, value: Any) -> None:
        self.backend.opx = value

    @property
    def qm_job(self) -> Any:
        """QUA-specific: running job handle (lives on QuaBackend)."""
        return getattr(self.backend, 'qm_job', None)

    @qm_job.setter
    def qm_job(self, value: Any) -> None:
        self.backend.qm_job = value

    @property
    def result_handles(self) -> Any:
        """QUA-specific: stream result handles (lives on QuaBackend)."""
        return getattr(self.backend, 'result_handles', None)

    @result_handles.setter
    def result_handles(self, value: Any) -> None:
        self.backend.result_handles = value

    @property
    def host_ip(self) -> str | None:
        """QUA-specific: OPX host address (lives on QuaBackend)."""
        return getattr(self.backend, 'host_ip', None)

    @host_ip.setter
    def host_ip(self, value: str) -> None:
        self.backend.host_ip = value

    # ──────────────────────────────────────────────────────────────────────
    # Measurements
    # ──────────────────────────────────────────────────────────────────────

    @property
    def measurements(self) -> list[Measurement]:
        """Measurements to be run within program"""
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

    # ──────────────────────────────────────────────────────────────────────
    # Hardware connection (delegated to backend)
    # ──────────────────────────────────────────────────────────────────────

    def connect_hardware(
            self,
            host_ip: str,
            config: dict | None = None,
            reconnect: bool = False,
            **kwargs) -> None:
        """
        Connects to the hardware backend at the given address.

        For the QuaBackend this creates a QuantumMachinesManager and opens a
        quantum machine. Other backends may not require a connection step.

        Args:
            host_ip (str): Address of the hardware (IP for OPX)
            config (dict): Hardware config dictionary to use. Defaults to
                None, in which case the config from the device is used. If
                given, overwrites the device config.
            reconnect (bool): Whether to reconnect (keeps manager alive).
            **kwargs: Backend-specific keyword arguments
        """
        if config is not None:
            if not isinstance(config, dict):
                raise ValueError(
                    "config must be a dictionary, not a string")
            self.device.config = copy.deepcopy(config)
        self.backend.connect(
            host_ip, self.device.config, reconnect=reconnect, **kwargs)

    def connect_opx(self, host_ip: str, qm_config: dict | None = None,
                    reconnect: bool = False, **kwargs) -> None:
        """Backwards-compatible alias for connect_hardware()."""
        self.connect_hardware(host_ip, config=qm_config,
                             reconnect=reconnect, **kwargs)

    def reconnect_hardware(
            self, host_ip: str | None = None, config: dict = None) -> None:
        """
        Reconnects to the hardware, closing any previous connection.

        Args:
            host_ip (str): Address of the hardware. If None, reuses last.
            config (dict): Hardware config override. Defaults to device config.
        """
        if host_ip is None:
            if self.host_ip is None:
                raise AttributeError(
                    "No hardware connected. Run 'connect_hardware' first")
            host_ip = self.host_ip
        self.backend.disconnect()
        self.connect_hardware(host_ip, config, reconnect=True)

    def reconnect_opx(
            self, host_ip: str | None = None, qm_config: dict = None) -> None:
        """Backwards-compatible alias for reconnect_hardware()."""
        self.reconnect_hardware(host_ip, config=qm_config)

    # ──────────────────────────────────────────────────────────────────────
    # Program execution (delegated to backend)
    # ──────────────────────────────────────────────────────────────────────

    def add_measurement(self, new_measurement: Measurement):
        """
        Adds a class which inherits `Measurement` to the program and adds it
        as a QCoDeS sub-module

        Args:
            new_measurement (Measurement): The instance which inherits
            Measurement to be added
        """
        self._measurements.append(new_measurement)

    def run(self, program, **kwargs):
        """
        Sends the compiled program for execution on the hardware backend.

        Args:
            program: Compiled program handle
            **kwargs: Backend-specific execution arguments
        """
        self.backend.run(program, **kwargs)

    def print_program_to_file(
            self,
            path: str,
            program,
            add_config: bool = False
            ) -> None:
        """
        Creates file with 'filename' and prints the program script to this file.

        Args:
            path (str): File path of target file
            program: Compiled program handle
            add_config (bool): Whether config is added to output file
        """
        config = self.device.config if (self.device is not None and add_config) else {}
        with open(path, 'w', encoding="utf-8") as file:
            file.write(self.backend.generate_program_script(program, config))

    def print_qua_program_to_file(
            self, path: str, qua_program, add_config: bool = False) -> None:
        """Backwards-compatible alias for print_program_to_file()."""
        self.print_program_to_file(path, qua_program, add_config)

    def get_idn(self):
        """
        Overload the get_idn method as we don't have one.
        """
        return None

    def ask_raw(self, cmd: str) -> str:
        """Abstract method from qcodes Instrument"""
        raise NotImplementedError

    def write_raw(self, cmd: str) -> None:
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
            sequence_config = self.device.param_config
            )
        if qc_measurement_name is None:
            qc_measurement_name = experiment.name
        measurement.qc_experiment = load_or_create_experiment(
            experiment.name, self.device.name)
        measurement.qc_measurement_name = qc_measurement_name
        sub_sequences = experiment.get_sequences_config(self.device)
        measurement.add_subsequences_from_dict(sub_sequences)
        return measurement

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
        if sql_run is None:
            raise LookupError(
                f"No SqlRun found for run-ID: {run_id}"
            )
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
