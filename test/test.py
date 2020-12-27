import os.path
import sys

#Change your path
path = 'C:/Users/kouba/Documents/GitHub/qgis-gtfs-plugin/'

sys.path.insert(0, path)
from gtfs_reader import GtfsReader

reader = GtfsReader(
    os.path.join(path, 'sample_data', 'PID_GTFS.zip')
)

# reader.write('test.shp')
reader.write(path + 'test.gpkg')
