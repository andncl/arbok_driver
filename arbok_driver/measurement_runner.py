"""Module containing the MeasurementRunner class."""
import logging
from .measurement import Measurement

class MeasurementRunner:
    """
    Helper class constructing QCoDeS measurement loops
    """

    def __init__(
        self,
        measurement: Measurement,
        sweep_list: list[dict],
        register_all: bool = False
        ):

        self.measurement = measurement
        self.qc_measurement  = measurement.qc_measurement
        self.sweep_list = sweep_list

        self.result_args_dict = self._get_result_arguments(register_all)
        self._prepare_params_and_gettables()
        
        sweep_lengths = [len(next(iter(dic.values()))) for dic in sweep_list]
        self.nr_total_results =  np.prod(sweep_lengths)

    def run_arbok_measurement(self, inner_func: callable):
        """
        Runs the measurement with the given inner function.
        
        Args:
            inner_func (callable): The function to be executed for each measurement
                point. It should accept the datasaver and the current sweep values
                as arguments.
        """
        logging.debug("Creating measurement loop")
        
        # Register parameters in the measurement
        for param, _ in self.result_args_dict.items():
            logging.debug("Registering sequence parameter %s", param.full_name)
            self.qc_measurement.register_parameter(param)

        # Register gettables in the measurement
        gettable_setpoints = self.result_args_dict.keys()
        for gettable in self.measurement.gettables:
            logging.debug("Registering gettable %s", gettable_setpoints)
            self.qc_measurement.register_parameter(
                gettable, setpoints=gettable_setpoints)

        # Run the measurement with the recursive measurement loop
        with self.qc_measurement.run() as datasaver:
            self._create_recursive_measurement_loop(
                datasaver=datasaver,
                inner_function=inner_func,
                **self.result_args_dict
            )
            print("Measurement finished!")
        
        return datasaver.dataset
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
        for i, sweep_dict in enumerate(sweep_list):
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

        for gettable in self.measurement.gettables:
            gettable_setpoints = self.result_args_dict.keys()
            logging.debug("Registering gettable %s", gettable_setpoints)
            self.qc_measurement.register_parameter(
                gettable, setpoints = gettable_setpoints)