import os.path
from pathlib import Path
from zipfile import ZipFile
from qgis.core import QgsVectorFileWriter, QgsVectorLayer, QgsMessageLog, Qgis

class GtfsError(Exception):
    pass

class GtfsReader:
    def __init__(self, input_zip):
        self.input_zip = input_zip

    def write(self, output_file):
        ext = Path(output_file).suffix
        if ext == '.gpkg':
            self._write_gpkg(output_file)
        else:
            raise GtfsError("Unsupported format extention {}".format(ext))

    def _write_gpkg(self,output_file):
        GTFS_name = os.path.splitext(os.path.basename(self.input_zip))[0]
        GTFS_path = os.path.join(os.path.dirname(self.input_zip), GTFS_name)

        # 1. unzip_file
        csv_files = self.unzip_file(self.input_zip,GTFS_path)

        # 2. save_layers_into_gpkg
        layer_names = self.save_layers_into_gpkg(csv_files,output_file)

        # 3. checking_required_layers
        self.checking_required_layers(layer_names)

    def unzip_file(self,input_zip,GTFS_path):
        # Load file - function that reads a GTFS ZIP file.

        # Create a folder for files.
        if not os.path.exists(GTFS_path):
            os.mkdir(GTFS_path)
        # Extracts files to path.
        with ZipFile(input_zip, 'r') as zip:
            # printing all the contents of the zip file
            zip.printdir()
            zip.extractall(GTFS_path)
        # Select text files only.
        csv_files = []
        # r=root, d=directories, f = files
        for r, d, f in os.walk(GTFS_path):
            for csv_file in f:
                current_file = os.path.splitext(os.path.basename(csv_file))[1]
                if current_file == '.txt':
                    csv_files.append(os.path.join(r, csv_file))
        return csv_files

    def save_layers_into_gpkg(self, csv_files, output_file):
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
            QgsVectorFileWriter.writeAsVectorFormat(layer, output_file, options)
            # append layers into single GPKG
            options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
        # Return all layers from geopackage
        return layer_names

    def checking_required_layers(self, layer_names):
        required_layers = ['agency','routes','trips','stop_times','stops','calendar']
        if set(required_layers).issubset(layer_names):
            QgsMessageLog.logMessage('All required files are included!', 'GTFS load', Qgis.Success)
        else:
            QgsMessageLog.logMessage('Some of the required files are missing!\n'
                                     'There is a list of required files: {}'.format(required_layers), 'GTFS load', Qgis.Warning)