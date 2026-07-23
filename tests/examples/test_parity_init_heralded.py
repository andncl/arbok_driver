"""
Module testing the heralded parity initialization example: the
`ParityInitHeralded` sub-sequence and its `parity_init_heralded_conf` config.

The heralded init wraps the bare `ParityInit` in a repeat-until-success loop
driven by the following readout. This is verified both at the Python level
(inheritance, parameters, step requirement registration) and by inspecting the
compiled QUA program (conditional re-init, control gating, conditional saving).
"""
import pytest

from arbok_driver.examples.sequences import ParityInitHeralded, ParityInit, Xstrict
from arbok_driver.examples.configurations.sequence import (
    parity_init_conf, parity_init_heralded_conf, parity_read_conf
)

FEEDBACK_RESULT = 'parity_read.p1p2.state__p1p2.qua_result_var'

test_heralded_measurement_dict = {
    'parity_init': {
        'config': parity_init_heralded_conf,
        'kwargs': {
            'feedback_result': FEEDBACK_RESULT,
            'target_state': 1,
        },
    },
    'spin_control': {
        'sub_sequences': {
            'x_gate': {
                'sequence': Xstrict,
                'kwargs': {
                    'target_qubit': 'Q1',
                    'control_pulse': 'control_pi',
                },
            },
        },
        'kwargs': {'check_step_requirements': True},
    },
    'parity_read': {'config': parity_read_conf},
}


def test_heralded_conf_is_parity_init_superset() -> None:
    """The heralded config reuses the bare init config plus one extra param"""
    assert parity_init_heralded_conf['sequence'] is ParityInitHeralded
    assert issubclass(ParityInitHeralded, ParityInit)
    # every bare-init parameter is preserved
    bare_params = set(parity_init_conf['parameters'])
    heralded_params = set(parity_init_heralded_conf['parameters'])
    assert bare_params.issubset(heralded_params)
    # the single extra parameter is the post-heralding settle time
    assert heralded_params - bare_params == {'t_wait_post_init'}
    # the copy must not mutate the original bare-init config
    assert 't_wait_post_init' not in parity_init_conf['parameters']


def test_heralded_measurement_structure(mock_measurement) -> None:
    """The heralded measurement builds with the expected hierarchy"""
    mock_measurement.add_subsequences_from_dict(test_heralded_measurement_dict)
    assert len(mock_measurement.sub_sequences) == 3
    assert isinstance(mock_measurement.parity_init, ParityInitHeralded)
    assert len(mock_measurement.spin_control.sub_sequences) == 1
    # constructor kwargs are stored on the heralded init
    assert mock_measurement.parity_init.feedback_result == FEEDBACK_RESULT
    assert mock_measurement.parity_init.target_state is True
    # the control stage is gated on the step requirement
    assert mock_measurement.spin_control.check_step_requirements is True
    # the extra timing parameter is exposed on the init sub-sequence
    assert mock_measurement.parity_init.t_wait_post_init.get() == int(1e3/4)


def test_heralded_measurement_registers_step_requirement(
        mock_measurement) -> None:
    """Compiling registers exactly one step requirement on the measurement"""
    mock_measurement.add_subsequences_from_dict(test_heralded_measurement_dict)
    assert mock_measurement.step_requirements == []
    mock_measurement.get_qua_program()
    assert len(mock_measurement.step_requirements) == 1


def test_heralded_measurement_compiles(mock_measurement) -> None:
    """The heralded measurement compiles to a QUA program with the expected
    conditional control flow of a repeat-until-success protocol"""
    mock_measurement.add_subsequences_from_dict(test_heralded_measurement_dict)
    prg_str = mock_measurement.get_qua_program_as_str(recompile=True)

    # bare ParityInit ramps are re-used inside the heralding loop
    assert 'unit_ramp' in prg_str
    # ... conditionally: re-init sits in the else branch of the herald check
    assert 'with else_():' in prg_str
    # the readout measurements run every iteration
    assert 'measure(' in prg_str

    # the single X control gate is gated behind a step-requirement check:
    # the `play` is the body of a `with if_(...):` block
    lines = [line.strip() for line in prg_str.splitlines()]
    control_idx = next(
        i for i, line in enumerate(lines)
        if line == 'play("control_pi", "Q1")'
    )
    assert lines[control_idx - 1].startswith('with if_(')


def test_heralded_target_state_zero_compiles(mock_measurement) -> None:
    """Heralding on the opposite target state compiles as well"""
    dict_target_zero = {
        'parity_init': {
            'config': parity_init_heralded_conf,
            'kwargs': {
                'feedback_result': FEEDBACK_RESULT,
                'target_state': 0,
            },
        },
        'parity_read': {'config': parity_read_conf},
    }
    mock_measurement.add_subsequences_from_dict(dict_target_zero)
    assert mock_measurement.parity_init.target_state is False
    prg_str = mock_measurement.get_qua_program_as_str(recompile=True)
    assert 'measure(' in prg_str


def test_heralded_debug_streams_attempts(mock_measurement) -> None:
    """With debug enabled the per-shot attempt counter is streamed"""
    dict_debug = {
        'parity_init': {
            'config': parity_init_heralded_conf,
            'kwargs': {
                'feedback_result': FEEDBACK_RESULT,
                'target_state': 1,
                'debug': True,
            },
        },
        'parity_read': {'config': parity_read_conf},
    }
    mock_measurement.add_subsequences_from_dict(dict_debug)
    assert mock_measurement.parity_init.debug is True
    prg_str = mock_measurement.get_qua_program_as_str(recompile=True)
    assert 'heralded_attempts' in prg_str


def test_heralded_debug_disabled_has_no_attempt_stream(mock_measurement) -> None:
    """With debug disabled no attempt stream is emitted"""
    dict_no_debug = {
        'parity_init': {
            'config': parity_init_heralded_conf,
            'kwargs': {
                'feedback_result': FEEDBACK_RESULT,
                'target_state': 1,
                'debug': False,
            },
        },
        'parity_read': {'config': parity_read_conf},
    }
    mock_measurement.add_subsequences_from_dict(dict_no_debug)
    assert mock_measurement.parity_init.debug is False
    prg_str = mock_measurement.get_qua_program_as_str(recompile=True)
    assert 'heralded_attempts' not in prg_str
