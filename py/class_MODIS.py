#!/usr/bin/env python
# coding: utf-8

# In[188]:


import os
import numpy as np
import pandas as pd
import ftputil
import geopandas as gpd
from datetime import datetime, timedelta
import subprocess
import re
from pyproj import Transformer
from sklearn.neighbors import KNeighborsRegressor, KNeighborsClassifier
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
import matplotlib.patheffects as pe
import matplotlib.animation as animation
from IPython.display import HTML




def MODIS_extract(path, product, var, tiles, factor=None, dateslim=None, extent=None, verbose=True):
    """Extrae los datos de MODIS para un producto, variable y fechas dadas, transforma las coordenadas y recorta a la zona de estudio.
    
    Entradas:
    ---------
    path:       string. Ruta donde se encuentran los datos de MODIS (ha de haber una subcarpeta para cada producto)
    product:    string. Nombre del producto MODIS, p.ej. MOD16A2
    var:        string. Variable de interés dentro de los archivos 'hdf'
    factor:     float. Factor con el que multiplicar los datos para obtener su valor real (comprobar en la página de MODIS para el producto y variable de interés)
    tiles:      list. Hojas del producto MODIS a tratar
    dateslim:   list. Fechas de inicio y fin del periodo de estudio en formato YYYY-MM-DD. Si es 'None', se extraen los datos para todas las fechas disponibles
    clip:       string. Ruta y nombre del archivo ASCII que se utilizará como máscara para recortar los datos. Si es 'None', se extraen todos los datos
    coordsClip: pyproj.CRS. Proj del sistema de coordenadas al que se quieren transformar los datos. Si en 'None', se mantiene el sistema de coordenadas sinusoidal de MODIS
    verbose:    boolean. Si se quiere mostrar en pantalla el desarrollo de la función
    
    Salidas:
    --------
    Como métodos:
        data:    array (Y, X) o (dates, Y, X). Mapas de la variable de interés. 3D si hay más de un archivo (más de una fecha)
        Xcoords: array (2D). Coordenadas X de cada celda de los mapas de 'data'
        Ycoords: array (2D). Coordenadas Y de cada celda de los mapas de 'data'
        dates:   list. Fechas a las que corresponde cada uno de los maapas de 'data'
    """    
    
    if os.path.exists(path + product + '/') is False:
        os.makedirs(path + product + '/')
    os.chdir(path + product + '/')
    
    # SELECCIÓN DE ARCHIVOS
    # ---------------------
    if dateslim is not None:
        # convertir fechas límite en datetime.date
        start = datetime.strptime(dateslim[0], '%Y-%m-%d').date()
        end = datetime.strptime(dateslim[1], '%Y-%m-%d').date()
    
    dates, files = {tile: [] for tile in tiles}, {tile: [] for tile in tiles}
    for tile in tiles:
        # seleccionar archivos del producto para las hojas y fechas indicadas
        for file in [f for f in os.listdir() if (product in f) & (tile in f)]:
            year = file.split('.')[1][1:5]
            doy = file.split('.')[1][5:]
            date = datetime.strptime(' '.join([year, doy]), '%Y %j').date()
            if dateslim is not None:
                if (date>= start) & (date <= end):
                    dates[tile].append(date)
                    files[tile].append(file)
            else:
                dates[tile].append(date)
                files[tile].append(file)
    # comprobar que el número de archivos es igual en todas las hojas
    if len(set([len(dates[tile]) for tile in tiles])) > 1:
        print('¡ERROR! Diferente número de fechas en las diferentes hojas')
        MODIS_extract.files = files
        MODIS_extract.dates = dates
        return 
    else:
        dates = np.sort(np.unique(np.array([date for tile in tiles for date in dates[tile]])))
        if verbose:
            print('Seleccionar archivos')
            print('nº de archivos (fechas): {0:>3}'.format(len(dates)), end='\n\n')

    # ATRIBUTOS MODIS
    # ---------------
    if verbose:
        print('Generar atributos globales')
    # extraer atributos para cada hoja
    attributes = pd.DataFrame(index=tiles, columns=['ncols', 'nrows', 'Xo', 'Yf', 'Xf', 'Yo'])
    for tile in tiles:
        attributes.loc[tile,:] = hdfAttrs(files[tile][0])

    # extensión total
    Xo = np.min(attributes.Xo)
    Yf = np.max(attributes.Yf)
    Xf = np.max(attributes.Xf)
    Yo = np.min(attributes.Yo)
    # nº total de columnas y filas
    colsize = np.mean((attributes.Xf - attributes.Xo) / attributes.ncols)
    ncols = int(round((Xf - Xo) / colsize, 0))
    rowsize = np.mean((attributes.Yf - attributes.Yo) / attributes.nrows)
    nrows = int(round((Yf - Yo) / rowsize, 0))
    if verbose == True:
        print('dimensión:\t\t({0:}, {1:})'.format(ncols, nrows))
        print('esquina inf. izqda.:\t({0:>10.2f}, {1:>10.2f})'.format(Xo, Yo))
        print('esquina sup. dcha.:\t({0:>10.2f}, {1:>10.2f})'.format(Xf, Yf), end='\n\n')

    # coordenadas x de las celdas
    Xmodis = np.linspace(Xo, Xf, ncols)
    # coordenadas y de las celdas
    Ymodis = np.linspace(Yf, Yo, nrows)
        
    # CREAR MÁSCARAS
    # --------------
    if extent is not None:
        if verbose == True:
            print('Crear máscaras')
            
        # crear máscara según la extensión
        left, right, bottom, top =  extent
        maskCols = (Xmodis >= left) & (Xmodis <= right)
        maskRows = (Ymodis >= bottom) & (Ymodis <= top)
        
        # recortar coordenadas
        Xmodis = Xmodis[maskCols]
        Ymodis = Ymodis[maskRows]
        
        if verbose == True:
            print('dimensión:\t\t({0:>4}, {1:>4})'.format(len(Ymodis), len(Xmodis)))
            print('esquina inf. izqda.:\t({0:>10.2f}, {1:>10.2f})'.format(Xmodis.min(), Ymodis.min()))
        print('esquina sup. dcha.:\t({0:>10.2f}, {1:>10.2f})'.format(Xmodis.max(), Ymodis.max()),
              end='\n\n')

    # IMPORTAR DATOS
    # --------------
    if verbose:
        print('Importar datos')
        
    for d, date in enumerate(dates):
        dateStr = str(date.year) + str(date.timetuple().tm_yday).zfill(3)

        for t, tile in enumerate(tiles):
            print('Fecha {0:>2} de {1:>2}: {2}\t||\tTile {3:>2} de {4:>2}: {5}'.format(d + 1, len(dates), date,
                                                                                       t + 1, len(tiles), tile), end='\r')
            
            # localización de la hoja dentro del total de hojas
            nc, nr, xo, yf, xf, yo = attributes.loc[tile, :]
            i = int(round((Yf - yf) / (rowsize * attributes.nrows[t]), 0))
            j = int(round((Xf - xf) / (colsize * attributes.ncols[t]), 0))

            # archivo de la fecha y hoja dada
            file = [f for f in files[tile] if dateStr in f][0]
            # cargar archivo 'hdf'
            hdf = Dataset(file, format='hdf4')
            # extraer datos de la variable
            tmp = hdf[var][:]
            tmp = tmp.astype(float)
            tmp[tmp.mask] = np.nan
            hdf.close()
            # guardar datos en un array global de la fecha
            if t == 0:
                dataD = tmp.copy()
            else:
                if (i == 1) & (j == 0):
                    dataD = np.concatenate((dataD, tmp), axis=0)
                elif (i == 0) & (j == 1):
                    dataD = np.concatenate((dataD, tmp), axis=1)
            del tmp
        
        # recortar array de la fecha con la máscara
        if extent is not None:
            dataD = dataD[maskRows, :][:, maskCols]
            
        # guardar datos en un array total
        if d == 0:
            data = dataD.copy()
        else:
            data = np.dstack((data, dataD))
        del dataD
    print()
    
    # multiplicar por el factor de escala (si existe)
    if factor is not None:
        data *= factor
        
    # reordenar el array (tiempo, Y, X)
    if len(data.shape) == 3:
        tmp = np.ones((data.shape[2], data.shape[0], data.shape[1])) * np.nan
        for t in range(data.shape[2]):
            tmp[t,:,:] = data[:,:,t]
        data = tmp.copy()
        del tmp

    # GUARDAR RESULTADOS
    # ------------------
    modis = MODIS(data, Xmodis, Ymodis, dates, crs=sinusoidal)
    
    return modis





