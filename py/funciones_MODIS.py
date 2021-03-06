#!/usr/bin/env python
# coding: utf-8

# AUTOR:    Jesús Casado
# REVISIÓN: 22/01/2020
# 
# INTRODUCCIÓN
# ------------
# Código con funciones para la descarga y tratamiento de datos MODIS.
# 
# Los datos MODIS se descargan del [servidor USGS](https://e4ftl01.cr.usgs.gov/). En dicho enlace se pueden ver las misiones, productos y fechas disponibles. Para poder descargar datos del servidor, es necesario estar registrado en https://urs.earthdata.nasa.gov/.
# 
# En el tratamiento de datos se incluye una función para extraer los datos de un producto para la variable, fechas y cuenca de interés.
# 
# COSAS QUE ARREGLAR
# ------------------
# 
# ***
# INDICE
# ------
# Descarga de datos MODIS
# 
# Tratamiento de datos MODIS



import os
import requests
import urllib
from http.cookiejar import CookieJar
from bs4 import BeautifulSoup


import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
#plt.style.use('seaborn-whitegrid')
#plt.style.use('dark_background')
#get_ipython().run_line_magic('matplotlib', 'inline')

from netCDF4 import Dataset
# import h5py
from datetime import datetime, timedelta
from calendar import monthrange

from pyproj import Transformer, CRS
#from pyproj import Proj, transform#, CRS
os.environ['PROJ_LIB'] = r'C:\Anaconda3\pkgs\proj4-4.9.3-vc14_5\Library\share'
# sistema de coordenadas de MODIS
sinusoidal = CRS.from_proj4('+proj=sinu +lon_0=0 +x_0=0 +y_0=0 +a=6371007.181 +b=6371007.181 +units=m +no_defs ')

from matplotlib.colors import ListedColormap, BoundaryNorm
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
import matplotlib.animation as animation
from IPython.display import HTML

url = 'https://raw.githubusercontent.com/casadoj/Calibrar/master/py/read_write.py'
r = requests.get(url).text
exec(r)

#url = 'https://github.com/casadoj/Calibrar/blob/Snow-DDM/py/funciones_raster.py'
#r = requests.get(url).text
#exec(r)
pathOrig = os.getcwd()
os.chdir(os.path.join(pathOrig, '../../Calibrar/py/'))
from funciones_raster import *
os.chdir(pathOrig)

# DESCARGA DE DATOS MODIS
# -----------------------


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


                
                
                
# TRATAMIENTO DE DATOS MODIS
# --------------------------


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




def hdfAttrs(file):
    """Extrae los atributos de los archivos 'hdf' de MODIS
    
    Parámetros:
    -----------
    file:      string. Ruta, nombre y extensión del archivo
    
    Salidas:
    --------
    ncols, nrows, Xtopleft, Ytopleft, Xbottomright, Ybottomright"""
    
    # cargar primer archivo 'hdf'
    f = Dataset(file, format='hdf4')
    # extraer atributos
    structure = getattr(f, 'StructMetadata.0').replace('\t', '').split('\n')
    # nº de columnas
    ncols = int(structure[5].split('=')[1])
    # nº de filas
    nrows = int(structure[6].split('=')[1])
    # coordenadas esquina superior izquierda
    Xo, Yf = [float(x) for x in structure[7].split('=')[1][1:-1].split(',')] 
    # coordenadas esquina inferior derecha
    Xf, Yo = [float(x) for x in structure[8].split('=')[1][1:-1].split(',')]
    
    return ncols, nrows, Xo, Yf, Xf, Yo

        


