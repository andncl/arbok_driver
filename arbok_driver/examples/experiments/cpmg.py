"""Module containing a simple CPMG experiment"""

from typing import Mapping

from arbok_driver import Experiment

from arbok_driver.examples.sequences import (
    Cpmg,
    FromControlPoint,
    StateProjection,
    ToControlPoint,
    Xstrict 
    )

class CpmgExperiment(Experiment):
    """Experiment containing a CPMG sequence with nested sub-sequences"""
    _name = 'cpmg_experiment'

    def __init__(
            self, target_qubit: str, parity_init: dict, parity_read: dict
            ) -> None:
        self.target_qubit = target_qubit
        super().__init__(parity_init = parity_init, parity_read = parity_read)

    @property
    def sequences_config(self):
        """Sequences-dict to contruct experiment"""
        return {
            'parity_init': {'config': self.configs["parity_init"]},
            'to_control': {'sequence': ToControlPoint},
            'spin_control':{
                'sub_sequences': {
                    'x_strict': {
                        'sequence': Xstrict,
                        'kwargs': {
                            'target_qubit': self.target_qubit,
                            'control_pulse': 'control_pi2'
                        }
                    },
                    'cpmg': {
                        'sequence': Cpmg,
                        'kwargs': {
                            'target_qubit': self.target_qubit,
                            'repetitions': 10,
                            't_equator_wait': int(1e3)
                        }
                    },
                    'state_projection': {
                        'sequence': StateProjection,
                        'kwargs': {
                            'target_qubit': self.target_qubit,
                        }
                    }
                }
            },
            'from_control': {'sequence': FromControlPoint},
            'parity_read': {'config': self.configs["parity_read"]}
        }