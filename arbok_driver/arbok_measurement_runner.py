"""Module containing the MeasurementRunner class."""
from __future__ import annotations
from typing import TYPE_CHECKING
import logging
import copy
import time
import warnings
import uuid
import io
import json

import numpy as np
from rich.progress import Progress
import xarray as xr
from sqlalchemy.orm import Session
from qm import generate_qua_script

from .sweep import Sweep
from .sqlalchemy_classes import SqlRun

if TYPE_CHECKING:
    from arbok_driver import Measurement

class ArbokMeasurementRunner:
    """
    Helper class constructing QCoDeS measurement loops
    """

    def __init__(
        self,
        measurement: Measurement,
        ext_sweep_list: list[dict] | None = None,
        ):
        self.measurement = measurement
        self.arbok_driver = measurement.driver
        self.arbok_driver.check_db_engine_and_bucket_connected()
        self.ext_sweep_list = ext_sweep_list

        self.opx_dims, self.opx_coords, self.opx_units = generate_dims_and_coords(
            self.measurement.sweeps)
        self.ext_dims, self.ext_coords, self.ext_units = generate_dims_and_coords(
            self.ext_sweep_list) if self.ext_sweep_list is not None else ([], {}, {})
        self.dims = self.ext_dims + self.opx_dims
        self.coords = {**self.ext_coords, **self.opx_coords}
        self.units = {**self.ext_units, **self.opx_units}

        self.nr_total_batches = self._calculate_nr_total_batches()
        self.inner_func = None
        self.progress_tracker = None
        self.progress_bars = {}
        self.batch_count = 0

        sql_run = None
        self.minio_data_store = None
        self.bucket_entry_name = None

        ### Coordinate register to correcltly index incoming opx batches
        ### OPX coords are always the same for each batch
        ### External coords change with each batch
        self.temp_batch_coordinates = {
            p: (dim, None) for p, (dim, _) in self.ext_coords.items()}
        self.temp_batch_coordinates.update(self.opx_coords)

    def run_arbok_measurement(self, inner_func: callable = None):
        """
        Runs the measurement with the given inner function.
        
        Args:
            inner_func (callable): The function to be executed for each measurement
                point. It should accept the datasaver and the current sweep values
                as arguments.
        Returns:
            dataset (Dataset): The QCoDeS dataset containing the measurement results.
        """
        logging.debug("Preparing params and gettables for measurement")
        self.inner_func = inner_func
        try:
            logging.debug("Running measurement with %s", self.measurement.name)
            self._run_measurement()
        except KeyboardInterrupt:
            logging.debug("Measurement interrupted by user.")
            print("Measurement interrupted by user.")
            return

    def _run_measurement(self):
        """
        Builds a native measurement object for the measurement.
        """
        self.batch_count = 0
        self.add_run_row_to_database()
        self._save_qua_program_as_metadata()
        self._save_qcodes_snapshot_as_metadata()
        with Progress() as self.progress_tracker:
            self.create_progress_bars()
            self._create_recursive_measurement_loop(
                self.ext_sweep_list)
        print("Measurement finished!")

    def _create_recursive_measurement_loop(
            self,
            ext_sweep_list: list[dict],
            ):
        """
        Creates a recursive measurement loop over the ext_sweep_list.

        Args:
            ext_sweep_list (list[dict]): List of dictionaries containing the sweep
                parameters.
            datasaver (DataSaver): The QCoDeS DataSaver object to save results to.
        """
        # Copy to avoid modifying the original list
        ext_sweep_list = copy.copy(ext_sweep_list)
        if not ext_sweep_list:
            # If the sweep list is empty, execute the inner function
            if self.inner_func is not None:
                self.inner_func()
            ### Program is resumed and all gettables are fetched when ready
            if not self.measurement.driver.is_mock:
                self.measurement.driver.qm_job.resume()
            time.sleep(0.1)
            logging.debug("Job resumed, Fetching gettables")
            self.measurement.wait_until_result_buffer_full(
                (self.progress_bars['batch_progress'], self.progress_tracker)
            )
            self._save_results()
            return

        ### The first axis will be popped from the list and iterated over
        sweep_dict = ext_sweep_list.pop(0)
        sweep_axis_size = len(list(sweep_dict.values())[0])
        for idx in range(sweep_axis_size):
            ### The parameter values are set for the current iteration
            for param, values in sweep_dict.items():
                value = values[idx]
                logging.debug('Setting %s to %s', param.instrument.name, value)
                param.set(value)
                self.last_updated_dim = param.register_name
                coord_tuple = self.temp_batch_coordinates[param.register_name]
                self.temp_batch_coordinates[param.register_name] = (
                    coord_tuple[0], [value])
            self._create_recursive_measurement_loop(
                ext_sweep_list=ext_sweep_list)

    def _save_results(self):
        """
        Saves the results of the measurement to the datasaver.
        
        Args:
            datasaver (DataSaver): The QCoDeS DataSaver object to save results to.
        """
        dataset = xr.Dataset(
            #dims = self.dims,
            coords = self.temp_batch_coordinates
        )
        for coord_name in dataset.coords:
            dataset[coord_name].attrs['units'] = self.units[coord_name]
        self.debug_ds = dataset
        for _, gettable in self.measurement.gettables.items():
            result_np = gettable.fetch_results()
            result_xr = xr.DataArray(
                data = self.bring_result_to_shape(result_np),
                dims=self.dims,
                coords=self.temp_batch_coordinates
                )
            for coord_name in result_xr.coords:
                result_xr[coord_name].attrs['units'] = self.units[coord_name]
            self.debug_arr = result_xr
            dataset[gettable.register_name] = result_xr
            
            
        self.save_dataset_to_store(dataset)
        self.update_run_row_in_database()
        self.batch_count += 1
        self.update_total_progress_bar()
        logging.debug("Results saved")

    def _calculate_nr_total_batches(self) -> int:
        """
        Calculates the total number of batches for the measurement.

        Returns:
            int: The total number of batches.
        """
        if self.ext_sweep_list is not None:
            ext_sweep_lengths = [
                len(next(iter(dic.values()))) for dic in self.ext_sweep_list]
            return np.prod(ext_sweep_lengths)
        else:
            self.ext_sweep_list = []
            warnings.warn(
                "NO sweeps outside the OPX registerd. Thus the measurement only"
                " fills the buffer once and finishes "
                "(e.g only lower progres bar)")
            return 1

    def add_run_row_to_database(self) -> None:
        """
        Adds a new run row to the database for the current measurement.
        """
        with Session(self.arbok_driver.database_engine) as session:
            sql_run = SqlRun(
                exp_id=1,
                uuid=str(uuid.uuid4()),
                name=self.measurement.qc_measurement_name,
                # device=self.measurement.device.name,
                coords = list(self.coords.keys()),
                sweeps = {}, #self.coords,
                setup='rf2v',
                start_time=time.time(),
            )
            
            session.add(sql_run)
            session.commit()
            self.run_id = int(sql_run.run_id)
            print("Inserted run with ID:", sql_run.run_id)
            self.bucket_entry_name = f"{sql_run.run_id}_{sql_run.uuid}"
            self.minio_data_store = self.arbok_driver.minio_filesystem.get_mapper(
                f"dev/{self.bucket_entry_name}/data.zarr")
            self.minio_metadata_store = self.arbok_driver.minio_filesystem.get_mapper(
                f"dev/{self.bucket_entry_name}/metadata")

    def update_run_row_in_database(self) -> None:
        """
        Updates the run row in the database after each batch.
        """
        with Session(self.arbok_driver.database_engine) as session:
            sql_run = session.get(SqlRun, self.run_id)
            # if self.batch_count + 1 >= self.nr_total_batches:
            if sql_run is None:
                    raise ValueError(
                        f"SqlRun with id={self.run_id} not found at batch {self.batch_count}")
            sql_run.batch_count = self.batch_count + 1
            sql_run.result_count += self.measurement.sweep_size
            session.commit()

    def bring_result_to_shape(self, result: xr.DataArray) -> xr.DataArray:
        """
        Brings the result DataArray to the correct shape to be added to xarray
        dataset. With each batch we add one datapoint for each external
        dimension setpoint. Therefore wrap the result with singleton dimensions
        for each external dimension.

        Args:
            result (xr.DataArray): The result DataArray to be reshaped.

        Returns:
            xr.DataArray: The reshaped DataArray.
        """
        return np.reshape(result, (1,)*len(self.ext_dims) + result.shape)

    def save_dataset_to_store(self, dataset: xr.Dataset) -> None:
        """
        Saves the given dataset to the MinIO store.

        Args:
            dataset (xr.Dataset): The dataset to be saved.
        """
        if self.batch_count > 0:
            dataset.to_zarr(
                self.minio_data_store,
                mode="a",
                append_dim=self.last_updated_dim,
                )
        else:
            dataset.to_zarr(self.minio_data_store, mode='w')

    def create_progress_bars(self) -> None:
        """
        Creates progress bars for the measurement.
        """
        total_progress = self.progress_tracker.add_task(
            description = f"[green]Total progress...\n0/{self.nr_total_batches}",
            total = self.nr_total_batches)
        batch_progress = self.progress_tracker.add_task(
            description = "[cyan]Batch progress...",
            total = self.measurement.sweep_size)
        self.progress_bars['total_progress'] = total_progress
        self.progress_bars['batch_progress'] = batch_progress

    def update_total_progress_bar(self) -> None:
        """
        Updates the total progress bar after each batch.
        """
        title = "[green]Total progress\n "
        self.progress_tracker.update(
            self.progress_bars['total_progress'],
            advance=1,
            description=f"{title}{self.batch_count}/{self.nr_total_batches}"
            )
        self.progress_tracker.refresh()

    def _save_qua_program_as_metadata(self) -> None:
        """
        Saves the QUA program as metadata to the binary bucket.
        """
        program_str = generate_qua_script(
            self.measurement.qua_program,
            self.measurement.device.config
        )
        program_str_binary = io.BytesIO(program_str.encode("utf-8"))
        self.minio_metadata_store["qua_program.py"] = program_str_binary.getvalue()

    def _save_qcodes_snapshot_as_metadata(self) -> None:
        """
        Saves the QCoDeS snapshot as metadata to the binary bucket.
        """
        driver = self.measurement.driver
        if not hasattr(driver, 'station'):
            print("Not saving QCoDeS snapshot, no station found.")
            return
        if driver.station is None:
            
            print("Not saving QCoDeS snapshot, no station found.")
            return
        snapshot_dict = driver.station.snapshot(update=False)
        snapshot_bytes = json.dumps(snapshot_dict, indent=2).encode("utf-8")
        self.minio_metadata_store["qcodes_snapshot.json"] = snapshot_bytes

def generate_dims_and_coords(sweeps) -> tuple[list[str], dict[str, tuple[str, list]]]:
    dims = []
    coords = {}
    units = {}
    for sweep in sweeps:
        if isinstance(sweep, Sweep):
            sweep = sweep.config
        for i, (parameter, array) in enumerate(sweep.items()):
            if i == 0:
                dims.append(parameter.register_name)
            coords[parameter.register_name] = (
                dims[-1], array
            )
            units[parameter.register_name] = parameter.unit
    return dims, coords, units
