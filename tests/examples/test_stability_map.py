
from arbok_driver.examples.sub_sequences import StabilityMap
from arbok_driver.examples.configurations import (
    stability_map_config
)
def test_stability_map(dummy_measurement):
    stability_map = StabilityMap(
        dummy_measurement, 'stability_map', stability_map_config
    )
    prg_str = dummy_measurement.get_qua_program_as_str(recompile = True)
    assert len(stability_map.signals) == 1
    assert len(stability_map.readout_groups) == 1
    assert len(stability_map.abstract_readouts) == 1