def MODIS_extract(path, product, var, tiles, factor=None, dateslim=None,
                  clip=None, coordsClip='epsg:25830', verbose=True):
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
#         return 
    else:
        dates = np.sort(np.unique(np.array([date for tile in tiles for date in dates[tile]])))
        if verbose:
            print('Seleccionar archivos')
            print('nº de archivos (fechas): {0:>3}'.format(len(dates)), end='\n\n')

    # ATRIBUTOS MODIS
    # ---------------
    if verbose: print('Generar atributos globales')
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
    # matrices 2D con las coordenadas X e Y de cada celda
    XXmodis, YYmodis = np.meshgrid(Xmodis, Ymodis)

    if coordsClip is not None:
        ## definir sistemas de referencia de coordenadas
        # ProjOut = Proj(init=coordsClip)
        # https://spatialreference.org/ref/sr-org/modis-sinusoidal/
        sinusoidal = CRS.from_proj4('+proj=sinu +lon_0=0 +x_0=0 +y_0=0 +a=6371007.181 +b=6371007.181 +units=m +no_defs ')
        #SINUSOIDAL = Proj(projparams='PROJCS["Sinusoidal",GEOGCS["GCS_Undefined",DATUM["D_Undefined",SPHEROID["User_Defined_Spheroid",6371007.181,0.0]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.017453292519943295]],PROJECTION["Sinusoidal"],PARAMETER["False_Easting",0.0],PARAMETER["False_Northing",0.0],PARAMETER["Central_Meridian",0.0],UNIT["Meter",1.0]]')
        project = Transformer.from_crs(sinusoidal, coordsClip)

        # transformar coordenadas
        Xmodis, Ymodis = project.transform(XXmodis.flatten(), YYmodis.flatten())
        XXmodis, YYmodis = Xmodis.reshape((nrows, ncols)), Ymodis.reshape((nrows, ncols))

    # CREAR MÁSCARAS
    # --------------
    if clip is not None:
        if verbose == True: print('Crear máscaras')
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
            print('dimensión:\t\t({0:>4}, {1:>4})'.format(aux.shape[0], aux.shape[1]))
            print('esquina inf. izqda.:\t({0:>10.2f}, {1:>10.2f})'.format(XXb[-1,0], YYb[-1,0]))
        print('esquina sup. dcha.:\t({0:>10.2f}, {1:>10.2f})'.format(XXb[0,-1], YYb[0,-1]), end='\n\n')

    # IMPORTAR DATOS
    # --------------
    if verbose: print('Importar datos')
        
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
        if clip is not None:
            dataD = dataD[maskRows, :][:, maskCols]
            dataD[maskClip] = np.nan
            
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
    MODIS_extract.data = data
    MODIS_extract.dates = dates
    if clip is not None:
        MODIS_extract.Xcoords = XXb
        MODIS_extract.Ycoords = YYb
    else:
        MODIS_extract.Xcoords = XXmodis
        MODIS_extract.Ycoords = YYmodis




def plotMODISseries(MODIS, **kwargs):
    """Figura con un gráfico de línea para Terra y otro para Aqua con la serie temporal de data.
    
    Entradas:
    ---------
    MODIS:   dict. Contiene los datos de las fuentes ('Terra' y 'Aqua') como objetos raster3D
    
    kwargs:     r:       int or float. Redondeo
                xlim
                ymin:    boolean. Si se quiere calcular el mínimo del eje Y (True), o se fija en 0 (False)
                ylabel:  string. Etiqueta del eje y
                lw:      float. Grosor de línea
                alpha:   float. Transparencia
                figsize: 
    """
    

    # extraer kwargs
    r = kwargs.get('r', 1)
    xlim = kwargs.get('xlim', [min([min(MODIS[sat].times) for sat in MODIS]),
                               max([max(MODIS[sat].times) for sat in MODIS])])
    ymin = kwargs.get('ymin', 0)
    ylabel = kwargs.get('ylabel', '')
    lw = kwargs.get('lw', .25)
    alpha = kwargs.get('alpha', .1)
    figsize = kwargs.get('figsize', (15, 7))

    # mostrar la serie 8-diaria para cada celda y la media de la cuenca
    nSats = len(MODIS.keys())
    fig, axes = plt.subplots(nrows=nSats, figsize=figsize, sharex=True)

    if ymin == True:
        ymin = np.floor(min([np.nanmin(MODIS[sat].data) for sat in MODIS]) / r) * r
    else:
        ymin = 0
    ymax = np.ceil(max([np.nanmax(MODIS[sat].data) for sat in MODIS]) / r) * r
    
    colors = [['yellowgreen', 'darkolivegreen'],
              ['lightsteelblue', 'steelblue'],
              ['gray', 'k']]

    for c, (ax, sat) in enumerate(zip(axes, MODIS)):
        timex, datax = MODIS[sat].times, MODIS[sat].data
        for i in range(datax.shape[1]):
            for j in range(datax.shape[2]):
                if np.all(np.isnan(datax[:,i,j])): # celda vacía
                    continue
                else:
                    try:
                        # serie de una celda
                        ax.plot(timex, datax[:,i,j], lw=lw, c=colors[c][0], alpha=alpha)
                    except:
                        return i, j
        # serie media areal
        ax.plot(timex, np.nanmean(datax, axis=(1, 2)), c=colors[c][1], lw=4*lw)
        # configuración
        ax.tick_params(labelsize=11)
        ax.set(xlim=xlim, ylim=(ymin, ymax))
        ax.set_ylabel(ylabel, fontsize=13)
        ax.set_title(sat, fontsize=13, fontweight='bold');

        
