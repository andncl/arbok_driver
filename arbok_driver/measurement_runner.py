"""Module containing the MeasurementRunner class."""
import logging
import copy
import time

import numpy as np
from rich.progress import Progress

class MeasurementRunner:
    """
    Helper class constructing QCoDeS measurement loops
    """

    def __init__(
        self,
        measurement: 'Measurement',
        sweep_list: list[dict],
        register_all: bool = False
        ):

        self.measurement = measurement
        self.qc_measurement  = measurement.get_qc_measurement()
        self.sweep_list = sweep_list

        self.result_args_dict = self._get_result_arguments(register_all)

        sweep_lengths = [len(next(iter(dic.values()))) for dic in sweep_list]
        self.nr_total_results =  np.prod(sweep_lengths)
        self.inner_func = None
        self.progress_tracker = None
        self.progress_bars = None
        self.counter = 0

    def run_arbok_measurement(self, inner_func: callable = None) -> "dataset":
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
        self._prepare_params_and_gettables()
        # Run the measurement with the recursive measurement loop
        try:
            logging.debug("Running measurement with %s", self.measurement.name)
            datasaver = self._build_qc_measurement()
        except KeyboardInterrupt:
            logging.warning("Measurement interrupted by user.")
            print("Measurement interrupted by user.")
            return None

        return datasaver.dataset

    def _build_qc_measurement(self):
        """
        Builds the QCoDeS measurement object for the measurement.
        """
        self.counter = 0
        with self.qc_measurement.run() as datasaver:
            with Progress() as self.progress_tracker:
                ### Adding progress bars

                self.progress_bars = {}
                total_progress = self.progress_tracker.add_task(
                    description = "[green]Total progress...",
                    total = self.nr_total_results)
                batch_progress = self.progress_tracker.add_task(
                    description = "[cyan]Batch progress...",
                    total = self.measurement.sweep_size)
                self.progress_bars['total_progress'] = total_progress
                self.progress_bars['batch_progress'] = batch_progress
                self._create_recursive_measurement_loop(
                    self.sweep_list, datasaver)
            print("Measurement finished!")
        return datasaver

    def _create_recursive_measurement_loop(
            self,
            sweep_list: list[dict],
            datasaver
            ):
        """
        Creates a recursive measurement loop over the sweep_list.

        Args:
            sweep_list (list[dict]): List of dictionaries containing the sweep
                parameters.
            datasaver (DataSaver): The QCoDeS DataSaver object to save results to.
        """
        # Copy to avoid modifying the original list
        sweep_list = copy.copy(sweep_list)
        if not sweep_list:
            # If the sweep list is empty, execute the inner function
            if self.inner_func is not None:
                self.inner_func()
            ### Program is resumed and all gettables are fetched when ready
            if not self.measurement.driver.is_mock:
                self.measurement.driver.qm_job.resume()
            time.sleep(1)
            logging.debug("Job resumed, Fetching gettables")
            self.measurement.wait_until_result_buffer_full(
                (self.progress_bars['batch_progress'], self.progress_tracker)
            )
            self._save_results(datasaver)
            return

        ### The first axis will be popped from the list and iterated over
        sweep_dict = sweep_list.pop(0)
        for idx in range(len(list(sweep_dict.values())[0])):
            ### The parameter values are set for the current iteration
            for param, values in sweep_dict.items():
                value = values[idx]
                logging.debug('Setting %s to %s', param.instrument.name, value)
                param.set(value)

                ### The parameter is added to the result arguments dict if its
                ### dict entry is registered
                if param in self.result_args_dict:
                    self.result_args_dict[param] = (param, value)
                else:
                    logging.debug( "Param %s on %s not registered",
                        param.instrument, param.name)
            self._create_recursive_measurement_loop(
                sweep_list = sweep_list,
                datasaver = datasaver,
            )

    def _save_results(self, datasaver):
        """
        Saves the results of the measurement to the datasaver.
        
        Args:
            datasaver (DataSaver): The QCoDeS DataSaver object to save results to.
        """
        self.counter += 1
        result_args_temp = []
        for _, gettable in self.measurement.gettables.items():
            result_args_temp.append(
                (gettable, gettable.fetch_results())
            )
        ### Retreived results are added to the datasaver
        result_args_temp += list(self.result_args_dict.values())
        datasaver.add_result(*result_args_temp)
        title = "[green]Total progress\n "
        self.progress_tracker.update(
            self.progress_bars['total_progress'],
            advance=1,
            description=f"{title}{self.counter}/{self.nr_total_results}"
            )
        self.progress_tracker.refresh()
        logging.debug("Results saved")

    def _get_result_arguments(self, register_all: bool = False) -> dict:
        """
        Generates a list of parameters that are varied in the sweep and a dict
        
        Args:
            register_all (bool): If True, all settables will be registered in the
                measurement. If False, only the first settable of each axis will be
                registered
        Returns:
            result_args_dict (dict): Dict with parameters as keys and tuples of
                (parameter, value) as values. The tuples will be used for
                `add_result` in the measurement
        """
        gettable_setpoints = []
        result_args_dict = {}
        for i, sweep_dict in enumerate(self.sweep_list):
            for j, param in enumerate(list(sweep_dict.keys())):
                if j == 0 or register_all:
                    result_args_dict[param] = ()
                    gettable_setpoints.append(param)
                else:
                    logging.debug(
                        "Not adding settable %s on axis %s", param.name, i)
        return result_args_dict

    def _prepare_params_and_gettables(self):
        """
        Prepare parameters and gettables for the measurement.
        """
        for param, _ in self.result_args_dict.items():
            logging.debug(
                "Registering sequence parameter %s", param.full_name)
            self.qc_measurement.register_parameter(param)

        for _, gettable in self.measurement.gettables.items():
            gettable_setpoints = list(self.result_args_dict.keys())
            logging.debug("Registering gettable %s", gettable_setpoints)
            self.qc_measurement.register_parameter(
                gettable, setpoints = gettable_setpoints)
