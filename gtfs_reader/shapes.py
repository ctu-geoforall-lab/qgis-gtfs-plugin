from qgis.core import (QgsVectorFileWriter, QgsVectorLayer, QgsFeatureRequest, QgsFeature, QgsField, QgsPoint,
                       QgsProject, QgsGeometry, QgsVectorLayerJoinInfo, QgsSymbol, QgsRendererCategory,
                       QgsCategorizedSymbolRenderer, QgsMessageLog, Qgis, QgsTask)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import QVariant
import sqlite3

from .. import GTFS

class GtfsShapes:
    def __init__(self,gpkg_path):
        self.gpkg_path = gpkg_path
        self.gtfs = GTFS.LoadTask(gpkg_path)

    def shapes_method(self):
        # create polyline by joining points
        polyline = self._connect_shapes()

        # create polyline file in GPKG
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
        options.driverName = 'GPKG'
        options.layerName = polyline.name()
        QgsVectorFileWriter.writeAsVectorFormat(polyline, self.gpkg_path, options)

        # add shapes_layer to the map canvas
        path_to_layer = self.gpkg_path + '|layername=' + polyline.name()
        # create index on on shape_id_short
        self.gtfs.index(self.gpkg_path, ['shape_id_short'], 'shapes_line')

        self.shapes_layer = QgsVectorLayer(path_to_layer, 'shapes', "ogr")
        # TODO: the way how to load other gtfs then PID
        features_shape = self.shapes_layer.getFeatures()
        for feat in features_shape:
            if str(feat['shape_id_short']) == 'NULL':
                possible_join = -1
            else:
                possible_join = 1
        if possible_join != -1:
            self._set_line_colors(self.shapes_layer)
        else:
            QgsMessageLog.logMessage('Colors from routes file were not uploaded!', 'GTFS load', Qgis.Warning)

        # add shapes_layer to canvas
        QgsProject.instance().addMapLayer(self.shapes_layer, False)

    # The function create polyline by joining the points from point layer "shapes" and adds information to the attribute table
    def _connect_shapes(self):
        path_to_shapes = self.gpkg_path + "|layername=" + 'shapes_point'
        layer = QgsVectorLayer(path_to_shapes, 'shapes', "ogr")

        # Index used to decide id field shape_dist_traveled exist
        idx = (layer.fields().indexFromName('shape_dist_traveled'))

        # load attribute table of shapes into variable features
        features = layer.getFeatures()

        # selecting unique id of shapes from features
        IDList = []
        for feat in features:
            id = feat['shape_id']
            IDList.append(id)
        uniqueId = list(set(IDList))

        # create polyline layer
        shapes_layer = QgsVectorLayer("LineString?crs=epsg:4326", "shapes_line", "memory")
        pr = shapes_layer.dataProvider()
        layer_provider = shapes_layer.dataProvider()

        # add new fields to polyline layer
        layer_provider.addAttributes(
            [QgsField("shape_id", QVariant.String), QgsField("shape_dist_traveled", QVariant.Double),
             QgsField("shape_id_short", QVariant.String)])
        shapes_layer.updateFields()

        for Id in uniqueId:
            # select rows from attribute table, where shape_id agree with current Id in for-cycle
            expression = ('"shape_id" = \'%s%s\'' % (Id, ''))
            request = QgsFeatureRequest().setFilterExpression(expression)
            features_shape = layer.getFeatures(request)

            # sorting attribute table of features_shape by field shape_pt_sequence
            sorted_f_shapes = sorted(features_shape, key=lambda por: por['shape_pt_sequence'])
            PointList = []
            DistList = []
            # add coordinates of shape points and traveled distance to the list
            for f in sorted_f_shapes:
                point = QgsPoint(f['shape_pt_lon'], f['shape_pt_lat'])
                PointList.append(point)
                if idx != -1:
                    dist = (f['shape_dist_traveled'])
                    DistList.append(dist)

            # create polyline from PointList
            polyline = QgsFeature()
            polyline.setGeometry(QgsGeometry.fromPolyline(PointList))
            if type(Id) == str and Id.find('V') != -1:
                # Create shape id short, used for joining routes
                shape_id_s = Id[0:Id.index('V')]
                # find last distance of each shape
                for j in range(0, len(sorted_f_shapes)):
                    if j == (len(sorted_f_shapes) - 1):
                        Dist = DistList[j]
                # adding features to attribute table of polyline
                polyline.setAttributes([Id, Dist, shape_id_s])
                pr.addFeatures([polyline])
            else:
                polyline.setAttributes([Id])
                pr.addFeatures([polyline])
        shapes_layer.updateExtents()
        self.gtfs.setProgress(85)

        return shapes_layer

    def _set_line_colors(self, shapes_layer):
        layer_routes = QgsProject.instance().mapLayersByName('routes')[0]

        # join
        lineField = 'shape_id_short'
        routesField = 'route_id'
        joinObject = QgsVectorLayerJoinInfo()
        joinObject.setJoinFieldName(routesField)
        joinObject.setTargetFieldName(lineField)
        joinObject.setJoinLayerId(layer_routes.id())
        joinObject.setUsingMemoryCache(True)
        joinObject.setJoinLayer(layer_routes)
        shapes_layer.addJoin(joinObject)

        # coloring
        target_field = 'routes_fid'
        features_shape = shapes_layer.getFeatures()
        myCategoryList = []
        colors = {}
        for f in features_shape:
            r_fid = f['routes_fid']
            if r_fid not in colors:
                colors[r_fid] = (f['routes_route_color'], f['routes_route_short_name'])

        for r_fid, r_item in colors.items():
            symbol = QgsSymbol.defaultSymbol(shapes_layer.geometryType())
            symbol.setColor(QColor('#' + r_item[0]))
            myCategory = QgsRendererCategory(r_fid, symbol, r_item[1])
            myCategoryList.append(myCategory)
            myRenderer = QgsCategorizedSymbolRenderer(target_field, myCategoryList)
            shapes_layer.setRenderer(myRenderer)
        shapes_layer.triggerRepaint()
        self.gtfs.setProgress(95)