def animate3Darray(data, dates, minmax, cblabel='', cmap='summer_r', fps=2, dpi=100, pathfile=None):
    """Crea una animación a partir de un 'array' 3D.
    
    Parámetros:
    -----------
    data:      array (tiempo, y, x)
    dates:     list (tiempo). Fechas a las que corresponden cada uno de los mapas de 'data'
    minmax:    list. Mínimo y máximo de la escala de colores
    cblabel:   string. Etiqueta de la escala de colores
    cmap:      string. Mapa de color
    fps:       int. Imágenes por segundo
    dpi:       int. Resolución en puntos por pulgada
    pathfile:  string. Ruta, nombre y extensión donde guardar la animación. Por defecto es 'None y no se guarda
    """
    
    # definir configuración del gráfico en blanco
    fig, ax = plt.subplots(figsize=(5,5))
    im = ax.imshow(np.zeros(data.shape[1:]), animated=True,
                   cmap=cmap, vmin=minmax[0], vmax=minmax[1])
    plt.axis('off')
    cb = plt.colorbar(im, shrink=.7)
    cb.set_label(cblabel, fontsize=12)
    title = ax.text(.5, 1.05, '', fontsize=13, fontweight='bold',
                    transform=ax.transAxes, horizontalalignment='center')

    def updatefig(i, *args):
        """Función que define los zdatos a mostrar  el título en cada iteración"""
        title.set_text(dates[i].date())
        im.set_array(data[i,:,:])
        return im,

    # genera la animación iterando sobre 'updatefig' un número 'frames' de veces
    ani = animation.FuncAnimation(fig, updatefig, frames=data.shape[0], interval=1000/fps,
                                  blit=True)
    # guardar vídeo
    if pathfile is not None:
        ani.save(pathfile, fps=fps, extra_args=['-vcodec', 'libx264'], dpi=dpi)
    # plt.show()

    # ver vídeo en el 'notebook'
    return HTML(ani.to_html5_video())



def MODISfromASC(path, product, factor=None, fillValue=None):
    """Lee los mapas de MODIS en formato ascii (generados mediante pyScripter) y genera un array único para todos los datos
    
    Parámetros:
    -----------
    path:      string. Ruta donde se encuentran los mapas en formato ASCII
    product:   string. Producto MODIS a descargar
    factor:    float. Factor corrector de los datos: https://lpdaac.usgs.gov/products/
    fillVale:  list. Valor (o dos valores) correspondientes a NaN: https://lpdaac.usgs.gov/products/
    
    Salidas:
    --------
    En forma de métodos de la función:
        data:  array (t,n,m). Datos de la variable de interés
        dates: array (t). Fechas de cada uno de los mapas
        Y:     array (n). Coordenadas Y de las filas
        X:     array (m). Coordenadas X de las columnas
    """
    
    # archivos ascii
    ascFiles = [f for f in os.listdir(path) if ('asc' == f[-3:]) & (product.lower() in f)]
    
    dates = []
    for f, file in enumerate(ascFiles):

        print('Archivo {0:>3} de {1:>3}: {2}'.format(f + 1, len(ascFiles), file), end='\r')

        # fecha del mapa
        year = file.split('_')[1][1:5]
        doy = file.split('_')[1][5:8]
        dates.append(datetime.strptime(' '.join([year, doy]), '%Y %j').date())

        # importar ascii
        read_ascii(path + file)
        aux = read_ascii.data
        if f == 0:
            attrs = read_ascii.attributes

        # eliminar celdas con códigos correspondientes a Nan
        if fillValue is not None:
            if len(fillValue) == 1:
                aux[aux == fillValue] = np.nan
            elif len(fillValue) == 2:
                for fill in range(fillValue[0], fillValue[1] + 1):
                    aux[aux == fill] = np.nan
            else:
                print('¡ERROR! Longitud de "fillValue"')

        # multiplicar por el factor correspondiente
        if factor is not None:
            aux *= factor

        # convertir en NaN según la máscara
        aux[aux.mask] = np.nan

        # unir al 'array' con el resto de fechas
        if f == 0:
            data = aux.data
        else:
            data = np.dstack((data, aux.data))

        del aux
    dates = np.array(dates)
    print()

    # calcular media para # eliminar filas y columnas vacías
    avg = np.nanmean(data, axis=2)
    maskCols = np.all(np.isnan(avg), axis=0)
    maskRows = np.all(np.isnan(avg), axis=1)
    data = data[~maskRows,:][:,~maskCols]

    # coordenadas x
    x = np.arange(attrs[2], attrs[2] + attrs[0] * attrs[4] - 1, attrs[4])
    x = x[~maskCols]
    # coordenadas y
    y = np.arange(attrs[3], attrs[3] + attrs[1] * attrs[4] - 1, attrs[4])
    y = y[~maskRows]

    # reordenar datos: (fechas, Y, X)
    data = np.moveaxis(data, 2, 0)
    print('dimensiones (fechas, y, x): {0}'.format(data.shape))
    
    # guardar resultados
    MODISfromASC.data = data
    MODISfromASC.dates = dates
    MODISfromASC.Y = y
    MODISfromASC.X = x

    
    
    
