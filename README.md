# MODIS
Conjunto de herramientas para trabajar con datos de [MODIS](https://modis.gsfc.nasa.gov/) (MODerate resolution Imaging Spectroradiometer) en hidrología. Como localización de prueba, se descargan y generan las series para la cuenca del Deva para la evapotranspiración, LAI/FPAR e índices de vegetación.

Se incluyen además funciones para el análisis de __EOF (_empirical ortogonal functions_)__. Estas funciones se aplican a las series de mapas de MODIS para la cuenca del Deva.

La organización del repositorio es la siguiente:
* [_data_](https://github.com/casadoj/MODIS/tree/master/data) contiene los datos para el ejemplo de prueba en la cuenca del Deva.
* [_docs_](https://github.com/casadoj/MODIS/tree/master/docs) contiene los _Jupyter notebooks_ para la descarga y análisis de los datos.
* [_src_](https://github.com/casadoj/MODIS/tree/master/src) contiene el código fuente, es decir, los archivos _py_ con las funciones desarrolladas para poder ser usadas desde otros repositorios.
* [ output_](https://github.com/casadoj/MODIS/tree/master/output) contiene las salidas del análisis. Se subdivide a su vez en carpetas para cada una de las variables estudiadas: evapotranspiración (ET), fracción de radiación fotosintéticamente activa y _leaf area index_ (FPAR/LAI) e índices de vegetación (VI.
