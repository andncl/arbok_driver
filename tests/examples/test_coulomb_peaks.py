
from arbok_driver.examples.sub_sequences import CoulombPeaks
from arbok_driver.examples.configurations.sequence import (
    coulomb_peaks_set1_set2_conf
)
def test_coulomb_peaks(mock_measurement):
    coulomb_peaks = CoulombPeaks(
        mock_measurement, 'coulomb_peaks', coulomb_peaks_set1_set2_conf
    )
    prg_str = mock_measurement.get_qua_program_as_str(recompile = True)
    assert len(coulomb_peaks.signals) == 3
    assert len(coulomb_peaks.abstract_readouts) == 3
    assert len(coulomb_peaks.readout_groups) == 2
