"""Init module loading example configurations"""
from .hardware_configs.divider_config import divider_config
from .hardware_configs.opx1000_config import opx1000_config
from .sequence_configs.coulomb_peaks_config import coulomb_peaks_set1_set2_conf
from .sequence_configs.device_config import device_config
from .sequence_configs.parity_init_conf import parity_init_conf
from .sequence_configs.parity_readout_conf import parity_read_conf
from .sequence_configs.square_pulse_confs import (
    square_pulse_conf,
    square_pulse_scalable_conf,
)
from .sequence_configs.stability_map_config import stability_map_config