# sistema de proyección de MODIS
# https://spatialreference.org/ref/sr-org/modis-sinusoidal/
sinusoidal = CRS.from_proj4('+proj=sinu +lon_0=0 +x_0=0 +y_0=0 +a=6371007.181 +b=6371007.181 +units=m +no_defs ')




class MODIS:
    def __init__(self, data, X, Y, times, units=None, variable=None, label=None, crs=sinusoidal):
        """Clase que contiene la información relevante de las predicciones del modelo HARMONIE para una variable concreta.
        
        Entradas:
        ---------
        data:    array (times, Y, X). Matriz con los datos de la predicción de HARMONIE
        X:       array (X,). Coordenadas X (m o grados) de las columnas de la matriz 'data'
        Y:       array (Y,). Coordenadas Y (m o grados) de las files de la matriz 'data'
        times:   array (times,). Fecha y hora de cada uno de los pasos temporales de 'data'
        units:   string. Unidades de la variable. P.ej. 'mm'
        variable: string. Descripción de la variable. P.ej. 'precipitación total'
        label:    string. Etiqueta de la variable. P.ej. 'APCP'
        crs:      string o callable. Sistema de coordenadas de referencia. Los datos originales están en 'epsg:4258'
        """
        
        self.data = data
        self.X = X
        self.Y = Y
        self.times = times
        self.units = units
        self.variable = variable
        self.label = label
        self.crs = crs
        
        
    def recortar(self, poligono, buffer=None, inplace=False):
        """Recorta los datos de MODIS según el polígono.

        Entradas:
        ---------
        self:      class MODIS
        poligono:  geopandas.GeoDataframe. Polígono con el que recortar los mapas
        buffer:    float. Distancia a la que hacer una paralela al polígono antes del recorte
        inplace:   boolean. Si se quiere sobreescribir el resultado sobre self o no
        
        Salidas:
        --------
        Si 'inplace == False':
            modis: class MODIS
        """
        
        # extraer información de 'HARMONIE'
        X, Y = self.X, self.Y
        data = self.data

        # buffer
        if buffer is not None:
            poligono = poligono.buffer(buffer)

        # definir crs del polígono
        if self.crs != poligono.crs:
            poligono = poligono.to_crs(self.crs)

        # extensión de la cuenca
        Xbo, Ybo, Xbf, Ybf = poligono.bounds.loc[0,:]
        # buffer
        if buffer is not None:
            Xbo -= buffer
            Ybo -= buffer
            Xbf += buffer
            Ybf += buffer

        # recortar según la extensión de la cuenca
        maskC = (X >= Xbo) & (X <= Xbf)
        maskR = (Y >= Ybo) & (Y <= Ybf)
        data = data[:,maskR,:][:,:,maskC]
        X = X[maskC]
        Y = Y[maskR]

        # GeoDataFrame de puntos de la malla MODIS
        XX, YY = np.meshgrid(X.flatten(), Y.flatten())
        points = gpd.GeoDataFrame(geometry=gpd.points_from_xy(XX.flatten(), YY.flatten(), crs=self.crs))

        # máscara del polígono
        inp, res = poligono.sindex.query_bulk(points.geometry, predicate='intersects')
        mask = np.isin(np.arange(len(points)), inp)
        mask2D = mask.reshape(XX.shape)

        # máscara 3D a partir de la anterior
        mask3D = np.zeros(data.shape, dtype=bool)
        mask3D[:,:,:] = mask2D[np.newaxis,:,:]
        
        # recortar mapa al área del polígono
    #     data_ma = np.ma.masked_array(data, ~mask3D)
        data_ma = data.copy()
        data_ma[~mask3D] = np.nan

        # eliminar filas y columnas sin datos
        maskR = np.isnan(data_ma.sum(axis=0)).all(axis=1)
        maskC = np.isnan(data_ma.sum(axis=0)).all(axis=0)
        data_ma = data_ma[:,~maskR,:][:,:,~maskC]
    #     data_ma = np.ma.masked_invalid(data_ma)
        Y = Y[~maskR]
        X = X[~maskC]
        
        if inplace:
            self.data = data_ma
            self.X = X
            self.Y = Y
            self.mask3D = mask3D
        else:
            # crear diccionario con los resultados  
            modis = MODIS(data_ma, X, Y, self.times, crs=self.crs)
            modis.mask3D = mask3D
            return modis
        

    def reproyectar(self, crsOut, cellsize, n_neighbors=1, weights='distance', p=2, inplace=False):
        """Proyecta la malla de MODIS desde su sistema de coordenadas original (sinusoidal) al sistema deseado en una malla regular de tamaño definido.

        Entradas:
        ---------
        self:        class MODIS
        crsOut:      CRS. Sistema de coordenadas de referencia al que se quieren proyectar los datos. P.ej. 'epsg:25830'
        cellsize:    float. Tamaño de celda de la malla a generar
        n_neighbors: int. Nº de celdas cercanas a utilizar en la interpolación
        weights:     str. Tipo de ponderación en la interpolación
        p:           int. Exponente de la ponderación
        inplace:   boolean. Si se quiere sobreescribir el resultado sobre self o no

        Salida:
        -------
        Si 'inplace == False':
            harmonie: class HARMONIE
        """

        # extraer información de HARMONIE
        data = self.data
        Y = self.Y
        X = self.X
        times = self.times
        crsIn = self.crs

        # matrices de longitud y latitud de cada una de las celdas
        XX, YY = np.meshgrid(X, Y)

        # transformar coordendas y reformar en matrices del mismo tamaño que el mapa diario
        transformer = Transformer.from_crs(crsIn, crsOut) 
        Xorig, Yorig = transformer.transform(XX.flatten(), YY.flatten())
        XXorig = Xorig.reshape(XX.shape)
        YYorig = Yorig.reshape(YY.shape)

        # definir límites de la malla a interpolar
        xmin, xmax, ymin, ymax = Xorig.min(), Xorig.max(), Yorig.min(), Yorig.max()
        # redondear según el tamaño de celda
        xmin = int(np.floor(xmin / cellsize) * cellsize)
        xmax = int(np.ceil(xmax / cellsize) * cellsize)
        ymin = int(np.floor(ymin / cellsize) * cellsize)
        ymax = int(np.ceil(ymax / cellsize) * cellsize)

        # coordenadas X e Y de la malla a interpolar
        Xgrid = np.arange(xmin, xmax + cellsize, cellsize)
        Ygrid = np.arange(ymin, ymax + cellsize, cellsize)

        # matrices de X e Y de cada una de las celdas de la malla a interpolar
        XXgrid, YYgrid = np.meshgrid(Xgrid, Ygrid)

        # interpolar mapas en la malla UTM
        data_ = np.empty((len(times), len(Ygrid), len(Xgrid)), dtype=float)
        for t, time in enumerate(times):
            print('Paso {0} de {1}:\t{2}'.format(t+1, len(times), time), end='\r')
            data_[t,:,:] = interpolarNN(XXorig, YYorig, data[t,:,:], XXgrid, YYgrid, datatype,
                                        n_neighbors=n_neighbors,  weights=weights, p=p)
        
        if inplace:
            self.data = data_
            self.X = Xgrid
            self.Y = Ygrid
            self.crs = crsOut
        else:
            # crear nueva instancia de clase HARMONIE
            modis = MODIS(data_, Xgrid, Ygrid, self.times, crs=crsOut)#, self.units, self.variable, self.label, crsOut)
            return modis




