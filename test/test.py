import os.path
import sys

from qgis.core import *
# Initialize QGIS Application
qgs = QgsApplication([], False)
QgsApplication.setPrefixPath(r"C:\OSGEO4~1\apps\qgis", True)
QgsApplication.initQgis()

plugin_path = os.path.join(os.path.dirname(__file__), '..')

sys.path.insert(0, plugin_path)
from gtfs_reader import GtfsReader

reader = GtfsReader(
    os.path.join(plugin_path, 'sample_data', 'PID_GTFS.zip')
)

reader.write(os.path.join(plugin_path, 'test', 'test.gpkg'))
