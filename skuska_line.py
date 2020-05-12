import os
import pandas as pd

os.chdir('C:\Users\Saul\Documents\Ih_CreateLineFromPointswithPyQGIS')
lista = os.listdir(os.getcwd())
print(lista)

datos = pd.read_csv(lista[1],parse_dates=True,index_col=1)
datos.sort_index(inplace=True)
print(datos.head())

PointList = []

for index, row in datos.iterrows():
    termino = QgsPoint(float(row['longitude']),float(row['latitude']))
    
    PointList.append(termino)
    
print(PointList)

linea = iface.addVectorLayer("LineString?crs=epsg:4326&field=id:integer&index=yes","Linea","memory")
linea.startEditing()
feature = QgsFeature()
feature.setGeometry(QgsGeometry.fromPolyline(PointList))
feature.setAttributes([1])
linea.addFeature(feature,True)
linea.commitChanges()
iface.zoomToActiveLayer()
 