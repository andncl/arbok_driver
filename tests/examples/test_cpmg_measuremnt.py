"""
Module testing the behaviour of a complex CPMG measurement containing nested
sub-sequences
"""
import pytest

from arbok_driver.examples.sequences import (
    Cpmg,
    FromControlPoint,
    StateProjection,
    ToControlPoint,
    Xstrict 
    )
from arbok_driver.examples.configurations.sequence import (
    parity_init_conf, parity_read_conf
)
from arbok_driver.examples.experiments import CpmgExperiment

test_cpmg_measurement_dict = {
    'parity_init': {'config': parity_init_conf},
    'to_control': {'sequence': ToControlPoint},
    'spin_control':{
        'sub_sequences': {
            'x_strict': {
                'sequence': Xstrict,
                'kwargs': {
                    'target_qubit': 'Q1',
                    'control_pulse': 'control_pi2'
                }
            },
            'cpmg': {
                'sequence': Cpmg,
                'kwargs': {
                    'target_qubit': 'Q1',
                    'repetitions': 10,
                    't_equator_wait': int(1e3)
                }
            },
            'state_projection': {
                'sequence': StateProjection,
                'kwargs': {
                    'target_qubit': 'Q1',
                }
            }
        }
    },
    'from_control': {'sequence': FromControlPoint},
    'parity_read': {'config': parity_read_conf}
}

def test_cpmg_measurement(mock_measurement) -> None:
    """Tests if a CPMG measurement with nested sub-sequences is correctly
    initialized and executed"""
    mock_measurement.add_subsequences_from_dict(test_cpmg_measurement_dict)
    assert len(mock_measurement.sub_sequences) == 5
    assert len(mock_measurement.spin_control.sub_sequences) == 3
    assert mock_measurement.spin_control.cpmg.repetitions.get() == 10
    prg_str = mock_measurement.get_qua_program_as_str(recompile = True)

def test_cpmg_measurement_from_experiment(arbok_driver) -> None:
    mock_measurement = arbok_driver.create_measurement_from_experiment(
        CpmgExperiment(
            target_qubit = 'Q1',
            parity_init=parity_init_conf,
            parity_read=parity_read_conf
        )
    )
    assert len(mock_measurement.sub_sequences) == 5
    assert len(mock_measurement.spin_control.sub_sequences) == 3
    assert mock_measurement.spin_control.cpmg.repetitions.get() == 10
    prg_str = mock_measurement.get_qua_program_as_str(recompile = True)
