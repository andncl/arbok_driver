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

from arbok_driver.sweep import Sweep
from arbok_driver.sqlalchemy_classes import SqlRun
from .measurement_runner_base import MeasurementRunnerBase
if TYPE_CHECKING:
    from arbok_driver.measurement import Measurement

class NativeMeasurementRunner(MeasurementRunnerBase):
    """
    Helper class constructing QCoDeS measurement loops
    """

    def __init__(
        self,
        measurement: Measurement,
        ext_sweep_list: list[dict] | None = None,
        ):
        super().__init__(
            measurement=measurement,
            ext_sweep_list=ext_sweep_list,
        )
        self.sql_run: SqlRun | None = None
        self.minio_data_store = None
        self.bucket_entry_name = None

    def _prepare_measurement(self) -> None:
        """
        Prepare the measurement for running. 
            1) creating entry in database
            2) saving qua program as metadata
            3) saving qcodes snapshot as metadata
        """
        self._add_run_row_to_database()
        self._save_qua_program_as_metadata()
        self._save_qcodes_snapshot_as_metadata()

    def _handle_keyboard_interrupt(self) -> None:
        """
        Handle keyboard interrupt during measurement.
        """
        self.measurement._set_dataset(
            self.measurement.driver.get_data_from_id(self.run_id))

    def _wrap_up_measurement(self) -> None:
        """
        Wrap up the measurement after running.
        """
        self.measurement._set_dataset(
            self.measurement.driver.get_data_from_id(self.run_id))

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
                data = self._bring_result_to_shape(result_np),
                dims=self.dims,
                coords=self.temp_batch_coordinates
                )
            for coord_name in result_xr.coords:
                result_xr[coord_name].attrs['units'] = self.units[coord_name]
            self.debug_arr = result_xr
            dataset[gettable.register_name] = result_xr

        self._save_dataset_to_store(dataset)
        self._update_run_row_in_database()
        logging.debug("Results saved")

    def _add_run_row_to_database(self) -> None:
        """
        Adds a new run row to the database for the current measurement.
        """
        with Session(self.arbok_driver.database_engine) as session:
            self.sql_run = SqlRun(
                exp_id=1,
                uuid=str(uuid.uuid4()),
                name=self.measurement.qc_measurement_name,
                # device=self.measurement.device.name,
                coords = list(self.coords.keys()),
                sweeps = {}, #self.coords,
                setup='rf2v',
                start_time=time.time(),
            )
            self.measurement._set_run_id(self.sql_run.run_id)
            session.add(self.sql_run)
            session.commit()
            self.run_id = int(self.sql_run.run_id)
            print("Inserted run with ID:", self.sql_run.run_id)
            self.bucket_entry_name = f"{self.sql_run.run_id}_{self.sql_run.uuid}"
            self.minio_data_store = self.arbok_driver.minio_filesystem.get_mapper(
                f"dev/{self.bucket_entry_name}/data.zarr")
            self.minio_metadata_store = self.arbok_driver.minio_filesystem.get_mapper(
                f"dev/{self.bucket_entry_name}/metadata")

    def _update_run_row_in_database(self) -> None:
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

    def _bring_result_to_shape(self, result: np.ndarray) -> np.ndarray:
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

    def _save_dataset_to_store(self, dataset: xr.Dataset) -> None:
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
