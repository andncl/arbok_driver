""" Helper tools for running and measuring OPX programs"""
import copy
import logging

from qcodes.dataset import Measurement

from arbok_driver import Program

def register_opx_program_qc_params_on_measurement(
    program: Program,
    measurement: Measurement
    ):
    """
    Registeres QCoDeS params describing the given OPX program on the QCoDeS
    measurement object
    
    Args:
        program (Program): arbok_driver Program
        measurement (Measurement): QCoDeS measurement object
    Returns:
        QCoDes measurement object: Measurement with registered parameters
    """
    if not hasattr(program, 'iteration'):
        program.add_parameter(
            'iteration', initial_value = 0, get_cmd = None, set_cmd = None)

    measurement.register_parameter(program.iteration)
    for gettable in program.gettables:
        measurement.register_parameter(
            gettable, setpoints = (program.iteration,) )
    return measurement

def run_qc_measurement_from_opx_program(
    program: Program,
    measurement: Measurement,
    shots: int
    ):
    """ 
    Runs QCoDeS `measurement` based on specified settables and gettables on
    the given opx `program` and and returns the resulting dataset with an
    amount of `shots`
    
    Args:
        program (Program): arbok_driver Program, parameterizing measurement
        measurement (Measurement): qcodes measurement object
        shots (int): amount of repetitions to be performed for averaging  
    Returns:
        dataset: QCoDeS dataset
    """
    register_opx_program_qc_params_on_measurement(program, measurement)
    with measurement.run() as datasaver:
        for shot in range(shots):
            program.iteration.set(shot)
            add_result_args = ((program.iteration, program.iteration.get()),)

            for gettable in program.gettables:
                add_result_args += ((gettable, gettable.get_raw(),),)
            datasaver.add_result(*add_result_args)
        dataset = datasaver.dataset
    return dataset

def run_qdac_measurement_from_opx_program(
    program: Program,
    measurement: Measurement,
    sweep_list: list[dict],
    ):
    """ 
    Runs QCoDeS `measurement` based on specified settables and gettables on
    the given opx `program` and and returns the resulting dataset with an
    amount of `shots`
    
    Args:
        program (Program): arbok_driver Program, parameterizing measurement
        measurement (Measurement): qcodes measurement object
        sweep_list (list[dict]): List of dictionairies with params as keys and
            np.ndarrays as settables. Each list entry creates one sweep axis.
            If you want to sweep params concurrently enter more entries into 
            their sweep dict
    Returns:
        dataset: QCoDeS dataset
    """
    def create_recursive_measurement_loop(sweeps_list_temp, result_args_temp):
        """
        Recursive generation of parameter sweeps for all axis given in dict
        ext_settables
        """
        result_args_temp = copy.copy(result_args_temp)
        if not sweeps_list_temp:
            for gettable in program.gettables:
                result_args_temp.append((gettable, gettable.get_raw(),))
            result_args_temp += list(res_args_dict.values())
            datasaver.add_result(*result_args_temp)
            return
        sweeps_list_temp = copy.copy(sweeps_list_temp)
        sweep_dict = sweeps_list_temp.pop(0)
        for idx in range(len(list(sweep_dict.values())[0])):
            for param, values in sweep_dict.items():
                value = values[idx]
                logging.debug('Setting %s to %s', param.instrument.name, value)
                param.set(value)
                try:
                    _ = res_args_dict[f"{param.instrument}.{param.name}"]
                    res_args_dict[f"{param.instrument}.{param.name}"] = (param, value)
                except KeyError:
                    logging.debug( "Param %s on %s not registered",
                        param.instrument, param.name)
            create_recursive_measurement_loop(
                    sweeps_list_temp, result_args_temp)

    gettable_setpoints = []
    res_args_dict = {}
    for i, sweep_dict in enumerate(sweep_list):
        for i, param in enumerate(list(sweep_dict.keys())):
            if i == 0:
                logging.debug("First param of sweep ax: %s.%s",
                              param.instrument, param.name)
                res_args_dict[f"{param.instrument}.{param.name}"] = ()
                measurement.register_parameter(param)
                gettable_setpoints.append(param)
            logging.debug("Register settable %s on axis %s", param.name, i)

    for gettable in program.gettables:
        logging.debug("Register gettable %s", gettable_setpoints)
        measurement.register_parameter(gettable, setpoints = gettable_setpoints)

    print(measurement.parameters)
    with measurement.run() as datasaver:
        result_args = []
        create_recursive_measurement_loop(sweep_list, result_args)
        dataset = datasaver.dataset
    return dataset
