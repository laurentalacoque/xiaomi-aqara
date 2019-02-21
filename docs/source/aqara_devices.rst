aqara_device module
===================

.. automodule:: aqara_devices

CallbackHandler
---------------

.. autoclass:: CallbackHandler
    :members:
    :private-members:

AqaraRoot class
---------------

.. inheritance-diagram:: AqaraRoot

.. autoclass:: AqaraRoot
    :members:
    :inherited-members:

KnowDevices class
-----------------

.. autoclass:: KnownDevices
    :members:
    :inherited-members:


AqaraDevice class
-----------------

.. inheritance-diagram:: AqaraDevice AqaraSensor AqaraWeather AqaraMotion AqaraMagnet AqaraSwitch AqaraCube AqaraController AqaraGateway 

.. autoclass:: AqaraDevice
    :members:
    :inherited-members:

.. autoclass:: AqaraSensor
    :members:
    :inherited-members:

Data classes
------------

.. inheritance-diagram:: SwitchStatusData MotionStatusData MagnetStatusData NumericData LuxData IlluminationData CubeRotateData NoMotionData VoltageData WeatherData TemperatureData PressureData HumidityData

The Data class
++++++++++++++

.. autoclass:: Data 
    :members:
    :inherited-members:

Children of the Data class
++++++++++++++++++++++++++

.. autoclass:: MotionStatusData
    :members:

.. autoclass:: MagnetStatusData 
    :members:

.. autoclass:: CubeStatusData 
    :members:

.. autoclass:: SwitchStatusData
    :members:

.. autoclass:: RGBData 
    :members:

.. autoclass:: IPData 
    :members:

The NumericData class
+++++++++++++++++++++

.. autoclass:: NumericData
    :members:
    :inherited-members:


Children of the NumericData class
+++++++++++++++++++++++++++++++++

.. autoclass:: LuxData 
    :members:
    
.. autoclass:: IlluminationData 
    :members:
    
.. autoclass:: CubeRotateData
    :members:

.. autoclass:: NoMotionData
    :members:
    
.. autoclass:: VoltageData
    :members:
    
.. autoclass:: WeatherData
    :members:
    
.. autoclass:: TemperatureData
    :members:
    
.. autoclass:: PressureData
    :members:
    
.. autoclass:: HumidityData
    :members:
    
