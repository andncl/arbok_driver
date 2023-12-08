"""Module containing signal class"""

from .readout_point import ReadoutPoint

class Signal:
    """
    Class managing voltage signal from certain redoout elements of OPX
    """
    def __init__(
            self,
            name: str,
            readout_elements: dict,
            readout_points: dict
            ):
        """
        Constructor method of Signal class
        
        Args:
            name (str): Name of the signal
            readout_points (dict): List of readout points
            readout_elements (dict): List of readout elements
        """
        self.readout_elements = readout_elements
        self._readout_points = []
        for name, config in readout_points.items():
            new_point = ReadoutPoint(name=name, signal=self, config=config)
            setattr(self, name, new_point)
            self._readout_points.append(new_point)

    @property
    def readout_points(self):
        return self._readout_points
