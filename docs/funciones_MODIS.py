#!/usr/bin/env python
# coding: utf-8

# _Autor:_    __Jesús Casado__ <br> _Revisión:_ __21/01/2020__ <br>
# 
# __Introducción__<br>
# Código con funciones para la descarga y tratamiento de datos MODIS.
# 
# Los datos MODIS se descargan del [servidor USGS](https://e4ftl01.cr.usgs.gov/). En dicho enlace se pueden ver las misiones, productos y fechas disponibles. Para poder descargar datos del servidor, es necesario estar registrado en https://urs.earthdata.nasa.gov/.
# 
# En el tratamiento de datos se incluye una función para extraer los datos de un producto para la variable, fechas y cuenca de interés.
# 
# __Cosas que arreglar__ <br>
# 
# ***
# __Índice__<br>
# __[Descarga de datos MODIS](#Descarga-de-datos-MODIS)__<br>
# 
# __[Tratamiento de datos MODIS](#Tratamiento-de-datos-MODIS)__<br>

# In[1]:


import os
import requests
import urllib
from http.cookiejar import CookieJar
from bs4 import BeautifulSoup
from datetime import datetime


# In[6]:


import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
# plt.style.use('seaborn-whitegrid')
plt.style.use('dark_background')
get_ipython().run_line_magic('matplotlib', 'inline')
from netCDF4 import Dataset
import h5py
from datetime import datetime, timedelta

import os

from pyproj import Proj, transform#, CRS
os.environ['PROJ_LIB'] = r'C:\Anaconda3\pkgs\proj4-4.9.3-vc14_5\Library\share'


# In[5]:


import requests
url = 'https://raw.githubusercontent.com/casadoj/Calibrar/master/read_write.py'
r = requests.get(url).text
exec(r)


# ### Descarga de datos MODIS

# In[ ]:


def EarthdataLogin(username, password, url='https://urs.earthdata.nasa.gov'):
    """Entra en la cuenta de usuario de Earthdata, con lo que se obtiene permiso para descargar .hdf, y crea un contenedor de las 'cookies' en la sesión.
    
    Modificado de https://wiki.earthdata.nasa.gov/display/EL/How+To+Access+Data+With+Python
    
    Entradas:
    ---------
    username: string. Nombre de usuario en Earthdata
    password: string. Contraseña en Earthdata
    url:     string. URL del servidor de datos; por defecto 'https://e4ftl01.cr.usgs.gov/'
    """
    
    # Create a password manager to deal with the 401 reponse that is returned from Earthdata Login
    password_manager = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    password_manager.add_password(None, "https://urs.earthdata.nasa.gov", username, password)
    
    # Create a cookie jar for storing cookies. This is used to store and return
    # the session cookie given to use by the data server (otherwise it will just
    # keep sending us back to Earthdata Login to authenticate).  Ideally, we
    # should use a file based cookie jar to preserve cookies between runs. This
    # will make it much more efficient.
    cookie_jar = CookieJar()
    
    # Install all the handlers.
    opener = urllib.request.build_opener(urllib.request.HTTPBasicAuthHandler(password_manager),
                                         #urllib.request.HTTPHandler(debuglevel=1),    # Uncomment these two lines to see
                                         #urllib.request.HTTPSHandler(debuglevel=1),   # details of the requests/responses
                                         urllib.request.HTTPCookieProcessor(cookie_jar))
    urllib.request.install_opener(opener)


# In[ ]:


def extract_dir(url, ext='/'):
    """Extrae los directorios existentes en una url.
    
    Entradas:
    ---------
    ulr:     string. Dirección url
    ext:     string. Caracter a buscar al final de cada nodo de la url para idenficarlo como un nuevo directorio"""
    
    # extrae el texto de la url
    page = requests.get(url).text
    # traduce el texto
    soup = BeautifulSoup(page, 'html.parser')
    # extrae las líneas del texto terminadas en 'ext'
    list_dir = [url + node.get('href') for node in soup.find_all('a') if node.get('href').endswith(ext)]
    
    return list_dir


# In[ ]:


