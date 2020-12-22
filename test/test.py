import os.path
import sys

sys.path.insert(0, '..')
from gtfs_reader import GtfsReader

reader = GtfsReader(
    os.path.join('..', 'sample_data', 'PID_GTFS.zip')
)

# reader.write('test.shp')
reader.write('test.gpkg')
