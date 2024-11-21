from typing import Union, Optional
import logging
import math

from qm import qua

from arbok_driver import SubSequence, SequenceParameter

def arbok_go(
        sub_sequence: SubSequence,
        elements: list,
        to_volt: str | list,
        operation: str,
        from_volt: Optional[Union[str, list]] = None,
        duration: any = None,
        align_after: str = 'elements',
        no_play_tolerance: float = 1e-6
    ):
    """ 
    Helper function that `play`s a qua operation on the respective elements 
    specified in the sequence config.
    TODO:   - [ ] raise error when target and origin dims dont match
            - [ ] raise error if duration is too short
            - [ ] separate this functions into digestible parts

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
        no_play_tolerance (optional, float): tolerance for not playing a pulse
    """
    if isinstance(duration, SequenceParameter):
        duration = duration()

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
    _qua_align(
        method=align_after,
        elements = elements,
        sub_sequence = sub_sequence
        )
    for element in elements:
        sticky_pulse_amplitude = _calculate_sticky_pulse_amplitude(
            target_param_sets[element],
            origin_param_sets[element],
            to_volt_signs,
            from_volt_signs
        )
        kwargs = {
            'pulse': operation*qua.amp(sticky_pulse_amplitude),
            'element': element
            }
        if duration is not None:
            kwargs['duration'] = duration

        logging.debug(
            "Arbok_go: Moving %s from %s to %s by %s in %s", 
            element, from_volt, to_volt, sticky_pulse_amplitude, sub_sequence
            )
        if not isinstance(sticky_pulse_amplitude, float):
            qua.play(**kwargs)
        elif math.isclose(sticky_pulse_amplitude, 0, abs_tol= no_play_tolerance):
            logging.debug(
                "Arbok_go: Omitting %s since amplitude %s is small (th = %s)", 
                element, sticky_pulse_amplitude, no_play_tolerance
                )
        else:
            qua.play(**kwargs)

    _qua_align(
        method=align_after,
        elements = elements,
        sub_sequence = sub_sequence
        )

def _calculate_sticky_pulse_amplitude(
        target_points: dict,
        origin_points: dict,
        to_volt_signs: dict,
        from_volt_signs: dict
        ) -> float:
    """
    Calculates the amplitude of the sticky pulse to be played. Target and origin
    can have multiple points. The amplitude is calculated as the difference

    Args
        element (str): qua element on which pulse is played
        target_points (dict): dict containing the target points as keys
            and their params (either values or qua variables) as values
        origin_points (dict): dict containing the origin points as keys
            and their params (either values or qua variables) as values
        to_volt_signs (dict): dict containing the target points as keys and
            their signs as values
        from_volt_signs (dict): dict containing the origin points as keys and
            their signs as values
    Returns:
        float | any: amplitude of the sticky pulse in qm units (note real volts)
    """
    target_v, origin_v = 0, 0
    for point, param in target_points.items():
        target_v += param()*(to_volt_signs[point])
    for point, param in origin_points.items():
        origin_v += param()*(from_volt_signs[point])


    return target_v - origin_v

def _qua_align(method, elements, sub_sequence):
    match method:
        case "elements":
            qua.align(*elements)
        case 'none':
            pass
        case 'global':
            qua.align()
        case 'sequence':
            qua.align(*sub_sequence.elements)
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

def reset_elements(
        element_list: list,
        sub_sequence: any,
        align_method: str = 'sequence',
        ) -> None:
    """runs `ramp_to_zero` on all element in the given list"""
    for element_name in element_list:
        qua.ramp_to_zero(element_name)
    _qua_align(
        method=align_method,
        elements=element_list,
        sub_sequence=sub_sequence
        )