def descarga_MODIS(username, password, path, product, start=None, end=None, tiles=None,
                   url='https://e4ftl01.cr.usgs.gov/', format='hdf'):
    """Descarga los archivos del producto MODIS de interés en las fechas, hojas y formato indicados.
    
    Entradas:
    ---------
    username: string. Nombre de usuario en Earthdata
    password: string. Contraseña en Earthdata
    path:    string. Carpeta donde guardar los datos descargados.
    product: string. Producto MODIS. P.ej.: 'MOD16A2.006', 'MYD16A2.006'
    start:   string. Fecha a partir de la que descargar datos. Formato 'YYYY-MM-DD'
    end:     string. Fecha hasta la que descargar datos. Formato 'YYYY-MM-DD'
    tiles:   list of strings. Hojas MODIS a descargar. Formato 'h00v00'
    url:     string. URL del servidor de datos; por defecto 'https://e4ftl01.cr.usgs.gov/'
    format:  string. Tipo de archivo a descargar: 'hdf', 'jpg', 'xml'
    
    Salidas:
    --------
    Se guardan en la carpeta 'path/product' los archivos (hdf, jpg o xml) para la selección indicada."""
    
    # entrar en Earth data con el usuario
    EarthdataLogin('casadoj', 'Chomolungma1619', url=url)
    
    # definir carpeta donde guardar los datos
    exportpath = path + '/' + product.split('.')[0] + '/'
    if os.path.isdir(exportpath) == False:
        os.mkdir(exportpath)
    os.chdir(exportpath)
    lsdir = os.listdir()
    
    # url de cada una de las misiones
    url_missions = extract_dir(url)
    # diccionario con las missiones y sus productos
    mission_products = {}
    for fd1 in url_missions:
        mission = fd1.split('/')[-2]
        url_products = extract_dir(fd1)
        products = [fd2.split('/')[-2] for fd2 in url_products if fd2.split('/')[-2] != '']
        mission_products[mission] = products

    # encontrar missión del producto de interés y url del producto
    for fd, mission in zip(url_missions, mission_products.keys()):
        if product in mission_products[mission]:
            urlproduct = fd + product + '/'
            break
    
    # convertir en datetime.date las fechas de inicio y fin de la búsqueda           
    if start != None:
        start = datetime.strptime(start, '%Y-%m-%d').date()
    else:
        start = datetime(1950, 1, 1).date()
    if end != None:        
        end = datetime.strptime(end, '%Y-%m-%d').date()
    else:
        end = datetime.now().date()
        
    # seleccionar fechas dentro del periodo de interés
    urldates = []
    for fd in extract_dir(urlproduct)[1:]:
        date = datetime.strptime(fd.split('/')[-2], '%Y.%m.%d').date()
        if (start <= date) & (end >= date):
            urldates.append(fd)
            
    for di, urldate in enumerate(urldates):
        # seleccionar archivos correspondientes a las hojas de interés
        urlfiles = extract_dir(urldate, ext='.' + format)
        if tiles == None:
            files = [file.split('/')[-1] for file in urlfiles]
        else:
            files = [file.split('/')[-1] for file in urlfiles if any(tile in file for tile in tiles)]

        # descargar archivos
        for fi, file in enumerate(files):
            print('Fecha {0:>4} de {1:>4}; archivo {2:>3} de {3:>3}'.format(di + 1, len(urldates),
                                                                            fi + 1, len(files)),
                  end='\r')
            if file in lsdir:
                continue
            else:
                urllib.request.urlretrieve(urldate + file, file)


# ### Tratamiento de datos MODIS

# In[ ]:


def ascii2df(pathfile):
    """Importar ASCII en forma de DataFrame
    
    Entradas:
    ---------
    path:    string. Ruta incluyendo nombre del archivo y extensión
    
    Salidas:
    --------
    asc:    data frame. Con las coordenadas en índices y columnas
    """
    
    # mdt de la cuenca
    read_ascii(pathfile)
    asc = read_ascii.data
    ncols, nrows, Xo, Yo, cellsize, nanvalue = read_ascii.attributes
    
    # coordenadas X del centro de las celdas
    Xf = Xo + ncols * cellsize
    Xo += cellsize / 2
    Xf += cellsize / 2
    XXasc = np.arange(Xo, Xf, cellsize).astype('int')
    
    # coordenadas Y del centro de las celdas
    Yf = Yo + nrows * cellsize
    Yo += cellsize / 2
    Yf += cellsize / 2
    YYasc = np.arange(Yo, Yf, cellsize).astype('int')[::-1]
    
    # convertir 'asc' en un DataFrame
    asc = pd.DataFrame(data=asc, index=YYasc, columns=XXasc)
    asc.dropna(axis=1, how='all', inplace=True)
    
    return asc


# In[ ]:


def MODIS_extract(path, product, var, atributes, factor=None, dateslim=None, clip=None,
                  coordsClip='epsg:25830', verbose=True):
    """Extrae los datos de MODIS para un producto, variable y fechas dadas, transforma las coordenadas y recorta a la zona de estudio.
    
    Entradas:
    ---------
    path:       string. Ruta donde se encuentran los datos de MODIS (ha de haber una subcarpeta para cada producto)
    product:    string. Nombre del producto MODIS, p.ej. MOD16A2
    var:        string. Variable de interés dentro de los archivos 'hdf'
    atributes:  list. [ncols, nrows, Xtopleft, Ytopleft, Xbottomright, Ybottomright]
    factor:     float. Factor con el que multiplicar los datos para obtener su valore real (comprobar en la página de MODIS para el producto y variable de interés)
    dateslim:   list. Fechas de inicio y fin del periodo de estudio en formato YYYY-MM-DD. Si es 'None', se extraen los datos para todas las fechas disponibles
    clip:       string. Ruta y nombre del archivo ASCII que se utilizará como máscara para recortar los datos. Si es 'None', se extraen todos los datos
    coordsClip: string. Código EPSG o Proj del sistema de coordenadas al que se quieren transformar los datos. Si en 'None', se mantiene el sistema de coordenadas sinusoidal de MODIS
    verbose:    boolean. Si se quiere mostrar en pantalla el desarrollo de la función
    
    Salidas:
    --------
    Como métodos:
        data:    array (2D ó 3D). Mapas de la variable de interés. 3D si hay más de un archivo (más de una fecha)
        Xcoords: array (2D). Coordenadas X de cada celda de los mapas de 'data'
        Ycoords: array (2D). Coordenadas Y de cada celda de los mapas de 'data'
        dates:   list. Fechas a las que corresponde cada uno de los maapas de 'data'
    """
    
    # SELECCIÓN DE ARCHIVOS
    # ---------------------
    if dateslim is not None:
        # convertir fechas límite en datetime.date
        start = datetime.strptime(dateslim[0], '%Y-%m-%d').date()
        end = datetime.strptime(dateslim[1], '%Y-%m-%d').date()

    # seleccionar archivos del producto y fechas dadas
    path = path + product + '/'
    os.chdir(path)
    dates, files = [], []
    for file in [file for file in os.listdir() if product in file]:
        year = file.split('.')[1][1:5]
        doy = file.split('.')[1][5:]
        date = datetime.strptime(' '.join([year, doy]), '%Y %j').date()
        if dateslim is not None:
            if (date>= start) & (date <= end):
                dates.append(date)
                files.append(file)
        else:
            dates.append(date)
            files.append(file)

    # ATRIBUTOS MODIS
    # ---------------
    ncols, nrows, Xo, Yf, Xf, Yo = atributes

    # coordenadas x de las celdas
    Xmodis = np.linspace(Xo, Xf, ncols)
    # coordenadas y de las celdas
    Ymodis = np.linspace(Yf, Yo, nrows)
    # matrices 2D con las coordenadas X e Y de cada celda
    XXmodis, YYmodis = np.meshgrid(Xmodis, Ymodis)

    if coordsClip is not None:
        # definir sistemas de referencia de coordenadas
        ProjOut = Proj(init=coordsClip)
        # https://spatialreference.org/ref/sr-org/modis-sinusoidal/
        SINUSOIDAL = Proj(projparams='PROJCS["Sinusoidal",GEOGCS["GCS_Undefined",DATUM["D_Undefined",SPHEROID["User_Defined_Spheroid",6371007.181,0.0]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.017453292519943295]],PROJECTION["Sinusoidal"],PARAMETER["False_Easting",0.0],PARAMETER["False_Northing",0.0],PARAMETER["Central_Meridian",0.0],UNIT["Meter",1.0]]')

        # transformar coordenadas
        Xmodis, Ymodis = transform(SINUSOIDAL, ProjOut, XXmodis.flatten(), YYmodis.flatten())
        XXmodis, YYmodis = Xmodis.reshape((nrows, ncols)), Ymodis.reshape((nrows, ncols))

    # CREAR MÁSCARAS
    # --------------
    if clip is not None:
        # cargar ascii
        clipdf = ascii2df(clip)
        # extensión del ascii
        Xbo, Xbf = clipdf.columns.min(), clipdf.columns.max()
        Ybo, Ybf = clipdf.index.min(), clipdf.index.max()

        # mapa auxiliar del tamaño de los hdf
        aux = np.ones((nrows, ncols))
        # convertir en NaN celdas fuera del rectángulo de extensión de la cuenca
        maskExtent = (XXmodis >= Xbo) & (XXmodis <= Xbf) & (YYmodis >= Ybo) & (YYmodis <= Ybf)
        aux[~maskExtent] = np.nan
        # filas (maskR) y columnas (masC) en la extensión de la cuenca
        maskRows = ~np.all(np.isnan(aux), axis=1)
        maskCols = ~np.all(np.isnan(aux), axis=0)

        # recortar aux
        aux = aux[maskRows, :][:, maskCols]
        # extraer coordenadas en el rectángulo de extensión de la cuenca
        XXb, YYb = XXmodis[maskRows, :][:, maskCols], YYmodis[maskRows, :][:, maskCols]

        # convertir en NaN celdas fuera de la cuenca
        for c, (y, x) in enumerate(zip(YYb.flatten(), XXb.flatten())):
            ibasin, jbasin = np.argmin(abs(y - clipdf.index)), np.argmin(abs(x - clipdf.columns))
            if np.isnan(clipdf.iloc[ibasin, jbasin]):
                imodis, jmodis = int(c / XXb.shape[1]), c % XXb.shape[1]
                aux[imodis, jmodis] = np.nan
                maskClip = np.isnan(aux)
        if verbose == True:
            print('nº filas: {0:>3}\tnº columnas: {1:>3}'.format(aux.shape[0], aux.shape[1]))

    # IMPORTAR DATOS
    # --------------
    for i, file in enumerate(files):
        if verbose is True:
            print('Archivo {0:>3} de {1:>3}'.format(i + 1, len(files)), end='\r')
        # cargar archivo 'hdf'
        f = Dataset(path + file, format='hdf4')
        # extraer datos de la variable
        if clip is not None:  
            tmp = f[var][maskRows, :][:, maskCols]
            tmp[tmp.mask] = np.nan
            tmp[maskClip] = np.nan
        else:
            tmp = f[var][:]
            tmp[tmp.mask] = np.nan
        # guardar datos en un array
        if i == 0:
            data = tmp.data
        else:
            data = np.dstack((data, tmp.data))
        del tmp
        f.close()
    if factor is not None:
        data *= factor
    
    # GUARDAR RESULTADOS
    # ------------------
    MODIS_extract.data = data
    MODIS_extract.dates = dates
    if clip is not None:
        MODIS_extract.Xcoords = XXb
        MODIS_extract.Ycoords = YYb
    else:
        MODIS_extract.Xcoords = XXmodis
        MODIS_extract.Ycoords = YYmodis