def MODISnc(pathfile, MODISdict, var, units, sats=['Terra', 'Aqua']):
    """Genera un netCDF a partir de un diccionario con los datos MODIS correspondientes a una variable
    
    Parámetros:
    -----------
    pathfile:  string. Ruta, nombre y extensión del archivo netCDF a crear
    MODISdict: dict. Diccionario en el que se guardan todos los datos modis de una variable. Ej: MODISdict{'Terra':  {var, 'dates', 'Y', 'X'}, 'Aqua':  {var, 'dates', 'Y', 'X'}}
    var:       string. Nombre de la variable de estudio. P.ej.: 'ET' para evapotranspiración
    units:     string. Unidades en las que se mide la variable
    sats:      list of strings. Nombres de los satélites. Por defecto hay dos productos para los satélites 'Terra' y 'Aqua'
    
    Salidas:
    --------
    Archivo netCDF en 'pathfile'
    """
    
    # definir el netcdf
    ncMODIS = Dataset(pathfile, 'w', format='NETCDF4')

    # crear atributos
    ncMODIS.description = 'Serie temporal de mapas de ' + var + ' de la cuenca obtenidos a partir de MODIS'
    ncMODIS.history = 'Creado el ' + datetime.now().date().strftime('%Y-%m-%d')
    ncMODIS.source = 'https://e4ftl01.cr.usgs.gov/'
    ncMODIS.coordinateSystem = 'epsg:25830' # ETRS89 30N

    for sat in sats:
        # crear grupo
        group = ncMODIS.createGroup(sat)
        
        # crear las dimensiones
        time = group.createDimension('time', len(MODISdict[sat]['dates']))
        Y = group.createDimension('Y', len(MODISdict[sat]['Y']))
        X = group.createDimension('X', len(MODISdict[sat]['X']))

        # crear variables
        data = group.createVariable(var, 'f4', ('time', 'Y', 'X'))
        data.units = units
        times = group.createVariable('time', 'f8', ('time',))
        times.units = 'días desde el 0001-01-01'
        times.calendar = 'Gregoriano'
        Xs = group.createVariable('X', 'u4', ('X',))
        Xs.units = 'm'
        Ys = group.createVariable('Y', 'u4', ('Y',))
        Ys.units = 'm'

        # variable
        data[:,:,:] = MODISdict[sat][var][:,:,:]
        # variable 'time'
        deltas = [date - datetime(1, 1, 1).date() for date in MODISdict[sat]['dates']]
        times[:] = [delta.days for delta in deltas]
        # variable 'X'
        Xs[:] = MODISdict[sat]['X']
        # variable 'Y'
        Ys[:] = MODISdict[sat]['Y']

    ncMODIS.close()
    
    
    
    
# AGREGAR DATOS MODIS
# -------------------



def mediaMensual(modis):
    """Calcula la media mensual interanual para cada mes del año
    
    Parámetros:
    -----------
    modis:     raster3D (t,n,m)
    
    Salida:
    -------
    meanM:     raster3D (12,n,m). Media mensual de la variable
    """
    
    # medias mensuales
    meanM = np.zeros((12, *modis.data.shape[1:])) * np.nan
    for m, month in enumerate(range(1, 13)):
        ks = [k for k, time in enumerate(modis.times) if time.month == month]
        meanM[m,:,:] = np.nanmean(modis.data[ks,:,:], axis=0)
    
    # guardar como raster3D
    meanM = raster3D(meanM, modis.X, modis.Y, np.arange(1, 13), modis.units, modis.variable, modis.label, modis.crs)
        
    return meanM




