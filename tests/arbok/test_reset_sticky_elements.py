

import re

import pytest
from qm import generate_qua_script, qua

from arbok_driver import arbok

@pytest.mark.parametrize("nr_elements", [0, 1, 2, 4])
def test_correct_amount_of_resets(nr_elements):
    with qua.program() as prg:
        arbok.reset_sticky_elements([f"P{i}" for i in range(nr_elements)])
    prg_str = generate_qua_script(prg)
    assert len(list(re.finditer('ramp_to_zero', prg_str))) == nr_elements

def test_align():
    with qua.program() as prg:
        arbok.reset_sticky_elements(["P0", "P1"], do_align=True)
    prg_str = generate_qua_script(prg)
    assert len(list(re.finditer('align', prg_str))) == 1
    with qua.program() as prg:
        arbok.reset_sticky_elements(["P0", "P1"], do_align=False)
    prg_str = generate_qua_script(prg)
    assert len(list(re.finditer('align', prg_str))) == 0
