from typing import Union, Optional
import logging

from qm.qua import play, amp, ramp_to_zero, align
from qm import qua

from arbok_driver import SubSequence, SequenceParameter

def arbok_go(
        sub_sequence: SubSequence,
        elements: list,
        to_volt: str | list,
        operation: str,
        from_volt: Optional[Union[str, list]] = None,
        duration: any = None,
        align_after: str = 'elements'
    ):
    """ 
    Helper function that `play`s a qua operation on the respective elements 
    specified in the sequence config.
    TODO:   - [ ] raise error when target and origin dims dont match
            - [ ] raise error if duration is too short

    Args:
        sub_sequence (Sequence): Sequence from which parameters are fetched
        elements (list): elements on which pulse is applied
        to_volt (str, List): voltage point to move to
        operation (str): Operation to be played -> find in OPX config
        from_volt (str, List): voltage point to come from
        duration (str | qcodes.Parameter): duration of the operation 
        align_after (optional, bool, str): whether to align channels after
            ramping. Input 'all' alligns all. 'none' does not align 
            at all and 'elements' (default) aligns all given elements
    """
    if isinstance(duration, SequenceParameter):
        if duration.qua_sweeped:
            duration = duration.qua_var
        else:
            duration = int(duration())
    from_volt = _check_voltage_point_input(from_volt)
    to_volt = _check_voltage_point_input(to_volt)
    from_volt_signs = {point: 1 for point in from_volt}
    to_volt_signs = {point: 1 for point in to_volt}

    for i, point in enumerate(from_volt):
        if point[0] == '-':
            from_volt[i] = point[1:]
            from_volt_signs[point[1:]] = -1
    for i, point in enumerate(to_volt):
        if point[0] == '-':
            to_volt[i] = point[1:]
            to_volt_signs[point[1:]] = -1
    origin_param_sets = sub_sequence.find_parameters_from_keywords(
        from_volt,
        elements
        )
    target_param_sets = sub_sequence.find_parameters_from_keywords(
        to_volt,
        elements
        )
    if not set(origin_param_sets.keys()) == set(target_param_sets.keys()):
        raise KeyError(
            "All given voltage points must have the same elements in the conf",
            f"{elements}")
    for element in elements:
        target_v = 0
        origin_v = 0
        for point, param in target_param_sets[element].items():
            target_v += param.get_raw()*to_volt_signs[point]
        for point, param in origin_param_sets[element].items():
            origin_v += param.get_raw()*from_volt_signs[point]
        kwargs = {
            'pulse': operation*qua.amp( target_v - origin_v ),
            'element': element
            }
        if duration is not None:
            kwargs['duration'] = duration
        logging.debug(
            "Arbok_go: Moving %s from %s (%s) to %s (%s) in %s", 
            element, origin_v,
            from_volt, target_v, to_volt, sub_sequence
            )
        qua.play(**kwargs)
    match align_after:
        case "elements":
            qua.align(*elements)
        case 'none':
            pass
        case 'all':
            qua.align()
        case _:
            raise ValueError(
                "Argument for align can only be bool or 'elements'")

def _check_voltage_point_input(points: list | str) -> list:
    """
    Checks if input is of type list or string and returns input as list
    """
    if points is None:
        return ['vHome']
    elif isinstance(points, str):
        return [points]
    elif isinstance(points, list):
        return points
    else:
        raise ValueError("Must be of type str or list!")

def reset_elements(element_list: list) -> None:
    """runs `ramp_to_zero` on all element in the given list"""
    for element_name in element_list:
        qua.ramp_to_zero(element_name)
    qua.align()
