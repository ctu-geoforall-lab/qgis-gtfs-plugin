from qgis import processing
from qgis.core import QgsVectorLayer, QgsProject, QgsVectorFileWriter, QgsCoordinateReferenceSystem, QgsLayerTreeLayer, \
    QgsDistanceArea, QgsSymbol, QgsRendererCategory, QgsCategorizedSymbolRenderer, QgsDataProvider
from PyQt5.QtGui import QColor


class GtfsZones:
    def __init__(self, gpkg_path):
        self.gpkg_path = gpkg_path
        self.zones = ['P', '0', 'B', '1', '2', '3', '4', '5', '6', '7', '8', '9']

    def zone_process(self):
        self._voronoi()

        expressionZones = "', '".join(map(str, self.zones))
        self._smooth('P0B', "zone_id NOT IN ('" + expressionZones + "') AND (zone_id LIKE '%" + self.zones[0] + "%'"
                            " OR zone_id LIKE '%" + self.zones[1] + "%' OR zone_id LIKE '%" + self.zones[2] + "%')")

        list_zones_smoothed = []
        list_border_zones_smoothed = []
        for i in self.zones[3:]:

            self._smooth(i,"zone_id LIKE '" + i + "," + str(int(i)+1) + "'")

            list_zones_smoothed.append(self.gpkg_path + '|layername=zone' + i + '_concaveHull_smoothed')
            list_border_zones_smoothed.append(self.gpkg_path + '|layername=border_zone' + i + '_smooth')
        list_border_zones_smoothed.append(self.gpkg_path + '|layername=border_zoneP0B_smooth')

        self._colecting_zones(list_zones_smoothed, list_border_zones_smoothed)

        smooth_layer = QgsProject.instance().addMapLayer(QgsVectorLayer(self.gpkg_path + '|layername=zones',
                                                                        'zones', 'ogr'), False)
        self._set_zone_colors(smooth_layer)

        self._deleting_layers()

        root = QgsProject.instance().layerTreeRoot()
        group_gtfs = root.findGroup('zones')
        group_gtfs.insertChildNode(0, QgsLayerTreeLayer(smooth_layer))

    def _voronoi(self):
        # creates voronoi polygons

        layer_stops = QgsVectorLayer(self.gpkg_path + '|layername=stops', "stops", "ogr")

        processing.run("qgis:voronoipolygons", {
            'INPUT': layer_stops,
            'OUTPUT': 'ogr:dbname=\'' + self.gpkg_path + '\' table=\"voronoi\" (geom)'
        })

        expressionZones = "', '".join(map(str, self.zones[:3]))
        layer_stops.selectByExpression("\"zone_id\" IN ('" + expressionZones + "') AND \"location_type\" = 0")
        self._saveIntoGpkg(layer_stops,'layer_stops_selected')

        layer_stops_selected = QgsVectorLayer(self.gpkg_path + '|layername=layer_stops_selected', 'layer_stops_selected', 'ogr')
        processing.run("qgis:deleteduplicategeometries", {
            'INPUT': layer_stops_selected,
            'OUTPUT': 'ogr:dbname=\'' + self.gpkg_path + '\' table=\"stops_zoneP0B\" (geom)'
        })

        layer_voronoi = QgsVectorLayer(self.gpkg_path + '|layername=voronoi', 'voronoi', 'ogr')
        layer_zoneP0B = QgsVectorLayer(self.gpkg_path + '|layername=stops_zoneP0B', 'stops_zoneP0B', 'ogr')
        # select voronoi polygons intersect with stops
        self._selectbylocation(layer_voronoi, layer_zoneP0B)

        self._saveIntoGpkg(layer_voronoi, 'zoneP0B_voronoi')

        layer_zoneP0B_voronoi = QgsVectorLayer(self.gpkg_path + '|layername=zoneP0B_voronoi', 'zoneP0B_voronoi', 'ogr')
        # combine features into new features
        self._dissolve(layer_zoneP0B_voronoi, 'zoneP0B_voronoi_dissolve')

        layer_zoneP0B_voronoi_dissolve = QgsVectorLayer(self.gpkg_path + '|layername=zoneP0B_voronoi_dissolve', 'zoneP0B_voronoi_dissolve', 'ogr')
        self._multiparttosingleparts(layer_zoneP0B_voronoi_dissolve, 'ogr:dbname=\'' + self.gpkg_path + '\' table=\"zoneP0B_singleparts\" (geom)')

        layer_zoneP0B_singleparts = QgsVectorLayer(self.gpkg_path + '|layername=zoneP0B_singleparts', 'zoneP0B_singleparts', 'ogr')
        layer_zoneP0B_singleparts.selectByExpression('$area = maximum($area, "zone_id")')
        self._saveIntoGpkg(layer_zoneP0B_singleparts,'zoneP0B_max')

        layer_zoneP0B_max = QgsVectorLayer(self.gpkg_path + '|layername=zoneP0B_max', 'zoneP0B_max', 'ogr')
        processing.run("qgis:deleteholes", {
            'INPUT': layer_zoneP0B_max, 'MIN_AREA': 500,
            'OUTPUT': 'ogr:dbname=\'' + self.gpkg_path + '\' table=\"zoneP0B_without_holes\" (geom)'
        })

        list_zones = []
        for i in self.zones[3:]:
            # select stops by zone_id
            _layer_stops = QgsVectorLayer(self.gpkg_path + '|layername=stops', "stops", "ogr")

            if int(i) <= 6:
                _layer_stops.selectByExpression("\"zone_id\" <= " + i + "AND \"zone_id\" != '-' AND \"location_type\" = 0")
            else:
                _layer_stops.selectByExpression("\"zone_id\" = " + i + "AND \"location_type\" = 0")

            self._saveIntoGpkg(_layer_stops, 'stops_zone' + i)

            layer_zoneI = QgsVectorLayer(self.gpkg_path + '|layername=stops_zone' + i, 'stops_zone' + i, 'ogr')

            # select voronoi polygons intersect with stops
            self._selectbylocation(layer_voronoi, layer_zoneI)

            self._saveIntoGpkg(layer_voronoi, 'zone' + i + '_voronoi')

            layer_zoneI_voronoi = QgsVectorLayer(self.gpkg_path + '|layername=zone' + i + '_voronoi', 'zone' + i + '_voronoi', 'ogr')

            # combine features into new features
            self._dissolve(layer_zoneI_voronoi, 'zone' + i + '_voronoi_dissolve')

            list_zones.append(self.gpkg_path + '|layername=zone' + i + '_voronoi_dissolve')
        list_zones.append(self.gpkg_path + '|layername=zoneP0B_without_holes')

    def _deleteLayer(self, layer_name):
        '''
        deletes layer into GeoPackage
        '''
        try:
            processing.run("qgis:spatialiteexecutesql", {
                'DATABASE': self.gpkg_path + '|layername=' + layer_name,
                'SQL': 'DROP TABLE ' + layer_name
            })
        except IndexError:
            layer_name = None

    def _saveIntoGpkg(self, layer, layer_name):
        '''
        saves layer into GeoPackage
        '''
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
        options.driverName = 'GPKG'
        options.layerName = layer_name
        options.onlySelectedFeatures = True
        options.destCRS = QgsCoordinateReferenceSystem(4326)
        QgsVectorFileWriter.writeAsVectorFormat(layer, self.gpkg_path, options)

    def _dissolve(self, input, output, field = []):
        return processing.run("qgis:dissolve", {
                'FIELD': field,
                'INPUT': input,
                'OUTPUT': 'ogr:dbname=\'' + self.gpkg_path + '\' table=\"' + output + '\" (geom)'
        })

    def _selectbylocation(self, input, intersect, method = 0, predicate = [0]):
        return processing.run("qgis:selectbylocation", {
            'INPUT': input,
            'INTERSECT': intersect,
            'METHOD': method,
            'PREDICATE': predicate
        })

    def _mergevectorlayers(self, layers, output, crs = QgsCoordinateReferenceSystem('EPSG:4326')):
        return processing.run("qgis:mergevectorlayers", {
            'CRS': crs,
            'LAYERS': layers,
            'OUTPUT': 'ogr:dbname=\'' + self.gpkg_path + '\' table=\"' + output + '\" (geom)'
        })

    def _multiparttosingleparts(self, input, output):
        return processing.run("qgis:multiparttosingleparts", {
            'INPUT': input,
            'OUTPUT': output
        })

    def _smoothgeometry(self, input, output, iterations = 10, offset = 0.25, max_angle = 180):
        return processing.run('qgis:smoothgeometry', {
            'INPUT': self.gpkg_path + '|layername=' + input,
            'ITERATIONS': iterations,
            'OFFSET': offset,
            'MAX_ANGLE': max_angle,
            'OUTPUT': 'ogr:dbname=\'' + self.gpkg_path + '\' table=\"' + output + '\" (geom)'
        })

    def _collect(self, input, field, output):
        return processing.run("qgis:collect", {
            'INPUT': input,
            'FIELD': field,
            'OUTPUT': output
        })

    def _difference(self, input, overlay, output):
        return processing.run("qgis:difference", {
            'INPUT': input,
            'OVERLAY': overlay,
            'OUTPUT': output
        })

    def _smooth(self, zone_id, expression):
        '''
        select border stops >>> Extract vertices >>> Concave Hull >>> Simplify Geometries >>> Smooth
        '''

        layer_stops = QgsVectorLayer(self.gpkg_path + '|layername=stops', 'stops', 'ogr')
        layer_stops.selectByExpression(expression)
        self._saveIntoGpkg(layer_stops, 'stops_border_zone' + zone_id)

        self._border_zones(zone_id)

        # extract vertices (polygon to nodes)
        processing.run('qgis:extractvertices', {
            'INPUT': self.gpkg_path + '|layername=zone' + zone_id + '_voronoi_dissolve',
            'OUTPUT': 'ogr:dbname=\'' + self.gpkg_path + '\' table=\"zone' + zone_id + '_vertices\" (geom)'
        })

        # merge stops_zoneI + stops_border_zoneI + zoneI_vertices
        zoneI_vertices_stops = [self.gpkg_path + '|layername=stops_zone' + zone_id,
                                self.gpkg_path + '|layername=stops_border_zone' + zone_id,
                                self.gpkg_path + '|layername=zone' + zone_id + '_vertices']

        self._mergevectorlayers(zoneI_vertices_stops, 'zone' + zone_id + '_vertices_stops')

        processing.run("qgis:concavehull", {
            'INPUT': self.gpkg_path + '|layername=zone' + zone_id + '_vertices_stops',
            'ALPHA': 0.09,
            'HOLES': False,
            'NO_MULTIGEOMETRY': True,
            'OUTPUT': 'ogr:dbname=\'' + self.gpkg_path + '\' table=\"zone' + zone_id + '_concaveHull\" (geom)'
        })

        processing.run("qgis:simplifygeometries", {
            'INPUT': self.gpkg_path + '|layername=zone' + zone_id + '_concaveHull',
            'METHOD': 0,
            'TOLERANCE': 0.005,
            'OUTPUT': 'ogr:dbname=\'' + self.gpkg_path + '\' table=\"zone' + zone_id + '_concaveHull_simplified\" (geom)'
        })

        self._smoothgeometry('zone' + zone_id + '_concaveHull_simplified', 'zone' + zone_id + '_concaveHull_smoothed')
        self._smoothgeometry('border_voronoi_dissolve_singleparts_counted_zone' + zone_id + '_moreThanX', 'border_zone' + zone_id +'_smooth')

        layer = QgsVectorLayer(self.gpkg_path + '|layername=zone' + zone_id + '_concaveHull_smoothed', 'zone' + zone_id + '_concaveHull_smoothed', 'ogr')

        d = QgsDistanceArea()
        d.setEllipsoid('WGS84')

        layer.startEditing()
        zone_id_idx = layer.fields().lookupField('zone_id')
        feats = []
        for feat in layer.getFeatures():
            layer.changeAttributeValue(feat.id(), zone_id_idx, zone_id)
            geom = feat.geometry()
            if d.measureArea(geom) / 1e6 < 50:
                feats.append(feat.id())
            layer.deleteFeatures(feats)
        layer.commitChanges()
        layer.updateExtents()

        self._saveIntoGpkg(layer,'zone' + zone_id + '_concaveHull_smoothed')

    def _border_zones(self, zone_id):
        '''
        border layer and voronoi layer >>> Select by location >>> Dissolve >>> Multipart to singleparts >>>
        Count Points in Polygon
        '''

        layer_border = QgsVectorLayer(self.gpkg_path + '|layername=stops_border_zone' + zone_id, 'stops_border_zone' + zone_id, 'ogr')
        layer_voronoi = QgsVectorLayer(self.gpkg_path + '|layername=voronoi', 'voronoi', 'ogr')
        self._selectbylocation(layer_voronoi, layer_border)

        self._saveIntoGpkg(layer_voronoi, 'border_voronoi_zone' + zone_id)
        layer_border_zone_voronoi = QgsVectorLayer(self.gpkg_path + '|layername=border_voronoi_zone' + zone_id, 'border_voronoi_zone' + zone_id, 'ogr')

        self._dissolve(layer_border_zone_voronoi, 'border_voronoi_dissolve_zone' + zone_id)

        layer_border_voronoi_dissolve_zone = QgsVectorLayer(self.gpkg_path + '|layername=border_voronoi_dissolve_zone' + zone_id, 'border_voronoi_dissolve_zone' + zone_id, 'ogr')
        self._multiparttosingleparts(layer_border_voronoi_dissolve_zone, 'ogr:dbname=\'' + self.gpkg_path + '\' table=\"border_voronoi_dissolve_singleparts_zone' + zone_id + '\" (geom)')

        layer_border_voronoi_dissolve_singleparts_zone = QgsVectorLayer(self.gpkg_path + '|layername=border_voronoi_dissolve_singleparts_zone' + zone_id, 'border_voronoi_dissolve_singleparts_zone' + zone_id, 'ogr')
        processing.run("qgis:countpointsinpolygon", {
            'POLYGONS': layer_border_voronoi_dissolve_singleparts_zone,
            'POINTS': layer_border,
            'FIELD': 'NUMPOINTS',
            'OUTPUT': 'ogr:dbname=\'' + self.gpkg_path + '\' table=\"border_voronoi_dissolve_singleparts_counted_zone' + zone_id + '\" (geom)'
        })

        numpoints = '5'
        layer_border_voronoi_dissolve_singleparts_counted_zone = QgsVectorLayer(self.gpkg_path + '|layername=border_voronoi_dissolve_singleparts_counted_zone' + zone_id, 'border_voronoi_dissolve_singleparts_counted_zone' + zone_id, 'ogr')
        layer_border_voronoi_dissolve_singleparts_counted_zone.selectByExpression('NUMPOINTS > ' + numpoints)
        self._saveIntoGpkg(layer_border_voronoi_dissolve_singleparts_counted_zone, 'border_voronoi_dissolve_singleparts_counted_zone' + zone_id + '_moreThanX')

        layer = QgsVectorLayer(self.gpkg_path + '|layername=border_voronoi_dissolve_singleparts_counted_zone' + zone_id + '_moreThanX', 'border_voronoi_dissolve_singleparts_counted_zone' + zone_id + '_moreThanX', 'ogr')

        layer.startEditing()
        zone_id_idx = layer.fields().lookupField('zone_id')
        for feat in layer.getFeatures():
            if zone_id == 'P0B':
                layer.changeAttributeValue(feat.id(), zone_id_idx, 'P0B,1')
            else:
                layer.changeAttributeValue(feat.id(), zone_id_idx, zone_id + ',' + str(int(zone_id) + 1))
        layer.commitChanges()
        layer.updateExtents()

        self._saveIntoGpkg(layer, 'border_voronoi_dissolve_singleparts_counted_zone' + zone_id + '_moreThanX')

    def _colecting_zones(self, list_zones_smoothed, list_border_zones_smoothed):
        list_zones_diff = []
        self._difference(self.gpkg_path + '|layername=zone1_concaveHull_smoothed', self.gpkg_path + '|layername=zoneP0B_concaveHull_smoothed', 'ogr:dbname=\'' + self.gpkg_path + '\' table=\"zoneP0B_smoothed_diff\" (geom)')
        for i in range(len(list_zones_smoothed) - 1):
            self._difference(list_zones_smoothed[i + 1], list_zones_smoothed[i],'ogr:dbname=\'' + self.gpkg_path + '\' table=\"zone' + str(i) + '_smoothed_diff\" (geom)')

            list_zones_diff.append(self.gpkg_path + '|layername=zone' + str(i) + '_smoothed_diff')
        list_zones_diff.append(self.gpkg_path + '|layername=zoneP0B_smoothed_diff')
        list_zones_diff.append(self.gpkg_path + '|layername=zoneP0B_concaveHull_smoothed')

        self._mergevectorlayers(list_zones_diff, 'zones_smoothed')
        self._mergevectorlayers(list_border_zones_smoothed, 'border_zones_smoothed')

        self._collect(self.gpkg_path + '|layername=border_zones_smoothed', ['zone_id'], 'ogr:dbname=\'' + self.gpkg_path + '\' table=\"border_zones_smoothed_collected\" (geom)')
        self._collect(self.gpkg_path + '|layername=zones_smoothed', ['zone_id'], 'ogr:dbname=\'' + self.gpkg_path + '\' table=\"zones_smoothed_collected\" (geom)')

        self._difference(self.gpkg_path + '|layername=zones_smoothed_collected', self.gpkg_path + '|layername=border_zones_smoothed_collected', 'ogr:dbname=\'' + self.gpkg_path + '\' table=\"zones_smoothed_collected_diff\" (geom)')

        self._mergevectorlayers([self.gpkg_path + '|layername=zones_smoothed_collected_diff', self.gpkg_path + '|layername=border_zones_smoothed_collected'], 'zones')


    def _set_zone_colors(self, zones_layer):
        '''
        Function, that sets color of each zone

        input: vector layer zones
        '''
        # zone: #color
        colors = {
            'P0B': '#c02026',
            'P0B,1': '#c02026',
            '1': '#d65e27',
            '1,2': '#d65e27',
            '2': '#e58027',
            '2,3': '#e58027',
            '3': '#f3a228',
            '3,4': '#f3a228',
            '4': '#fabc29',
            '4,5': '#fabc29',
            '5': '#ffd12a',
            '5,6': '#ffd12a',
            '6': '#d6c034',
            '6,7': '#d6c034',
            '7': '#9aaa3e',
            '7,8': '#9aaa3e',
            '8': '#5a8e40',
            '8,9': '#5a8e40',
            '9': '#188041'
        }

        target_field = 'zone_id'
        myCategoryList = []
        for r_fid, r_item in colors.items():
            symbol = QgsSymbol.defaultSymbol(zones_layer.geometryType())
            symbol.setColor(QColor(r_item))
            myCategory = QgsRendererCategory(r_fid, symbol, r_fid)
            myCategoryList.append(myCategory)
            myRenderer = QgsCategorizedSymbolRenderer(target_field, myCategoryList)
            zones_layer.setRenderer(myRenderer)
        zones_layer.triggerRepaint()

    def _deleting_layers(self):
        layer = QgsVectorLayer(self.gpkg_path, "gpkg", "ogr")
        subLayers = layer.dataProvider().subLayers()
        gpkg_layers = []

        layers = ['agency', 'attributions', 'calendar', 'calendar_dates', 'fare_attributes', 'fare_rules', 'feed_info',
                  'frequencies', 'levels', 'lines', 'pathways', 'route_sub_agencies', 'routes', 'shapes_line',
                  'stop_times', 'stops', 'transfers', 'translations', 'trips', 'zones']

        for subLayer in subLayers:
            name = subLayer.split(QgsDataProvider.SUBLAYER_SEPARATOR)[1]
            gpkg_layers.append(name)

        for gpkg_layer in gpkg_layers:
            if gpkg_layer not in layers:
                self._deleteLayer(gpkg_layer)