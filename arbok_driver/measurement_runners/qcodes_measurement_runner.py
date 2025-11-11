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
        super().__init__(
            measurement=measurement,
            ext_sweep_list=ext_sweep_list,
            register_all=register_all
        )
        self.qc_measurement  = measurement.get_qc_measurement()
        self.datasaver: QcMeasurement | None = None
        self.qc_dataset: QcDataSet | None = None

    def _prepare_measurement(self) -> None:
        """
        Prepare the measurement for running.
            1) preparing parameters and gettables
            2) auto saving qua program
        """
        self._register_params_and_gettables()

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
            self.run_id = self.datasaver.run_id
            self._auto_save_qua_program()
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
        for param, value in self.external_param_values.items():
            result_args_temp.append((param, value))
        self.datasaver.add_result(*result_args_temp)
        logging.debug("Results saved")

    def _register_params_and_gettables(self):
        """
        Register varied parameters and gettables for the measurement.
        """
        for param, _ in self.external_param_values.items():
            logging.debug(
                "Registering sequence parameter %s", param.full_name)
            self.qc_measurement.register_parameter(param)
        for _, gettable in self.measurement.gettables.items():
            logging.debug("Registering gettable %s", gettable.register_name)
            self.qc_measurement.register_parameter(
                gettable, setpoints = list(self.external_param_values.keys()))

    def _auto_save_qua_program(self) -> None:
        """
        Automatically saves the QUA program in a folder next to the database
        if the folder 'qua_programs' does not exist it is created
        """
        print("Auto saving qua program next to database in './qua_programs/'")
        qua_program = self.measurement.qua_program
        db_path = os.path.abspath(get_DB_location())
        db_name = db_path.split('/')[-1].split('.db')[0]
        db_dir = os.path.dirname(db_path)
        programs_dir = Path(db_dir) / f"qua_programs__{db_name}/"
        if not os.path.isdir(programs_dir):
            os.makedirs(programs_dir)
        save_path = programs_dir / f"{self.run_id}.py"
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