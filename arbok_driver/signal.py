"""Module containing signal class"""
import logging
from .readout_point import ReadoutPoint

class Signal:
    """
    Class managing voltage signal from certain redoout elements of OPX
    """
    def __init__(
        self,
        name: str,
        sequence,
        config: dict,
        ):
        """
        Constructor method of Signal class
        a
        Args:
            name (str): Name of the signal
            readout_points (dict): List of readout points
            readout_elements (dict): List of readout elements
        """
        self.name = name
        self.sequence = sequence
        self.config = config

        self._observables = {}
        self._readout_elements = self.config["elements"]
        self._readout_points = {}
        self.readout_points_from_config(self.config["readout_points"])

    @property
    def observables(self):
        """Dictionary with all observables registered on the signal"""
        return self._observables

    @property
    def readout_points(self):
        """List of readout points"""
        return self._readout_points

    @property
    def readout_elements(self):
        """List of readout elements"""
        return self._readout_elements

    def qua_save_streams(self):
        """Saves streams of all readout points"""
        for point_name, readout_point in self.readout_points.items():
            readout_point.qua_save_streams()
            logging.debug("Saving streams of readout point %s", point_name)

    def add_abstract_readout(
        self,
        abstract_readout,
        name: str
        ):
        """
        Adds an abstract readout to this signal
        
        Args:
            abstract_readout (arbok_driver.AbstractReadout): Readout to add
            name (str): Abstract readout to add
        """
        logging.debug(
            "Adding abstract readout %s to signal %s",
            self.name,
            abstract_readout
            )
        setattr(self, name, abstract_readout)
        self._abstract_readouts[name] = abstract_readout

    def readout_points_from_config(self, points_config: dict):
        """
        Adds the readout points to the signal from the given config
            
        Args:
            points_config (dict): dictionairy configuring all readout points
        """
        for point_name, point_config in points_config.items():
            logging.debug(
                "Adding readout point '%s' to signal '%s'",
                point_name,
                self.name
                )
            new_point = ReadoutPoint(
                point_name=point_name,
                signal=self,
                config=point_config
                )
            setattr(self, point_name, new_point)
            self._readout_points[new_point.name] = new_point
            self.sequence.readout_points[new_point.name] = new_point
