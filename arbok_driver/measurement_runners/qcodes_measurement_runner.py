"""Module containing the MeasurementRunner class."""
from __future__ import annotations
from typing import TYPE_CHECKING
from datetime import datetime
import logging
import os
from pathlib import Path

import qcodes
from qm import generate_qua_script
import numpy as np
# from qcodes.dataset.experiment_container import get_DB_location
from qcodes.dataset.sqlite.database import get_DB_location

from .measurement_runner_base import MeasurementRunnerBase

if TYPE_CHECKING:
    from arbok_driver.measurement import Measurement
    from arbok_driver.sequence_parameter import SequenceParameter
    from qm.program import Program
    from qcodes.dataset.data_set import DataSet as QcDataSet
    from qcodes.dataset.measurements import Measurement as QcMeasurement

class QCodesMeasurementRunner(MeasurementRunnerBase):
    """
    Helper class constructing QCoDeS measurement loops
    """

    def __init__(
        self,
        measurement: Measurement,
        ext_sweep_list: list[dict[SequenceParameter, np.ndarray]] | None = None,
        register_all: bool = False
        ):
        # TODO: overwork self.ext_result_args_dict, this can probably made redundant
        super().__init__(
            measurement=measurement,
            ext_sweep_list=ext_sweep_list,
        )
        self.qc_measurement  = measurement.get_qc_measurement()
        self.ext_result_args_dict = self._get_result_arguments(register_all)

        self.datasaver: QcMeasurement | None = None
        self.qc_dataset: QcDataSet | None = None

    def _prepare_measurement(self) -> None:
        """
        Prepare the measurement for running.
            1) preparing parameters and gettables
            2) auto saving qua program
        """
        self._prepare_params_and_gettables()
        self._auto_save_qua_program()

    def _handle_keyboard_interrupt(self) -> None:
        pass

    def _wrap_up_measurement(self) -> None:
        """
        Wrap up the measurement after running.
            1) Fetches data as xarray dataset
            2) Sets the run id in the measurement
            3) Saves the QUA program as metadata to qcodes dataset
        """
        self.qc_dataset = self.datasaver.dataset
        self.measurement._set_dataset(self.qc_dataset.to_xarray_dataset())
        self.run_id = self.qc_dataset.run_id
        self.measurement._set_run_id(self.run_id)
        self._save_qua_program_as_metadata(
            self.measurement.qua_program,
            self.measurement.driver.device.config
            )

    def _run_measurement(self) -> QcMeasurement:
        """
        Builds the QCoDeS measurement object for the measurement.
        """
        with self.qc_measurement.run() as datasaver:
            self.datasaver = datasaver
            self._create_recursive_measurement_loop(self.ext_sweep_list)
            print("Measurement finished!")
        return datasaver

    def _save_results(self):
        """
        Saves the results of the measurement to the datasaver.
        
        Args:
            datasaver (DataSaver): The QCoDeS DataSaver object to save results to.
        """
        result_args_temp: list[tuple] = []
        for _, gettable in self.measurement.gettables.items():
            result = gettable.fetch_results()
            result_args_temp.append(
                (gettable, result)
            )
        ### Retreived results are added to the datasaver
        for param_name, param in self.ext_params.items():
            value = self.temp_batch_coordinates[param_name][1][0]
            result_args_temp.append((param, value))
        self.datasaver.add_result(*result_args_temp)
        logging.debug("Results saved")

    def _get_result_arguments(self, register_all: bool = False) -> dict:
        """
        Generates a dict of parameters that are varied in the sweeps.
        The dict will be used to register the results in the measurement.
        
        Args:
            register_all (bool): If True, all settables will be registered in the
                measurement. If False, only the first settable of each axis will be
                registered
        Returns:
            ext_result_args_dict (dict): Dict with parameters as keys and tuples of
                (parameter, value) as values. The tuples will be used for
                `add_result` in the measurement
        """
        gettable_setpoints = []
        ext_result_args_dict = {}
        for i, sweep_dict in enumerate(self.ext_sweep_list):
            for j, param in enumerate(list(sweep_dict.keys())):
                if j == 0 or register_all:
                    ext_result_args_dict[param] = ()
                    gettable_setpoints.append(param)
                else:
                    logging.debug(
                        "Not adding settable %s on axis %s", param.name, i)
        return ext_result_args_dict

    def _prepare_params_and_gettables(self):
        """
        Prepare parameters and gettables for the measurement.
        """
        for param, _ in self.ext_result_args_dict.items():
            logging.debug(
                "Registering sequence parameter %s", param.full_name)
            self.qc_measurement.register_parameter(param)

        for _, gettable in self.measurement.gettables.items():
            gettable_setpoints = list(self.ext_result_args_dict.keys())
            logging.debug("Registering gettable %s", gettable_setpoints)
            self.qc_measurement.register_parameter(
                gettable, setpoints = gettable_setpoints)

    def _auto_save_qua_program(self) -> None:
        """
        Automatically saves the QUA program in a folder next to the database
        if the folder 'qua_programs' does not exist it is created
        """
        print("Auto saving qua program next to database in './qua_programs/'")
        qua_program = self.measurement.qua_program
        db_path = os.path.abspath(get_DB_location())
        db_dir = os.path.dirname(db_path)
        programs_dir = Path(db_dir) / "qua_programs/"
        if not os.path.isdir(programs_dir):
            os.makedirs(programs_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        measurement_name = self.measurement.qc_measurement_name
        save_path = programs_dir / f"{timestamp}__{measurement_name}.py"
        opx_config = self.measurement.driver.device.config
        with open(save_path, 'w', encoding="utf-8") as file:
            file.write(
                generate_qua_script(qua_program, opx_config))

    def _save_qua_program_as_metadata(
            self,
            qua_program: Program,
            opx_config: dict) -> None:
        """
        Saves the QUA program as metadata in the dataset.
        """
        if self.qc_dataset is not None:
            self.qc_dataset.add_metadata(
                "qua_program",
                generate_qua_script(qua_program, opx_config)
                )
        else:
            raise ValueError(
                "Dataset is not available yet for saving QUA program metadata."
                " Run measurement first."
                )