"""Module testing generic tuning interface"""
import pytest
import re
import numpy as np

from arbok_driver.generic_tunig_interface import CostStrategy
from arbok_driver.examples.configurations import (
    parity_init_conf, parity_read_conf
)

def test_generic_tuning_interface_init(mock_measurement) -> None:
    mock_measurement.driver.is_mock = True
    mock_measurement.mock_steps = 0
    mock_measurement.add_subsequences_from_dict(
        {
            'paraity_init_even': {'config': parity_init_conf},
            'parity_read_even': {'config': parity_read_conf},
            'parity_init_odd': {'config': parity_init_conf},
            'parity_read_odd': {'config': parity_read_conf}
        }
    )
    _ = mock_measurement.get_qua_program_as_str()

    class CustomStrategy(CostStrategy):
        def get_cost(self, results: dict) -> float:
            return float(np.random.rand())
        
    parity_cost_strat = CustomStrategy(
        [
            mock_measurement.parity_read_even.p1p2.diff__p1p2,
            mock_measurement.parity_read_odd.p1p2.diff__p1p2,
        ],
        )

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
    }
    tuning_interface = mock_measurement.initialize_tuning_interface(
        parameter_dicts = parameter_dicts,
        cost_strategy = parity_cost_strat,
        sweeps = [{mock_measurement.iteration: np.arange(100)}],
        verbose = True
    )

    qua_prog_input_streams_str = mock_measurement.get_qua_program_as_str(
        recompile=True)
    assert len(re.findall('advance_input_stream', qua_prog_input_streams_str)) == 2

    dataset = tuning_interface.run_cross_entropy_sampler(
        populations = [10, 10],
        select_frac = 0.5,
        plot_histograms = True,
        sampling_params_to_plot = [('t_ramp_init', 'read_detuning')]
    )
    assert len(dataset) == len(mock_measurement.gettables) + len(parameter_dicts) + 1
