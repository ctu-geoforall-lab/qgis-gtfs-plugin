import os.path
import shutil
from pathlib import Path
from zipfile import ZipFile
from qgis.core import QgsVectorFileWriter, QgsVectorLayer, QgsMessageLog, Qgis

class GtfsError(Exception):
    pass

class GtfsReader:
    def __init__(self, input_zip):
        self.input_zip = input_zip
        self.dir_name = os.path.splitext(os.path.basename(self.input_zip))[0]
        self.dir_path = os.path.join(os.path.dirname(self.input_zip), self.dir_name)

    def __del__(self):
        shutil.rmtree(self.dir_path)

    def write(self, output_file):
        ext = Path(output_file).suffix
        if ext != '.gpkg':
            raise GtfsError("Unsupported format extention {}".format(ext))

        # 1. unzip_file
        csv_files = self._unzip_file()

        # 2. store data into target data format
        if ext == '.gpkg':
            layer_names = self._write_gpkg(csv_files, output_file)
        else:
            pass # it shouldn't happen

        # 3. checking_required_layers
        self._checking_required_layers(layer_names)

        return layer_names
    
    def _unzip_file(self):
        # Load file - function that reads a GTFS ZIP file.

        # Create a folder for files.
        if not os.path.exists(self.dir_path):
            os.mkdir(self.dir_path)
        # Extracts files to path.
        with ZipFile(self.input_zip, 'r') as zip:
            # printing all the contents of the zip file
            zip.printdir()
            zip.extractall(self.dir_path)
        # Select text files only.
        csv_files = []
        # r=root, d=directories, f = files
        for r, d, f in os.walk(self.dir_path):
            for csv_file in f:
                current_file = os.path.splitext(os.path.basename(csv_file))[1]
                if current_file == '.txt':
                    csv_files.append(os.path.join(r, csv_file))
        return csv_files

    def _write_gpkg(self, csv_files, output_file):
        layer_names = []
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = 'GPKG'

        for csv in csv_files:
            # build URI
            uri = 'file:///{}?delimiter=,'.format(csv)
            csv_name = os.path.splitext(os.path.basename(csv))[0]
            if csv_name == 'stops':
                uri += '&xField=stop_lon&yField=stop_lat&crs=epsg:4326'
            elif csv_name == 'shapes':
                uri += '&xField=shape_pt_lon&yField=shape_pt_lat&crs=epsg:4326'
                csv_name='shapes_point'

            # create CSV-based layer
            layer_names.append(csv_name)
            layer = QgsVectorLayer(uri, csv_name, 'delimitedtext')

            # save layer to GPKG
            options.layerName = layer.name().replace(' ', '_')
            code, msg = QgsVectorFileWriter.writeAsVectorFormat(layer, output_file, options)
            if code != QgsVectorFileWriter.NoError:
                raise GtfsError("Unable to create output GPKG file {} (details: {}/{})".format(output_file, code, msg))

            # append layers into single GPKG
            options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
        # Return all layers from geopackage
        return layer_names

    def _checking_required_layers(self, layer_names):
        required_layers = ['agency','routes','trips','stop_times','stops','calendar']
        if set(required_layers).issubset(layer_names):
            QgsMessageLog.logMessage('All required files are included!', 'GTFS load', Qgis.Success)
        else:
            QgsMessageLog.logMessage('Some of the required files are missing!\n'
                                     'There is a list of required files: {}'.format(required_layers), 'GTFS load', Qgis.Warning)
