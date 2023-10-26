from typing import Union, Optional
import logging

from qm.qua import play, amp, ramp_to_zero, align

from arbok_driver import SubSequence, SequenceParameter

def arbok_go(
        sub_sequence: SubSequence, 
        to_volt: Union[str, list],
        operation: str,
        from_volt: Optional[Union[str, list]] = None,
        duration: int = None,
        align_elements: bool = True
    ):
    """ 
    Helper function that `play`s a qua operation on the respective elements 
    specified in the sequence config.
    TODO:   - [ ] raise error when target and origin dims dont match
            - [ ] raise error if duration is too short
            - [ ] if target is vHome -> ramp_to_zero (avoids accumulated errors
                from sticky pulses)
    Args:
        seq (Sequence): Sequence
        from_volt (str, List): voltage point to come from
        to_volt (str, List): voltage point to move to
        duration (str): duration of the operation 
        operation (str): Operation to be played -> find in OPX config
        align (optional, bool): whether to align all channels before and after
    """
    if from_volt is None:
        from_volt = ['vHome']
    if isinstance(duration, SequenceParameter):
        if duration.qua_sweeped:
            duration = duration.qua_var
        else:
            duration = int(duration())
    origin_param_sets = sub_sequence.find_parameters_from_keywords(from_volt)
    target_param_sets = sub_sequence.find_parameters_from_keywords(to_volt)
    if len(origin_param_sets) == 0:
        raise AttributeError(f"Couldnt find parameters with name {from_volt}")
    if len(target_param_sets) == 0:
        raise AttributeError(f"Couldnt find parameters with name {to_volt}")
    if align_elements:
        align()
    for target_list, origin_list in zip(target_param_sets, origin_param_sets):
        target_v = sum([par() for par in target_list])
        origin_v = sum([par() for par in origin_list])
        logging.debug(
            "Arbok_go: Moving %s from %s (%s) to %s (%s) in %s", 
            target_list[0].element, origin_v, 
            from_volt, target_v, to_volt, sub_sequence
            )
        kwargs = {
            'pulse': operation*amp( target_v - origin_v ),
            'element': target_list[0].element
            }
        if duration is not None:
            kwargs['duration'] = duration

        play(**kwargs)
    if align_elements:
        align()

def reset_elements(element_list: list) -> None:
    """runs `ramp_to_zero` on all element in the given list"""
    for element_name in element_list:
        ramp_to_zero(element_name)
    align()