def interpolarNN(XXorig, YYorig, mapa, XXgrid, YYgrid, n_neighbors=1, weights='distance', p=1):
    """Interpolar un mapa desde una malla original a otra malla regular. Se utiliza el algoritno de vencinos cercanos.
    Utilizando como pesos 'distance' y como exponente 'p=2' es el método de la distancia inversa al cuadrado.
    
    Entradas:
    ---------
    XXorig:      np.array (r1, c1). Coordenadas X de los puntos del mapa de origen
    YYorig:      np.array (r1, cw). Coordenadas Y de los puntos del mapa de origen
    mapa:        np.array (r1, c1). Valores de la variable en los puntos del mapa de origen
    XXgrid:      np.array (r2, c2). Coordenadas X de los puntos del mapa objetivo
    YYgrid:      np.array (r2, c2). Coordenadas Y de los puntos del mapa objetivo
    n_neighbors: int. Nº de vecinos cercanos, es decir, los puntos a tener en cuenta en la interpolación de cada celda de la malla.
    weights:     str. Tipo de ponderación: 'uniform', 'distance'
    p:           int. Exponente al que elevar 'weights' a la hora de ponderar
    
    Salida:
    -------
    pred:         np.array (r2, c2). Valores de la varible interpolados en la mall objetivo
    """
    
    # AJUSTE
    # ......
    # target array
    if isinstance(mapa, np.ma.MaskedArray):
        y = mapa.data.flatten().astype(float)
    else:
        y = mapa.flatten().astype(float)
    mask = np.isnan(y)
    y = y[~mask]
    # feature matrix
#     XXorig, YYorig = np.meshgrid(Xorig, Yorig)
    X = np.vstack((XXorig.flatten(), YYorig.flatten())).T
    X = X[~mask,:]
    # definir y ajustar el modelo
    neigh = KNeighborsRegressor(n_neighbors=n_neighbors, weights=weights, p=p).fit(X, y)
    
    # PREDICCIÓN
    # ..........
    # feauture matrix
#     XXgrid, YYgrid = np.meshgrid(Xgrid, Ygrid)
    X_ = np.vstack((XXgrid.flatten(), YYgrid.flatten())).T
    # predecir
    pred = neigh.predict(X_).reshape(XXgrid.shape)
    
    return pred




