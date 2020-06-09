Description
---------------

Download data (ZIP file) from the `PID <https://pid.cz/o-systemu/opendata/>`__ page:

.. image:: images/download.png
   :width: 800

In **GTFS load** plugin window enter path to ZIP the file:

.. image:: images/select.png
   :width: 400

.. note:: It is only possible to insert a ZIP file.

When you press **Load**, a warning pops up. The process can take several minutes. It depends on the amount of data.

.. image:: images/warning.png
   :width: 200

After loading the data, the individual layers will be displayed in the layer tree and the lines of individual lines will be displayed in the map window.

Visualization:

.. image:: images/output.png
   :width: 800

The line colors match the PID definition and are added to the lines based on the line join with the colors defined in routes.txt.
A warning will appear if the colors cannot be loaded.

.. image:: images/colors.png
   :width: 300