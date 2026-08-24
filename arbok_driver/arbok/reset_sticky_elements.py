"""Module containing reset_sticky_elements function"""
from .context import get_active_backend


def reset_sticky_elements(
        element_list: list,
        do_align: bool = True,
        ) -> None:
    """
    Runs `ramp_to_zero` on all sticky elements in the given list.
    This is cruicial to stop numerical errors from accumulation on the sticky
    elements
    """
    backend = get_active_backend()
    for element_name in element_list:
        backend.ramp_to_zero(element_name)
    if do_align:
        backend.align(element_list)
