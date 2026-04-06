
from arbok_driver.examples.sequences import StabilityMap
from arbok_driver.examples.configurations.sequence import (
    stability_8q_conf, stability_2q_conf
)
def test_stability_map_8q(mock_measurement):
    stability_map = StabilityMap(
        mock_measurement, 'stability_map', stability_8q_conf
    )
    prg_str = mock_measurement.get_qua_program_as_str(recompile = True)
    assert len(stability_map.signals) == 1
    assert len(stability_map.readout_groups) == 1
    assert len(stability_map.abstract_readouts) == 1
    assert len(mock_measurement.available_gettables) == 12 # 3 x 4

def test_stability_map_2q(mock_measurement):
    stability_map = StabilityMap(
        mock_measurement, 'stability_map', stability_2q_conf
    )
    prg_str = mock_measurement.get_qua_program_as_str(recompile = True)
    assert len(stability_map.signals) == 1
    assert len(stability_map.readout_groups) == 1
    assert len(stability_map.abstract_readouts) == 1
    assert len(mock_measurement.available_gettables) == 3
