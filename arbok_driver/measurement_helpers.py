""" Helper tools for running and measuring OPX sequences"""
import copy
import time
import logging

import numpy as np
from rich.progress import Progress
from qcodes.dataset import Measurement
from qcodes.dataset.measurements import Runner

def create_measurement_loop(
    sequence,
    measurement: Measurement,
    sweep_list: list[dict],
    register_all: bool = False,
    ):
    """
    Decorator to create a measurement loop for a given measurement. Registers
    all measurement parameters and creates the measurement loops recuresively.
    The OPX measurement can be regarded as the innermost loops of the
    measurement. However the OPX returns all results it measures in the loops in
    the qua measurement in one batch. Therefore in QCoDeS logic a get() on the
    OPX is a single shot measurement. The result is saved on a
    `qcodes.ParameterWithSetpoints` (Matrix with coordinates).

    Loops in the sense of QCoDeS are only added when we sweep parameters outside
    the OPX (e.g) DC voltages LO frequency etc.

    Those loops are added by providing a sweep list. Each entry of dict creates
    a new sweep axis. Parameters (keys) and their setpoints (values ) in the
    respective sweep dict are swept concurrently.

    Args:
        sequence (arbok_driver.Sequence) : The OPX measurement sequence
        measurement (qcodes.Measurement): QCoDeS measurement to run
        sweep list (list[dict[arbok_driver.SequenceParameter, numpy.array]]):
            list configuring the sweep axes and the parameters and setpoints
        register_all (bool, optional): Whether all concurrently swept parameters
            are registered in the measurement. Breaks live plotting.
            Defaults to False

    Returns:
        qcodes.Dataset: Dataset of the measurement
    """
    logging.debug("Creating measurement loop")
    sweep_lengths = [len(next(iter(dic.values()))) for dic in sweep_list]
    nr_sweep_list_points = np.prod(sweep_lengths)
    def decorator(func):
        """Decorator to be returned"""
        def wrapper(*args, **kwargs):
            """Wrapper function with arguments"""
            ### Firstly, all settables are extracted from the sweep dict and the
            ### results arguments are created. Those will used for `add_result`
            result_args_dict = _get_result_arguments(sweep_list, register_all)

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

            ### The measurement is run with the recursive measurement loop over
            ### the qcodes (non-opx) parameters
            with measurement.run() as datasaver:
                ### Measurement loops are generated recursively
                with Progress() as progress_tracker:
                    progress_bars = {}

                    progress_bars['total_progress'] = progress_tracker.add_task(
                        description = "[green]Total progress...",
                        total = nr_sweep_list_points)
                    progress_bars['batch_progress'] = progress_tracker.add_task(
                        description = "[cyan]Batch progress...",
                        total = sequence.sweep_size)
                    _create_recursive_measurement_loop(
                        sequence = sequence,
                        datasaver = datasaver,
                        sweeps_list_temp = sweep_list,
                        res_args_dict= result_args_dict,
                        inner_function=func,
                        progress_bars = progress_bars,
                        progress_tracker = progress_tracker,
                        **kwargs
                        )
                    print("Measurement finished!")
                dataset = datasaver.dataset
            return dataset
        return wrapper
    return decorator

def run_arbok_measurement(
    sequence,
    measurement: Measurement,
    sweep_list: list[dict],
    register_all: bool = False,
    ):
    """
    Function calling the decorator `create_measurement_loop` without a function
    """
    filled_decorator = create_measurement_loop(
        sequence = sequence,
        measurement = measurement,
        sweep_list = sweep_list,
        register_all = register_all
        )

    @filled_decorator
    def dummy_function():
        pass
    dataset = dummy_function()
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
        for j, param in enumerate(list(sweep_dict.keys())):
            if j == 0 or register_all:
                result_args_dict[param] = ()
                gettable_setpoints.append(param)
            else:
                logging.debug(
                    "Not adding settable %s on axis %s", param.name, i)
    return result_args_dict

def _create_recursive_measurement_loop(
        sequence,
        datasaver: Runner,
        sweeps_list_temp: list,
        res_args_dict: dict,
        progress_bars: list,
        progress_tracker: any,
        *args: any,
        inner_function = None,
        **kwargs: any
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
        ### If an inner_function is given it is executed HERE
        if inner_function is not None:
            logging.debug("calling inner function")
            inner_function(*args, **kwargs)

        ### Program is resumed and all gettables are fetched when ready
        if not sequence.driver.is_dummy:
            sequence.driver.qm_job.resume()
        logging.debug("Job resumed, Fetching gettables")
        result_args_temp = []
        for gettable in sequence.gettables:
            result_args_temp.append(
                (
                    gettable,
                    gettable.get_raw(
                        progress_bar = (
                            progress_bars['batch_progress'], progress_tracker,
                        )
                    )
                )
            )

        ### Retreived results are added to the datasaver
        result_args_temp += list(res_args_dict.values())
        datasaver.add_result(*result_args_temp)
        progress_tracker.update(progress_bars['total_progress'], advance=1)
        progress_tracker.refresh()
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
            if param in res_args_dict:
                res_args_dict[param] = (param, value)
            else:
                logging.debug( "Param %s on %s not registered",
                    param.instrument, param.name)
        _create_recursive_measurement_loop(
                *args,
                sequence = sequence,
                datasaver = datasaver,
                sweeps_list_temp = sweeps_list_temp,
                res_args_dict = res_args_dict,
                inner_function = inner_function,
                progress_bars = progress_bars,
                progress_tracker = progress_tracker,
                **kwargs
                )