def serieMensual(modis, agg='mean'):
    """Calcula la serie mensual
    
    Parámetros:
    -----------
    modis:     raster3D (t,n,m).
    agg:       string. Tipo de agregación mensual: 'mean', media diaria; 'sum' suma mensual (ET)
    
    Salida:
    -------
    serieM:    raster3D (t',n,m). Mapas de la serie mensual
    """
    
    # extraer información de 'modis'
    times = modis.times
    data = modis.data

    # paso temporal de la serie original
    At = np.round(np.mean([d.days for d in np.diff(times)]), 1)

    # serie de meses
    if At == 1:
        start = datetime(times[0].year, times[0].month, times[0].day).date()
        end = datetime(times[-1].year, times[-1].month, times[-1].day).date()
    else:
        start = datetime(times[0].year, times[0].month, 1).date()
        end = datetime(times[-1].year, times[-1].month, monthrange(times[-1].year, times[-1].month)[1]).date()
    days = pd.date_range(start, end)
    months = [m.date() for m in pd.date_range(start, end, freq='M')]

    # SERIE MENSUAL
    serieM = np.zeros((len(months), *data.shape[1:])) * np.nan
    for i in range(data.shape[1]):
        for j in range(data.shape[2]):
            print('celda {0:>5} de {1:>5}'.format(i * data.shape[2] + j + 1,
                                                  data.shape[1] * data.shape[2]), end='\r')
            if np.isnan(data[:,i,j]).sum() == data.shape[0]: # ningún dato en toda la serie
                continue
            else:
                if At > 1: # si la serie original no es diaria
                    # generar serie diaria
                    auxd = pd.Series(index=days)
                    for k, (st, et) in enumerate(zip(times, data[:,i,j])):
                        if np.isnan(et):
                            continue
                        else:
                            if st != times[-1]:
                                en = times[k+1]
                                auxd[st:en - timedelta(1)] = et / (en - st).days
                            else:
                                en = st + timedelta(At)
                                auxd[st:end - timedelta(1)] = et / (en - st).days
                else: # si la serie original es diaria
                    auxd = pd.Series(data=data[:,i,j], index=days)
                # generar serie mensual
                if agg == 'mean':
                    auxm = auxd.groupby([auxd.index.year, auxd.index.month]).agg(np.nanmean)
                elif agg == 'sum':
                    auxm = auxd.groupby([auxd.index.year, auxd.index.month]).agg(np.nansum)
                auxm.index = [datetime(idx[0], idx[1], monthrange(idx[0], idx[1])[1]).date() for idx in auxm.index]
                # asignar serie mensual a su celda en el array 3D
                serieM[:,i,j] = auxm.iloc[:serieM.shape[0]].copy()
                del auxd, auxm

    serieM = raster3D(serieM, modis.X, modis.Y, months, modis.units, modis.variable,
                      modis.label, modis.crs)

    return serieM




def serieAnual(modis, agg='mean', threshold=40):
    """Calcula la serie anual
    
    Parámetros:
    -----------
    modis:     raster3D (t,n,m)
    
    Salida:
    -------
    serieA:    raster3D (t',n,m). Mapas de la serie anual
    """
    
    # extraer información de 'modis'
    times = modis.times
    data = modis.data
    
    # años con datos
    years = np.unique(np.array([date.year for date in times]))
    
    # serie anual
    serieA = np.zeros((len(years), *data.shape[1:])) * np.nan
    for y, year in enumerate(years):
        maskT = [t for t, time in enumerate(times) if time.year == year]
        nT = len(maskT)
        if nT > threshold: # si no faltan más de 46 - 'threhsold' mapas en un año
            mean = np.nanmean(data[maskT,:,:], axis=0)
            if agg == 'sum':
                count = np.sum(~np.isnan(data[maskT,:,:]), axis=0)
                serieA[y,:,:] = mean * count
            elif agg == 'mean':
                serieA[y,:,:] = mean
        else: # si faltan más de 46 - 'threhsold' mapas en un año 
            serieA[y,:,:] = np.zeros((1, *data.shape[1:])) * np.nan
            
    # guardar como raster3D
    serieA = raster3D(serieA, modis.X, modis.Y, years, modis.units, modis.variable, modis.label,
                      modis.crs)
    
    return serieA



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
    modis = raster3D(data, Xmodis, Ymodis, dates, crs=sinusoidal)
    
    return modis


# ### video

# In[1]:


def video(raster, cuenca, cmap, norm, DEM=None, fps=2, dpi=600, export=False, **kwargs):
    """Crea un vídeo con la predicción de HARMONIE.

    Entradas:
    ---------
    raster:     class raster3D
    cuenca:     geodataframe. Polígonos de las cuencas
    cmap:       
    norm:
    DEM:        class raster2D. Mapa de elevación
    fps:        int. 'frames per seconds'. Número de pasos temporales a mostrar por segundo
    dpi:        int. 'dots per inch'. Resolución del mapa
    export:     boolean. Si se quiere exportar la figura como mp4

    kwargs:
                figsize:    list (,). Tamaño de la figura. Por defecto (16, 7)
                color:      string. Color con el que definir los límites de las provincias. Por defecto es blanco
                dateformat: string. Formato de las fechas en la figura. Por defecto '%d-%m-%Y %H:%M'
                extent:     tuple [O, E, S, N]. Límites espaciales de la figura. Por defecto 'None'
                rutaExport: string. Carpeta donde guardar el pdf. Por defecto '../output/'

    Salidas:
    --------
    Mapas diarios
    Si 'export == True', se exporta un pdf con el nombre 'label_pasada.mp4'. Por ejemplo, 'APCP_2020113000.mp4'
    """

    # extraer datos del raster
    data, X, Y, times = raster.data, raster.X, raster.Y, raster.times

    # extraer kwargs
    figsize = kwargs.get('figsize', (16, 3.75))#(17, 3.5)
    color = kwargs.get('color', 'k')
    dateformat = kwargs.get('dateformat', '%d-%m-%Y')
    extent = kwargs.get('extent', raster.extent())
    rutaExport = kwargs.get('rutaExport', '../output/')

    # definir configuración del gráfico en blanco
    fig, ax = plt.subplots(figsize=figsize)

    # título del gráfico
    title = ax.text(.5, 1.05, '', horizontalalignment='center', fontsize=13,
                    transform=ax.transAxes)

    # capas vectoriales
    cuenca.boundary.plot(color=color, lw=1., ax=ax, zorder=3)

    # dem de fondo
    ax.imshow(DEM.data, extent=DEM.extent, cmap='pink', zorder=1)

    # mapa
    im = ax.imshow(np.zeros(data.shape[1:]), cmap=cmap, norm=norm, extent=raster.extent(),
                   zorder=2)

    ax.set_aspect('equal')
    ax.set(xlim=(extent[0], extent[1]), ylim=(extent[2], extent[3]))
    ax.axis('off');

    # barra de la leyenda
    snow_patch = mpatches.Patch(color=cmap.colors[1], label='snow')
    fig.legend(handles=[snow_patch], loc=8, fontsize=13)

    def updatefig(i, *args):
        """Función que define los zdatos a mostrar  el título en cada iteración"""
        title.set_text(times[i].strftime(dateformat))
        im.set_array(data[i,:,:])
        return im,

    # genera la animación iterando sobre 'updatefig' un número 'frames' de veces
    ani = animation.FuncAnimation(fig, updatefig, frames=data.shape[0], interval=1000/fps,
                                  blit=True)
    # guardar vídeo
    if export:
        mp4File = rutaExport + '{0}_{1}.mp4'.format(raster.label, times[0].strftime('%Y%m%d%H'))
        print('Exportando archivo {0}'.format(mp4File))
        ani.save(mp4File, fps=fps, extra_args=['-vcodec', 'libx264'], dpi=dpi)

    # ver vídeo en el 'notebook'
    return HTML(ani.to_html5_video())


# ### video2

# In[116]:


def video2(raster1, raster2, cuenca, cmap, norm, DEM=None, fps=2, dpi=600, export=None, **kwargs):
    """Crea un vídeo con la predicción de HARMONIE.

    Entradas:
    ---------
    raster1:    class raster3D
    raster2:    class raster3D
    cuenca:     geodataframe. Polígonos de las cuencas
    cmap:
    norm:
    DEM:        class raster2D. Mapa de elevación
    fps:        int. 'frames per seconds'. Número de pasos temporales a mostrar por segundo
    dpi:        int. 'dots per inch'. Resolución del mapa
    export:     boolean. Si se quiere exportar la figura como pdf

    kwargs:
                figsize:    list (,). Tamaño de la figura. Por defecto (16, 7)
                color:      string. Color con el que definir los límites de las provincias. Por defecto es blanco
                dateformat: string. Formato de las fechas en la figura. Por defecto '%d-%m-%Y %H:%M'
                extent:     tuple [O, E, S, N]. Límites espaciales de la figura. Por defecto 'None'
                rutaExport: string. Carpeta donde guardar el pdf. Por defecto '../output/'

    Salidas:
    --------
    Mapas diarios
    Si 'export == True', se exporta un pdf con el nombre 'label_pasada.mp4'. Por ejemplo, 'APCP_2020113000.mp4'
    """

    # extraer datos del raster
    data1, X, Y, times = raster1.data, raster1.X, raster1.Y, raster1.times
    data2 = raster2.data

    # extraer kwargs
    figsize = kwargs.get('figsize', (16, 3.75))#(17, 3.5)
    color = kwargs.get('color', 'k')
    dateformat = kwargs.get('dateformat', '%d-%m-%Y')
    extent = kwargs.get('extent', raster1.extent())
    rutaExport = kwargs.get('rutaExport', '../output/')
    labels = kwargs.get('labels', ['', ''])

    # definir configuración del gráfico en blanco
    fig, ax = plt.subplots(ncols=2, figsize=figsize, sharex=True, sharey=True)

    # título del gráfico
    title = ax[0].text(1.05, 1.0, '', horizontalalignment='center', fontsize=13, transform=ax[0].transAxes)

    # capas vectoriales
    ax[0].text(.5, 1.05, labels[0], horizontalalignment='center', fontsize=14, transform=ax[0].transAxes)
    cuenca.boundary.plot(color=color, lw=1., ax=ax[0], zorder=3)
    # dem de fondo
    ax[0].imshow(DEM.data, extent=DEM.extent, cmap='pink', zorder=1)
    # mapa
    im1 = ax[0].imshow(np.zeros(data1.shape[1:]), cmap=cmap, norm=norm, extent=raster1.extent(),
                       zorder=2)
    ax[0].set_aspect('equal')
    ax[0].set(xlim=(extent[0], extent[1]), ylim=(extent[2], extent[3]))
    ax[0].axis('off');

    # capas vectoriales
    ax[1].text(.5, 1.05, labels[1], horizontalalignment='center', fontsize=14, transform=ax[1].transAxes)
    cuenca.boundary.plot(color=color, lw=1., ax=ax[1], zorder=3)
    # dem de fondo
    ax[1].imshow(DEM.data, extent=DEM.extent, cmap='pink', zorder=1)
    # mapa
    im2 = ax[1].imshow(np.zeros(data2.shape[1:]), cmap=cmap, norm=norm, extent=raster2.extent(),
                       zorder=2)
    ax[1].set_aspect('equal')
    ax[1].set(xlim=(extent[0], extent[1]), ylim=(extent[2], extent[3]))
    ax[1].axis('off');

    # barra de la leyenda
    snow_patch = mpatches.Patch(color=cmap.colors[1], label='snow')
    fig.legend(handles=[snow_patch], loc=8, fontsize=13)

    def updatefig(i, *args):
        """Función que define los zdatos a mostrar  el título en cada iteración"""
        title.set_text(times[i].strftime(dateformat))
        im1.set_array(data1[i,:,:])
        im2.set_array(data2[i,:,:])
        return im1, im2

    # genera la animación iterando sobre 'updatefig' un número 'frames' de veces
    ani = animation.FuncAnimation(fig, updatefig, frames=data1.shape[0], interval=1000/fps,
                                  blit=True)
    # guardar vídeo
    if export is not None:
        if export.endswith('mp4'):
            print('Exportando archivo {0}'.format(export))
            ani.save(export, fps=fps, extra_args=['-vcodec', 'libx264'], dpi=dpi)
        else:
            print('Formato de archivo incorrecto; ha de ser mp4.')

    # ver vídeo en el 'notebook'
    return HTML(ani.to_html5_video())


def MODIS2netCDF(file, raster3D, description=None):
    """Exportar datos MODIS como netCDF.
    
    Entradas:
    ---------
    file:        string. Archivo (incluye ruta y extensión) donde guardar los datos
    raster3D:    raster3D. Datos de MODIS
    description: string. Descripción de los datos contenidos en 'raster3D' que se incluirá dentro del netCDF.
    
    Salida:
    -------
    Archivo netCDF con el nombre indicado
    """
    
    # definir el netcdf
    nc = Dataset(file, 'w', format='NETCDF4')

    # crear atributos
    nc.description = description
    nc.history = 'Creado el ' + datetime.now().date().strftime('%Y-%m-%d')
    nc.source = 'https://e4ftl01.cr.usgs.gov/'
    nc.coordinateSystem = 'epsg:{0}'.format(raster3D.crs.to_epsg())

    # crear las dimensiones
    time = nc.createDimension('time', len(raster3D.times))
    Y = nc.createDimension('Y', len(raster3D.Y))
    X = nc.createDimension('X', len(raster3D.X))

    # crear variables
    Var = nc.createVariable(raster3D.variable, 'f4', ('time', 'Y', 'X'))
    Var.units = raster3D.units
    times = nc.createVariable('time', 'f8', ('time',))
    times.units = 'días desde el 0001-01-01'
    times.calendar = 'Gregoriano'
    Xs = nc.createVariable('X', 'u4', ('X',))
    Xs.units = 'm'
    Ys = nc.createVariable('Y', 'u4', ('Y',))
    Ys.units = 'm'

    # variable
    Var[:,:,:] = raster3D.data[:,:,:]
    # variable 'time'
    deltas = [date - datetime(1, 1, 1).date() for date in raster3D.times]
    times[:] = [delta.days for delta in deltas]
    # variable 'X'
    Xs[:] = raster3D.X # + cellsize / 2
    # variable 'Y'
    Ys[:] = raster3D.Y # + cellsize / 2

    nc.close()
    
    
def netCDF2MODIS(file, label=None):
    """Leer datos de MODIS guardados en formato netCDF y crear un objeto raster3D con ellos
    
    Entradas:
    ---------
    file:     string. Archivo netCDF (incluida ruta y extensión) con los datos
    label:    string. Etiqueta a asignar a la variable
    """
    
    # abrir conexión con el archivo netCDF
    nc = Dataset(file, 'r', format='NETCDF4')
    
    # extraer datos
    for variable in nc.variables:
        if variable not in ['time', 'X', 'Y']:
            break
    data = nc[variable][::]
    units = nc[variable].units
    # fechas
    times = np.array([datetime(1, 1, 1).date() + timedelta(time) for time in nc['time'][:].data])
    # coordenadas
    X = nc['X'][:].data
    Y = nc['Y'][:].data
    crs = CRS.from_epsg(nc.coordinateSystem.split(':')[1])

    # guardar como objeto raster3D
    MODIS = raster3D(data, X, Y, times, variable=variable, label=label, units=units,
                       crs=crs)
    
    # cerrar archivo netCDF
    nc.close()
    
    return MODIS


def missingMaps(Terra, Aqua, verbose=True):
    """Encuentra mapas que falten en la serie temporal de cada uno de los satélites. En caso de encontrarlos, los intenta rellenar con los datos del otro satélite. Si el otro satélite tampoco dipusiera de datos para esa fecha, se crea un mapa vacío en esa fecha.
    
    Entradas:
    ---------
    Terra:   raster3D. Datos de Terra
    Aqua:    raster3D. Datos de Aqua
    verbose: boolean. Mostrar el proceso en pantalla
    
    Salidas:
    --------
    Terra_:  raster3D. Datos de Terra completados
    Aqua_:   raster3D. Datos de Aqua completados
    """
    
    Terra_ = copy.deepcopy(Terra)
    Aqua_ = copy.deepcopy(Aqua) 
    
    # datos modicados y originales
    for label, mod, ori in zip(['Terra', 'Aqua'], [Terra_, Aqua_], [Aqua, Terra]):
        if verbose:
            print(label.upper())
            print('-' * len(label))
        # identificar mapas que falten
        mask = np.diff(mod.times) > timedelta(days=8)
        mask = np.append(mask, False)
        if verbose:
            print('t', 'time', '\tDisp', sep='\t')
        missing = []
        for t in np.where(mask == True)[0]:
            time = mod.times[t] + timedelta(days=8)
            missing.append(time)
            if verbose:
                print(t, time, time in ori.times, sep='\t')

        # rellenar mapas que falten
        for time in missing:
            # posición en el array
            t = np.where(mod.times >= time)[0][0]

            # introducir el mapa en 'data'
            if time in ori.times:
                mod.data = np.concatenate((mod.data[:t,:,:],
                                           ori.data[t:t+1,:,:],
                                           mod.data[t:,:,:]))
            else:
                mod.data = np.concatenate((mod.data[:t,:,:],
                                           np.zeros((1, *mod.data.shape[1:])) * np.nan,
                                           mod.data[t:,:,:]))

            # introducir la fecha en 'times'
            mod.times = np.concatenate((mod.times[:t],
                                        np.array([time]),
                                        mod.times[t:]))
        print()
            
    return Terra_, Aqua_


def combinarMODIS(Aqua, Terra, verbose=True):
    """Combina los datos de Aqua y Terra mediante la media.
    
    Entradas:
    ---------
    Aqua:    raster3D
    Terra:   raster3D
    verbose: boolean. Si mostrar el proceso por pantalla
    
    Salidas:
    --------
    union:   raster3D
    """
    

    # Extraer fechas de Aqua y Terra
    timesA = Aqua.times
    timesT = Terra.times

    # escoger la serie de fechas más larga
    if len(timesA) >= len(timesT):
        times = timesA
    else:
        times = timesT

    # array con la media de los dos satélites
    data = np.zeros((len(times), *Aqua.data.shape[1:])) * np.nan
    for t, time in enumerate(times):
        if verbose:
            print('{0}:\t{1:<4} de {2:<4}'.format(time, t + 1, data.shape[0]), end='\r')
        if (time in timesA) & (time in timesT):
            tA = np.where(timesA == time)[0][0]
            tT = np.where(timesT == time)[0][0]
            data[t,:,:] = np.nanmean(np.stack((Aqua.data[tA,:,:], Terra.data[tT,:,:]),
                                              axis=0), axis=0)
        elif time not in timesA:
            tT = np.where(timesT == time)[0][0]
            data[t,:,:] = Terra.data[tT,:,:]
        elif time not in timesT:
            tA = np.where(timesA == time)[0][0]
            data[t,:,:] = Aqua.data[tA,:,:]

    # convertir en raster3D
    union = raster3D(data, Aqua.X, Aqua.Y, times, Aqua.units, Aqua.variable, Aqua.label,
                     Aqua.crs)

    return union