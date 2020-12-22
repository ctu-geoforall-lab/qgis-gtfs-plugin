from pathlib import Path

class GtfsError(Exception):
    pass

class GtfsReader:
    def __init__(self, input_zip):
        self.input_zip = input_zip

    def unzip_file(self):
        pass # TBD
    
    def write(self, output_file):
        ext = Path(output_file).suffix
        if ext == '.gpkg':
            self._write_gpkg(output_file)
        else:
            raise GtfsError("Unsupported format extention {}".format(ext))

    def _write_gpkg(output_file):
        # 1. unzip_file
        # 2. save_layers_into_gpkg
        # 3. checking_required_layers (?)
        pass
    
    
        
    
