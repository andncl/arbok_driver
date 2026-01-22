"""Module containing reset_sticky_elements function"""
from qm import qua

def reset_sticky_elements(
        element_list: list,
        do_align: bool = True,
        ) -> None:
    """
    Runs `ramp_to_zero` on all sticky elements in the given list.
    This is cruicial to stop numerical errors from accumulation on the sticky
    elements
    """
    for element_name in element_list:
        qua.ramp_to_zero(element_name)
    if do_align:
        qua.align(*element_list)
