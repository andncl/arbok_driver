from typing import Optional
import logging
import math

from qm import qua

from arbok_driver.parameter_types import ParameterMap, Voltage, Time

def ramp(
        elements: list,
        to_volt: ParameterMap,
        operation: str,
        duration: Time | None = None,
        from_volt: Optional[ParameterMap | None] = None,
        do_align: bool = True,
        no_play_tolerance: float = 1e-6
    ):
    """ 
    Helper function that `play`s a qua operation on the respective elements 
    specified in the sequence config.

    Args:
        elements (list): elements on which pulse is applied
        to_volt (ParameterMap): voltage point to move to
        operation (str): Operation to be played -> find in OPX config
        from_volt (Optional[ParameterMap | None]): voltage point to come from
        duration (str | qcodes.Parameter): duration of the operation 
        do_align (optional, bool): whether to align elements before and after
            the ramp
        no_play_tolerance (optional, float): tolerance for not playing a pulse
    """
    target_params = to_volt
    origin_params = from_volt
    _check_voltage_point_input(to_volt, elements)
    if origin_params is not None:
        _check_voltage_point_input(origin_params, elements)
    if do_align:
        qua.align(*elements)
    for element in elements:
        if origin_params is not None:
            amplitude = target_params[element].qua - origin_params[element].qua
        else:
            print(target_params)
            amplitude = target_params[element].qua
        kwargs = {
            'pulse': operation*qua.amp(amplitude),
            'element': element
            }
        if duration is not None:
            kwargs['duration'] = duration.qua
        logging.debug(
            "Arbok_go: Moving %s from %s to %s by %s", 
            element, from_volt, to_volt, amplitude
            )
        if not isinstance(amplitude, float):
            qua.play(**kwargs)
        elif math.isclose(amplitude, 0, abs_tol= no_play_tolerance):
            logging.debug(
                "Arbok_go: Omitting %s since amplitude %s is small (th = %s)", 
                element, amplitude, no_play_tolerance
                )
        else:
            qua.play(**kwargs)
    if do_align:
        qua.align(*elements)

def _check_voltage_point_input(
        parameter_maps: ParameterMap[str, Voltage],
        elements: list[str]
        ) -> None:
    """
    Checks if input is of type list or string and returns input as list
    """
    if parameter_maps is None:
        print('Nothing to return!')
        return
    if not isinstance(parameter_maps, ParameterMap):
        raise TypeError(
            f"Must be of type ParameterMap. Is {type(parameter_maps)}")
    if not all([isinstance(p, Voltage) for _, p in parameter_maps.items()]):
        raise TypeError(
            "Not all parameters in the given ParameterMap are of type Voltage"
        )
    if not set(elements).issubset(parameter_maps):
        missing = set(elements) - parameter_maps.keys()
        raise ValueError(
            f"Parameter map {parameter_maps} is missing elements: {missing}")
