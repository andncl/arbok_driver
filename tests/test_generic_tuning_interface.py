"""Module testing generic tuning interface"""
import pytest
import re
import numpy as np

from arbok_driver.generic_tunig_interface import CostStrategy
from arbok_driver.examples.configurations import (
    parity_init_conf, parity_read_conf
)

def test_generic_tuning_interface_init(mock_measurement) -> None:
    mock_measurement.add_subsequences_from_dict(
        {
            'paraity_init_even': {'config': parity_init_conf},
            'parity_read_even': {'config': parity_read_conf},
            'parity_init_odd': {'config': parity_init_conf},
            'parity_read_odd': {'config': parity_read_conf}
        }
    )
    qua_prog_str = mock_measurement.get_qua_program_as_str()

    class CustomStrategy(CostStrategy):
        def get_cost(self, results: dict) -> float:
            return float(np.random.rand())
        
    parity_cost_strat = CustomStrategy(
        mock_measurement.available_gettables,
        [{mock_measurement.iteration: np.arange(100)}]
        )

    mock_measurement.initialize_tuning_interface(
        parameter_dicts = {
            't_ramp_init': {
                'qua_vars': {mock_measurement.parity_init_odd.arbok_params.t_ramp_over_crossing: 1},
                'bounds': (25, 1e4)
                },
            'read_detuning': {
                'qua_vars': {
                    mock_measurement.parity_read_even.arbok_params.v_read['P1']: 1,
                    mock_measurement.parity_read_even.arbok_params.v_read['P2']: -1,
                    mock_measurement.parity_read_odd.arbok_params.v_read['P1']: 1,
                    mock_measurement.parity_read_odd.arbok_params.v_read['P2']: -1,
                    },
                'bounds': (-0.01, 0.01)
                },
            },
        cost_strategy = parity_cost_strat,
        verbose = True
    )

    qua_prog_input_streams_str = mock_measurement.get_qua_program_as_str(
        recompile=True)
    assert len(re.findall('advance_input_stream', qua_prog_input_streams_str)) == 2
