# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GTFS
                                 A QGIS plugin
 Otevírám GTFS.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2020-03-26
        git sha              : $Format:%H$
        copyright            : (C) 2020 by Skupina B
        email                : martin.kouba@fsv.cvut.cz
 ***************************************************************************/
/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
# Initialize Qt resources from file resources.py
from .resources import *

# Import the code for the DockWidget
from .GTFS_dockwidget import GTFSDockWidget
import os.path

from PyQt5.QtGui import QColor, QPixmap
from PyQt5.QtWidgets import QFileDialog
from qgis.utils import iface
from qgis.core import *
from qgis.gui import *

from zipfile import ZipFile

import os.path

class GTFS:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.
        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface

        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)

        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'GTFS_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&GTFS load')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'GTFS')
        self.toolbar.setObjectName(u'GTFS')

        #print "** INITIALIZING GTFS"

        self.pluginIsActive = False
        self.dockwidget = None


    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.
        We implement this ourselves since we do not inherit QObject.
        :param message: String for translation.
        :type message: str, QString
        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('GTFS', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.
        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str
        :param text: Text that should be shown in menu items for this action.
        :type text: str
        :param callback: Function to be called when the action is triggered.
        :type callback: function
        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool
        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool
        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool
        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str
        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget
        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.
        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action


    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/GTFS/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'GTFS Load'),
            callback=self.run,
            parent=self.iface.mainWindow())

    #--------------------------------------------------------------------------

    def onClosePlugin(self):
        """Cleanup necessary items here when plugin dockwidget is closed"""

        #print "** CLOSING GTFS"

        # disconnects
        self.dockwidget.closingPlugin.disconnect(self.onClosePlugin)

        # remove this statement if dockwidget is to remain
        # for reuse if plugin is reopened
        # Commented next statement since it causes QGIS crashe
        # when closing the docked window:
        # self.dockwidget = None

        self.pluginIsActive = False


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""

        #print "** UNLOAD GTFS"

        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&GTFS load'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    #--------------------------------------------------------------------------

    def run(self):
        """Run method that loads and starts the plugin"""

        if not self.pluginIsActive:
            self.pluginIsActive = True

            #print "** STARTING GTFS"

            # dockwidget may not exist if:
            #    first run of plugin
            #    removed on close (see self.onClosePlugin method)
            if self.dockwidget == None:
                self.browsePathSetting="/plugins/2020-b-qgis-gtfs-plugin"
                self._home = QSettings().value(self.browsePathSetting,'')
                # Create the dockwidget (after translation) and keep reference
                self.dockwidget = GTFSDockWidget()
 #               self.dockwidget.soubory.setFilters(QgsMapLayerProxyModel.VectorLayer)
                self.dockwidget.browse.clicked.connect(self.browse_file)
                self.dockwidget.submit.clicked.connect(self.load_file)

            # connect to provide cleanup on closing of dockwidget
            self.dockwidget.closingPlugin.connect(self.onClosePlugin)

            # show the dockwidget
            # TODO: fix to allow choice of dock location
            self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.dockwidget)
            self.dockwidget.show()
            
    def browse_file(self):        
        filename = QFileDialog.getOpenFileName(self.dockwidget,"Select file", self._home, "GTFS (*.zip)")[0]
        if filename:
            self.dockwidget.input_dir.setText(filename)   
            
    def load_file(self):
        # Load file - function that reads a GTFS ZIP file. 
        #path = self.dockwidget.input_dir.filePath()
        path = self.dockwidget.input_dir.text()
        if not path.endswith('.zip'):
            self.iface.messageBar().pushMessage(
            "Error", "Please upload a zipfile", level=Qgis.Critical)
        else:
            name = os.path.splitext(os.path.basename(path))[0]
            # Create a folder for files. 
            path1 = os.path.join(os.path.dirname(path), name)

            os.mkdir(path1) 
            # Extracts files to path. 
            with ZipFile(path, 'r') as zip: 
                # printing all the contents of the zip file 
                zip.printdir() 
                zip.extractall(path1) 
            # Select text files only. 
            print(path1)
            print(path)
            files = []
            # r=root, d=directories, f = files
            for r, d, f in os.walk(path1):
                for file in f:
                    exten = os.path.splitext(os.path.basename(file))[1]
                    if exten == '.txt':
                        files.append(os.path.join(r, file))

            # Load text files to Layers and add vector layers to map.
            for f in files:
                #f = self.dockwidget.input_dir.filePath()
                
                uri = 'file:///{}?delimiter=,'.format(f)
                print(uri)

                name = os.path.splitext(os.path.basename(f))[0]
                layer = QgsVectorLayer(uri, '{}'.format(name), 'delimitedtext')
                print(layer.isValid())
                if layer.name()== 'stops':
                    uri = 'file:///{}?delimiter=,&xField=stop_lon&yField=stop_lat&crs=epsg:4326'.format(f)
                    name = os.path.splitext(os.path.basename(f))[0]
                    layer = QgsVectorLayer(uri, name, 'delimitedtext')
                    QgsProject.instance().addMapLayer(layer)
                if layer.name()== 'shapes':
                    uri = 'file:///{}?delimiter=,&xField=shape_pt_lon&yField=shape_pt_lat&crs=epsg:4326'.format(f)
                    name = os.path.splitext(os.path.basename(f))[0]
                    layer_stop = QgsVectorLayer(uri, name, 'delimitedtext')
                    QgsProject.instance().addMapLayer(layer_stop)       
                else:
                    QgsProject.instance().addMapLayer(layer)
            options = QgsVectorFileWriter.SaveVectorOptions()
            options.driverName = 'GPKG'
            options.layerName = 'shapes'  
            error_message = QgsVectorFileWriter.writeAsVectorFormat(layer_stop,path1,options)
            
            layer = QgsProject.instance().mapLayersByName("shapes")[0]
            features = layer.getFeatures()
            hodList=[]
            for feat in features:
                ids=feat['shape_id']
                hodList.append(ids)
            unikatniId=list(set(hodList))


            v_layer = QgsVectorLayer("LineString?crs=epsg:4326", "line", "memory")
            pr = v_layer.dataProvider()
            ## I do believe that you want to store resulting lines in one layer,
            ## so these lines should be moved from internal for loop


            for i in unikatniId:
                expression = ('"shape_id" LIKE \'%s%s\''%(i,'%'))
                request = QgsFeatureRequest().setFilterExpression(expression)
                PointList = []

                line=QgsFeature()
                for f in layer.getFeatures(request):

                    termino = QgsPoint(f['shape_pt_lon'],f['shape_pt_lat']) #I do understand that shape_pt_lon and shape_pt_lat are columns containing coordinates 
                    ## definitely you want to use f rather then feat. 
                    ## Feat was returning last scanned point,
                    ## that is why you were getting empty lines
                    ## (actually they were lines consisting of one point) 

                    PointList.append(termino)

                line.setGeometry(QgsGeometry.fromPolyline(PointList))
                pr.addFeatures( [ line ] )
                ## indenting might be reason of logical errors.
                ## You probably want to add line only once for given unikatniId
                ## so take it outside of "f" loop

            v_layer.updateExtents()
            QgsProject.instance().addMapLayers([v_layer])
            ## And finally add shape to MapLayers, but only once
            ## (if you want to have one layer with resulting lines)