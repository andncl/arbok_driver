"""Base class for measurement runners."""
from __future__ import annotations
from typing import TYPE_CHECKING
from abc import ABC, abstractmethod
import logging
import copy
import time
import warnings

import numpy as np
from rich.progress import Progress
import xarray as xr

from arbok_driver.sweep import Sweep

if TYPE_CHECKING:
    from arbok_driver.measurement import Measurement
    from arbok_driver.measurement_runners.parameters.sequence_parameter import SequenceParameter

class MeasurementRunnerBase(ABC):
    """
    Helper class constructing QCoDeS measurement loops
    """

    def __init__(
        self,
        measurement: Measurement,
        ext_sweep_list: list[dict[SequenceParameter, np.ndarray]] | None = None,
        register_all: bool = True
        ):
        self.measurement = measurement
        self.arbok_driver = measurement.driver
        self.ext_sweep_list = ext_sweep_list
        self.external_param_values = self._get_external_params(
            self.ext_sweep_list, register_all)

        self.nr_total_batches = self._calculate_nr_total_batches()
        self.inner_func = None
        self.progress_tracker: Progress | None = None
        self.progress_bars = {}
        self.batch_count = 0

        self.opx_dims, self.opx_coords, self.opx_units = \
            generate_dims_and_coords(self.measurement.sweeps)

        self.ext_dims, self.ext_coords, self.ext_units = \
            generate_dims_and_coords(self.ext_sweep_list) if self.ext_sweep_list is not None else ([], {}, {})

        self.dims = self.ext_dims + self.opx_dims
        self.coords = {**self.ext_coords, **self.opx_coords}
        self.units = {**self.ext_units, **self.opx_units}

    @abstractmethod
    def _prepare_measurement(self) -> None:
        """
        Prepare the measurement for running. E.g creating entry in database
        """
        pass

    @abstractmethod
    def _save_results(self, results_xr: xr.Dataset) -> None:
        """
        Save the results of the measurement. E.g. storing data in the database
        """
        pass

    @abstractmethod
    def _handle_keyboard_interrupt(self) -> None:
        """
        Handle keyboard interrupt during the measurement.
        """
        pass

    @abstractmethod
    def _wrap_up_measurement(self) -> None:
        """
        Wrap up the measurement after completion.
        """
        pass

    def run_arbok_measurement(self, inner_func: callable = None) -> None:
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
        self._prepare_measurement()
        try:
            logging.debug("Running measurement with %s", self.measurement.name)
            self.batch_count = 0
            with Progress() as self.progress_tracker:
                self._create_progress_bars()
                self._run_measurement()
        except KeyboardInterrupt:
            logging.debug("Measurement interrupted by user.")
            print("Measurement interrupted by user.")
            self._handle_keyboard_interrupt()
        self._wrap_up_measurement()

    def _run_measurement(self):
        """
        Builds a native measurement object for the measurement.
        """
        self._create_recursive_measurement_loop(self.ext_sweep_list)
        print("Measurement finished!")

    def _create_recursive_measurement_loop(
            self,
            ext_sweep_list: list[dict[SequenceParameter, np.ndarray]],
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
            batch_coords = {}
            for param, value in self.external_param_values.items():
                dim = self.ext_coords[param.register_name][0]
                batch_coords[param.register_name] = (dim, np.array([value]))
            results_dict = self.measurement.fetch_all_results()
            results_xr = xr.Dataset(coords = batch_coords)
            for gettable, values in results_dict.items():
                dims, coords = gettable.get_full_dims_and_coords(
                    self.ext_dims, batch_coords)
                result_xr = xr.DataArray(
                    data = self._bring_result_to_shape(values),
                    dims = dims,
                    coords = coords
                    )
                results_xr[gettable.register_name] = result_xr
            self.latest_xr_batch = results_xr
            self._save_results(results_xr)
            self.batch_count += 1
            self.update_total_progress_bar()
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
                if param in self.external_param_values:
                    self.external_param_values[param] = value
            self._create_recursive_measurement_loop(
                ext_sweep_list=ext_sweep_list)

    def _calculate_nr_total_batches(self) -> int:
        """
        Calculates the total number of batches for the measurement.

        Returns:
            int: The total number of batches.
        """
        if self.ext_sweep_list is not None:
            ext_sweep_lengths = [
                len(next(iter(dic.values()))) for dic in self.ext_sweep_list]
            return int(np.prod(ext_sweep_lengths))
        else:
            self.ext_sweep_list = []
            warnings.warn(
                "NO sweeps outside the OPX registerd. Thus the measurement only"
                " fills the buffer once and finishes "
                "(e.g only lower progres bar)")
            return 1

    def _create_progress_bars(self) -> None:
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

    def _get_external_params(
            self,
            ext_sweep_list: list[dict[SequenceParameter, np.ndarray]] | None,
            register_all: bool
            ) -> dict[SequenceParameter, float | None]:
        """
        Generates a list of external sweep parameters from the ext_sweep_list.
        Args:
            ext_sweep_list (list[dict]): List of dictionaries containing the sweep
                parameters.
        Returns:
            ext_params (list): List of external sweep parameters.
        """
        if ext_sweep_list is None:
            self.ext_sweep_list = []
        else:
            self.ext_sweep_list = ext_sweep_list
        ext_param_values = {}
        for i, sweep_dict in enumerate(self.ext_sweep_list):
            for j, param in enumerate(sweep_dict.keys()):
                if j == 0 or register_all:
                    ext_param_values[param] = None
                else:
                    logging.debug(
                        "Not adding settable %s on axis %s", param.name, i)
        return ext_param_values
    
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

def generate_dims_and_coords(
        sweeps: list[dict[str, np.ndarray]] | list[Sweep]
    ) -> tuple[
        list[str],
        dict[str, tuple[str, list]],
        dict[str, str]
        ]:
    dims = []
    coords = {}
    units = {}
    for sweep in sweeps:
        if isinstance(sweep, Sweep):
            sweep = sweep.config
        for i, (parameter, array) in enumerate(sweep.items()):
            if i == 0:
                dims.append(parameter.register_name)
            coords[parameter.register_name] = (dims[-1], array)
            units[parameter.register_name] = parameter.unit
    return  dims, coords, units
