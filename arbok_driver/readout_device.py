"""Module containing class to describe readout devices"""

from arbok_driver import ReadSequence, ReadoutPoint


class ReadoutDevice():
    """Class describing readout hardware"""
    def __init__(
            self,
            name: str,
            sequence: ReadSequence,
            readout_device_config: dict
            ):
        """
        Constructor method for ReadoutDevice class
        
        Args:
            name (str):
            sequence (ReadSequence): ReadSequence containing readout
            readout_device_config (dict):
        """
        self.name = name
        self.sequence = sequence
        self.readout_device_config = readout_device_config
        self._readout_points = []
        self.add_readout_points_from_config()

    def add_readout_points_from_config(self):
        """Creates ReadoutPoint objects from readout device config"""
        if self.readout_device_config is None:
            raise ValueError(f"No readout config given for {self.name}")
        for read_point_name, config in self.readout_device_config:
            new_read_point = ReadoutPoint(read_point_name, config)
            setattr(self, read_point_name, new_read_point)
            self._readout_points.append(new_read_point)

    def declare_qua_variables(self):
        """Declares QUA variables for streams"""
        for read_point in self._readout_points:
            read_point.declare_qua_vars()
