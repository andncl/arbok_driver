"""Module containing Average child class inheriting from ReadoutPoint"""
from qm import qua
from arbok_driver.readout_point import ReadoutPoint

class Average(ReadoutPoint):
    """
    ReadoutPoint child class providing a `qua_measure` method to measure I and Q
    in a static averaging manner
    """
    def __init__(
            self,
            point_name: str,
            signal: any,
            config: dict
            ):
        """
        Constructor method of ReadoutPoint class
        
        Args:
            point_name (str): Name of readout point
            signal (Signal): Signal corresponding to readout point
            config (dict): List of readout points
        """
        super().__init__(point_name, signal, config)

    def qua_measure(self):
        """
        Measures I and Q at the given read point in a static averaging manner
        """
        for name, qm_element in self.signal.readout_elements.items():
            self._check_IQ_qua_vars(name)
            qua_var_I = getattr(self, f"{name}_I").qua_var
            qua_var_Q = getattr(self, f"{name}_Q").qua_var
            outputs = [
                qua.integration.full('x', qua_var_I),
                qua.integration.full('y', qua_var_Q)
                ]
            qua.measure('measure', qm_element, None, *outputs)
            if 'IQ' in self.config["observables"]:
                qua.assign(
                    getattr(self, f"{name}_IQ").qua_var, qua_var_I + qua_var_Q)
