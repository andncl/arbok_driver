""" Helper tools for running and measuring OPX programs"""
import copy
import logging

from qcodes.dataset import Measurement
from qcodes.parameters import Parameter
from qcodes.dataset.descriptions.detect_shapes import detect_shape_of_measurement

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

def run_qdac_sweep_with_opx_program(
    program: Program,
    measurement: Measurement,
    ext_settables: dict(),
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
    if not hasattr(program, 'iteration'):
        program.add_parameter(
            'iteration', initial_value = 0, get_cmd = None, set_cmd = None)

    measurement.register_parameter(program.iteration)
    gettable_setpoints = [program.iteration]
    for ext_settable, values in ext_settables.items():
        logging.debug("Registering parameter: %s with value %s",
                      ext_settable.name, values)
        measurement.register_parameter(ext_settable)
        gettable_setpoints.append(ext_settable)
    for gettable in program.gettables:
        logging.debug("Registering gettable: %s",
                      gettable.name)
        measurement.register_parameter(gettable, setpoints = gettable_setpoints)

    with measurement.run() as datasaver:
        for v1 in ext_settables.values()[0]:
            ext_settables.items[1].set(v1)
            for v2 in ext_settables.values()[1]:
                ext_settables.items[1].set(v2)
                for shot in range(shots):
                    program.iteration.set(shot)
                    result_args = [(program.iteration, program.iteration.get())]
                    result_args.append(ext_settables.items[0], v1)
                    result_args.append(ext_settables.items[1], v2)
                    for gettable in program.gettables:
                        result_args.append((gettable, gettable.get_raw(),))
                    datasaver.add_result(*result_args)
        dataset = datasaver.dataset
    return dataset

def run_qdac_measurement_from_opx_program(
    program: Program,
    measurement: Measurement,
    ext_settables: list[dict],
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
    def create_recursive_measurement_loop(ext_settables, result_args_temp):
        """
        Recursive generation of parameter sweeps for all axis given in dict
        ext_settables
        """
        result_args_temp = copy.copy(result_args_temp)
        if not ext_settables:
            # Innermost step: adding results of gettables and independent params
            for gettable in program.gettables:
                result_args_temp.append((gettable, gettable.get_raw(),))
            datasaver.add_result(*result_args_temp)
            return
        else:
            settables = copy.copy(ext_settables)
            sweep_data = (k := next(iter(settables)), settables.pop(k))
            param, sweep_list = sweep_data
            result_args_temp.append(None)
            for value in sweep_list:
                logging.debug('Setting %s to %s', param.instrument.name, value)
                param.set(value)
                result_args_temp[-1] = (param, value)
                create_recursive_measurement_loop(settables, result_args_temp)

    gettable_setpoints = []
    steps = []
    for ext_settable, values in ext_settables.items():
        print(ext_settable.name, values)
        measurement.register_parameter(ext_settable)
        print("register settable ", ext_settable)
        gettable_setpoints.append(ext_settable)
        steps.append(len(values))
    for gettable in program.gettables:
        print("SETPOINTS ", gettable_setpoints)
        measurement.register_parameter(gettable, setpoints = gettable_setpoints)
    print('STEPS! ', steps)

    with measurement.run() as datasaver:
        result_args = []#(program.iteration, program.iteration.get())]
        create_recursive_measurement_loop(ext_settables, result_args)
        dataset = datasaver.dataset
    return dataset