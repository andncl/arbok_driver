""" Helper tools for running and measuring OPX sequences"""
import copy
import logging
import re

from qcodes.dataset import Measurement
from qcodes.dataset.measurements import Runner
from arbok_driver import Program, Sequence

def create_measurement_loop(
    sequence: Sequence,
    measurement: Measurement,
    sweep_list: list[dict],
    register_all: bool = False,
    ):
    """Decorator to create a measurement loop for a given measurement"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            ### Firstly, all settables are extracted from the sweep dict and the
            ### results arguments are created. Those will used for `add_result`
            result_args_dict = _get_result_arguments(sweep_list, register_all)
            print("RES ARGS: ", result_args_dict.keys())
            ### The extracted settables are registered in the measurement
            for param, _ in result_args_dict.items():
                logging.debug(
                    "Registering sequence parameter %s", param.full_name)
                measurement.register_parameter(param)
            ### The gettables are registered in the measurement
            for gettable in sequence.gettables:
                gettable_setpoints = result_args_dict.keys()
                logging.debug("Registering gettable %s", gettable_setpoints)
                measurement.register_parameter(
                    gettable, setpoints = gettable_setpoints)

            print("MEAS PARAMS: ", measurement.parameters.keys())
            ### The measurement is run with the recursive measurement loop over
            ### the qcodes (non-opx) parameters
            with measurement.run() as datasaver:
                _create_recursive_measurement_loop(
                    sequence = sequence,
                    datasaver = datasaver,
                    sweeps_list_temp = sweep_list,
                    res_args_dict= result_args_dict,
                    )
                func(*args, **kwargs)
                dataset = datasaver.dataset
                print("DONE")
            return dataset
        return wrapper
    return decorator

def run_qdac_measurement_from_opx_program(
    sequence: Sequence,
    measurement: Measurement,
    sweep_list: list[dict],
    register_all: bool = False,
    ):
    """ 
    Runs QCoDeS `measurement` based on specified settables and gettables on
    the given opx `sequence` and and returns the resulting dataset with an
    amount of `shots`
    
    Args:
        sequence (Program): arbok_driver Program, parameterizing measurement
        measurement (Measurement): qcodes measurement object
        sweep_list (list[dict]): List of dictionairies with params as keys and
            np.ndarrays as settables. Each list entry creates one sweep axis.
            If you want to sweep params concurrently enter more entries into 
            their sweep dict
    Returns:
        dataset: QCoDeS dataset
    """
    ### Firstly, all settables are extracted from the sweep dict
    ### and the results arguments are created. Those will used for `add_result`
    result_args_dict = _get_result_arguments(sweep_list, register_all)
    print("RES ARGS: ", result_args_dict.keys())
    ### The extracted settables are registered in the measurement
    for param, _ in result_args_dict.items():
        logging.debug("Registering sequence parameter %s", param.full_name)
        measurement.register_parameter(param)
    ### The gettables are registered in the measurement
    for gettable in sequence.gettables:
        gettable_setpoints = result_args_dict.keys()
        logging.debug("Registering gettable %s", gettable_setpoints)
        measurement.register_parameter(gettable, setpoints = gettable_setpoints)

    print("MEAS PARAMS: ", measurement.parameters.keys())
    ### The measurement is run with the recursive measurement loop over the
    ### qcodes (non-opx) parameters
    with measurement.run() as datasaver:
        _create_recursive_measurement_loop(
            sequence = sequence,
            datasaver = datasaver,
            sweeps_list_temp = sweep_list,
            res_args_dict= result_args_dict,
            )
        sequence.program.qm_job.resume()
        dataset = datasaver.dataset
    return dataset


def _get_result_arguments(
        sweep_list: list[dict],
        register_all: bool = False) -> dict:
    """
    Generates a list of parameters that are varied in the sweep and a dict
    
    Args:
        sweep_list (list[dict]): List of dictionairies with params as keys and
            np.ndarrays as settables. Each list entry creates one sweep axis.
            If you want to sweep params concurrently enter more entries into 
            their sweep dict
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
        for i, param in enumerate(list(sweep_dict.keys())):
            if i == 0 or register_all:
                result_args_dict[param] = ()
                gettable_setpoints.append(param)
            else:
                logging.debug(
                    "Not adding settable %s on axis %s", param.name, i)
    return result_args_dict

def _create_recursive_measurement_loop(
        sequence: Sequence,
        datasaver: Runner,
        sweeps_list_temp: list,
        res_args_dict: dict,
        ):
    """
    Recursive generation of parameter sweeps for all axis given in dict
    ext_settables

    Args:
        sweeps_list_temp (list): List of dictionairies of given sweeps
        result_args_temp (list): List of tuples of params their values
    """
    if not sweeps_list_temp:
        ### This is the end of the recursion.
        ### All gettables will be fetched in the following
        logging.debug("Fetching gettables")
        print(sequence.gettables)
        result_args_temp = []
        sequence.program.qm_job.resume()
        for gettable in sequence.gettables:
            result_args_temp.append((gettable, gettable.get_raw(),))
        result_args_temp += list(res_args_dict.values())
        datasaver.add_result(*result_args_temp)
        return
    ### The first axis will be popped from the list and iterated over
    sweeps_list_temp = copy.copy(sweeps_list_temp)
    sweep_dict = sweeps_list_temp.pop(0)
    for idx in range(len(list(sweep_dict.values())[0])):
        ### The parameter values are set for the current iteration
        for param, values in sweep_dict.items():
            value = values[idx]
            logging.debug('Setting %s to %s', param.instrument.name, value)
            param.set(value)
            ### The parameter is added to the result arguments dict if its
            ### dict entry is registered
            try:
                res_args_dict[param] = (param, value)
            except KeyError:
                logging.debug( "Param %s on %s not registered",
                    param.instrument, param.name)
        _create_recursive_measurement_loop(
                sequence, datasaver, sweeps_list_temp, res_args_dict)