# In[ ]:


def plotMODISseries(data, var, timevar, r, ymin=None, ylabel=None, lw=.25, alpha=.1):
    """Figura con un gráfico de línea para Terra y otro para Aqua con la serie temporal de data.
    
    Entradas:
    ---------
    data:    dict. Contiene los datos de 'Terra' y 'Aqua' en la variable 'var' para las fechas en la variable 'timevar'
    var:     string. Nombre de la variable de interés dentro de 'data'
    timevar: string. Nombre de la variable deentro de 'data' que contiene las fechas
    ymin:    boolean. Si se quiere calcular el mínimo del eje Y (True), o se fija en 0 (False)
    r:       string. Redondeo
    ylabel:  string. Etiqueta del eje y
    lw:      float. Grosor de línea
    alpha:   float. Transparencia
    """
    
    # mostrar la serie 8-diaria para cada celda y la media de la cuenca
    fig, axes = plt.subplots(nrows=2, figsize=(15, 7), sharex=True)

    xlim = [min(min(data['Terra'][timevar]), min(data['Aqua'][timevar])),
            max(max(data['Terra'][timevar]), max(data['Aqua'][timevar]))]
    if ymin == True:
        ymin = np.floor(min([np.nanmin(data[sat][var]) for sat in data.keys()]) / r) * r
    else:
        ymin = 0
    ymax = np.ceil(max([np.nanmax(data[sat][var]) for sat in data.keys()]) / r) * r
    colors = [['yellowgreen', 'darkolivegreen'], ['lightsteelblue', 'steelblue']]

    for c, (ax, sat) in enumerate(zip(axes, ['Terra', 'Aqua'])):
        timex, datax = data[sat][timevar], data[sat][var]
        for i in range(datax.shape[1]):
            for j in range(datax.shape[2]):
                if np.isnan(datax[:,i,j]).sum() == datax.shape[0]: # celda vacía
                    continue
                else:
                    # serie de una celda
                    ax.plot(timex, datax[:, i,j], lw=lw, c=colors[c][0], alpha=alpha)
        # serie media areal
        ax.plot(timex, np.nanmean(datax, axis=(1, 2)), c=colors[c][1], lw=4*lw)
        # configuración
        ax.tick_params(labelsize=11)
        ax.set(xlim=xlim, ylim=(ymin, ymax))
        ax.set_ylabel(ylabel, fontsize=13)
        ax.set_title(sat, fontsize=13, fontweight='bold');


# In[ ]:




