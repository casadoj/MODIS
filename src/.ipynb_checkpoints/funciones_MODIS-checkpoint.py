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
plt.style.use('seaborn-whitegrid')
plt.style.use('dark_background')
get_ipython().run_line_magic('matplotlib', 'inline')

from netCDF4 import Dataset
# import h5py
from datetime import datetime, timedelta
from calendar import monthrange

from pyproj import Proj, transform#, CRS
os.environ['PROJ_LIB'] = r'C:\Anaconda3\pkgs\proj4-4.9.3-vc14_5\Library\share'

import matplotlib.animation as animation
from IPython.display import HTML

url = 'https://raw.githubusercontent.com/casadoj/Calibrar/master/read_write.py'
r = requests.get(url).text
exec(r)




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
    factor:     float. Factor con el que multiplicar los datos para obtener su valore real (comprobar en la página de MODIS para el producto y variable de interés)
    tiles:      list. Hojas del producto MODIS a tratar
    dateslim:   list. Fechas de inicio y fin del periodo de estudio en formato YYYY-MM-DD. Si es 'None', se extraen los datos para todas las fechas disponibles
    clip:       string. Ruta y nombre del archivo ASCII que se utilizará como máscara para recortar los datos. Si es 'None', se extraen todos los datos
    coordsClip: string. Código EPSG o Proj del sistema de coordenadas al que se quieren transformar los datos. Si en 'None', se mantiene el sistema de coordenadas sinusoidal de MODIS
    verbose:    boolean. Si se quiere mostrar en pantalla el desarrollo de la función
    
    Salidas:
    --------
    Como métodos:
        data:    array (Y, X) o (dates, Y, X). Mapas de la variable de interés. 3D si hay más de un archivo (más de una fecha)
        Xcoords: array (2D). Coordenadas X de cada celda de los mapas de 'data'
        Ycoords: array (2D). Coordenadas Y de cada celda de los mapas de 'data'
        dates:   list. Fechas a las que corresponde cada uno de los maapas de 'data'
    """    
    

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
        if verbose == True:
            print('Seleccionar archivos')
            print('nº de archivos (fechas): {0:>3}'.format(len(dates)), end='\n\n')

    # ATRIBUTOS MODIS
    # ---------------
    if verbose == True: print('Generar atributos globales')
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
    if verbose ==True: print('Importar datos')
        
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




def plotMODISseries(data, var, timevar, r, src=['Terra', 'Aqua'], ymin=None, ylabel=None, lw=.25, alpha=.1):
    """Figura con un gráfico de línea para Terra y otro para Aqua con la serie temporal de data.
    
    Entradas:
    ---------
    data:    dict. Contiene los datos de las fuentes ('Terra' y 'Aqua') en la variable 'var' para las fechas en la variable 'timevar'
    var:     string. Nombre de la variable de interés dentro de 'data'
    timevar: string. Nombre de la variable dentro de 'data' que contiene las fechas
    ymin:    boolean. Si se quiere calcular el mínimo del eje Y (True), o se fija en 0 (False)
    r:       string. Redondeo
    src:     list of strings. Fuentes de los datos; son las 'keys' del diccionario data. Por defecto son 'Terra' y 'Aqua'
    ylabel:  string. Etiqueta del eje y
    lw:      float. Grosor de línea
    alpha:   float. Transparencia
    """
    
    # mostrar la serie 8-diaria para cada celda y la media de la cuenca
    fig, axes = plt.subplots(nrows=2, figsize=(15, 7), sharex=True)

    xlim = [min(min(data[src[0]][timevar]), min(data[src[1]][timevar])),
            max(max(data[src[0]][timevar]), max(data[src[1]][timevar]))]
    if ymin == True:
        ymin = np.floor(min([np.nanmin(data[sat][var]) for sat in data.keys()]) / r) * r
    else:
        ymin = 0
    ymax = np.ceil(max([np.nanmax(data[sat][var]) for sat in data.keys()]) / r) * r
    colors = [['yellowgreen', 'darkolivegreen'], ['lightsteelblue', 'steelblue']]

    for c, (ax, sat) in enumerate(zip(axes, [src[0], src[1]])):
        timex, datax = data[sat][timevar], data[sat][var]
        for i in range(datax.shape[1]):
            for j in range(datax.shape[2]):
                if np.all(np.isnan(datax[:,i,j])): # celda vacía
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

        
def animate3Darray(data, dates, minmax, cblabel='', fps=2, dpi=100, pathfile=None):
    """Crea una animación a partir de un 'array' 3D.
    
    Parámetros:
    -----------
    data:      array (tiempo, y, x)
    dates:     list (tiempo). Fechas a las que corresponden cada uno de los mapas de 'data'
    minmax:    list. Mínimo y máximo de la escala de colores
    cblabel:   string. Etiqueta de la escala de colores
    fps:       int. Imágenes por segundo
    dpi:       int. Resolución en puntos por pulgada
    pathfile:  string. Ruta, nombre y extensión donde guardar la animación. Por defecto es 'None y no se guarda
    """
    
    # definir configuración del gráfico en blanco
    fig, ax = plt.subplots(figsize=(5,5))
    im = ax.imshow(np.zeros(data.shape[1:]), animated=True,
                   cmap='summer_r', vmin=minmax[0], vmax=minmax[1])
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

    
    
    
def MODISnc(pathfile, MODISdict, var, units):
    """Genera un netCDF a partir de un diccionario con los datos MODIS correspondientes a una variable
    
    Parámetros:
    -----------
    pathfile:  string. Ruta, nombre y extensión del archivo netCDF a crear
    MODISdict: dict. Diccionario en el que se guardan todos los datos modis de una variable. Ej: MODISdict{'Terra':  {var, 'dates', 'Y', 'X'}, 'Aqua':  {var, 'dates', 'Y', 'X'}}
    var:       string. Nombre de la variable de estudio. P.ej.: 'ET' para evapotranspiración
    units:     string. Unidades en las que se mide la variable
    
    Salidas:
    --------
    Archivo netCDF en 'pathfile'
    """
    
    # definir el netcdf
    ncMODIS = Dataset(pathfile, 'w', format='NETCDF4')
    
    # crear grupos
    terra = ncMODIS.createGroup('Terra')
    aqua = ncMODIS.createGroup('Aqua')

    # crear atributos
    ncMODIS.description = 'Serie temporal de mapas de ' + var + ' de la cuenca obtenidos a partir de MODIS'
    ncMODIS.history = 'Creado el ' + datetime.now().date().strftime('%Y-%m-%d')
    ncMODIS.source = 'https://e4ftl01.cr.usgs.gov/'
    ncMODIS.coordinateSystem = 'epsg:25830' # ETRS89 30N

    for group, sat in zip([terra, aqua], ['Terra', 'Aqua']):

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



def mediaMensual(dates, Data):
    """Calcula la media mensual interanual para cada mes del año
    
    Parámetros:
    -----------
    dates:     array (t). Fechas de cada uno de los mapas
    Data:      array (t,n,m). Datos a agregar
    
    Salida:
    -------
    meanM:     array(12,n,m). Media mensual de la variable
    """
    
    # medias mensuales
    meanM = np.zeros((12, Data.shape[1], Data.shape[2])) * np.nan
    for m, month in enumerate(range(1, 13)):
        ks = [k for k, date in enumerate(dates) if date.month == month]
        meanM[m,:,:] = np.nanmean(Data[ks,:,:], axis=0)
        
    return meanM




def serieMensual(dates, Data):
    """Calcula la serie mensual
    
    Parámetros:
    -----------
    dates:     array (t). Fechas de cada uno de los mapas
    Data:      array (t,n,m). Datos a agregar
    
    Salida:
    -------
    serieM:    array (t',n,m). Mapas de la serie mensual
    months:    array (t'). Fechas de los meses de la serie
    """
    
    start = datetime(dates[0].year, dates[0].month, 1).date()
    end = dates[-1] + timedelta(8)
    end = datetime(end.year, end.month, monthrange(end.year, end.month)[1]).date()
    days = pd.date_range(start, end)
    months = pd.date_range(start, end, freq='M')
    len(days), len(months)

    # serie mensuales
    serieM = np.zeros((len(months), Data.shape[1], Data.shape[2])) * np.nan
    for i in range(Data.shape[1]):
        for j in range(Data.shape[2]):
            print('celda {0:>5} de {1:>5}'.format(i * Data.shape[2] + j + 1,
                                                  Data.shape[1] * Data.shape[2]), end='\r')
            if np.isnan(Data[:,i,j]).sum() == Data.shape[0]: # ningún dato en toda la serie
                continue
            else:
                # generar serie diaria
                auxd = pd.Series(index=days)
                for k, (st, et) in enumerate(zip(dates, Data[:,i,j])):
                    if np.isnan(et):
                        continue
                    else:
                        if st != dates[-1]:
                            en = dates[k+1]
                        else:
                            en = st + timedelta(8)
                        auxd[st:en - timedelta(1)] = et / (en - st).days
                # generar serie mensual
                auxm = auxd.groupby([auxd.index.year, auxd.index.month]).agg(np.nanmean)
                auxm.index = [datetime(idx[0], idx[1], monthrange(idx[0], idx[1])[1]).date() for idx in auxm.index]
                # asignar serie mensual a su celda en el array 3D
                serieM[:,i,j] = auxm.iloc[:serieM.shape[0]].copy()
                del auxd, auxm
    
    return serieM, months




def serieAnual(dates, Data):
    """Calcula la serie anual
    
    Parámetros:
    -----------
    dates:     array (t). Fechas de cada uno de los mapas
    Data:      array (t,n,m). Datos a agregar
    
    Salida:
    -------
    serieA:    array (t',n,m). Mapas de la serie anual
    years:    array (t'). Fechas de los años de la serie"""
    
    # años con datos suficientes
    years = np.unique(np.array([date.year for date in dates]))
    ksyear = {}
    for year in years:
        ks = [k for k, date in enumerate(dates) if date.year == year]
        if len(ks) < 40: # si faltan más de 5 mapas en un año 
            years = years[years != year]
            continue
        else:
            ksyear[year] = ks

    # medias anuales        
    serieA = np.zeros((len(years), Data.shape[1], Data.shape[2])) * np.nan
    for y, year in enumerate(years):
        serieA[y,:,:] = np.nanmean(Data[ksyear[year],:,:], axis=0) * 365 / 8
        
    return serieA, years
