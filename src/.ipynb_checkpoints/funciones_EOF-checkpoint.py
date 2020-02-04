#!/usr/bin/env python
# coding: utf-8

# Autor:    Jesús Casado
# Revisión: 22/01/2020
# 
# INTRODUCCIÓN
# ------------
# Partiendo del paquete [`eofs`](https://ajdawson.github.io/eofs/latest/#), se crean dos funciones para hacer la descomposición en EOFs (*empirical orthogonal functions*) y PCs (*principal components*) de un array 3D en el que la primera dimensión es el tiempo.
# 
# Ejemplos del uso del paquete `eofs`:
# * [North Atlantic Oscillation](https://ajdawson.github.io/eofs/latest/examples/nao_standard.html)
# * [El Niño](https://ajdawson.github.io/eofs/latest/examples/elnino_standard.html)
# 
# Pasos habituales:
# 1. Importar la clase 'solver'
# ```Python
# from eofs.standard import Eof`
# ```
# 2. Crear un 'solver'
# ```Python
# solver = Eof(data, weights=weights_array, center=True, ddof=1)
# ```
# 3. Extraer resultados
# ```Python
# pcs = solver.pcs(npcs=5, pcscaling=1)
# eofs = solver.eofs()
# reconstructed_data = solver.reconstructedField(4)
# pseudo_pcs = solver.projectField(other_field)
# ```
# 4. 'Solvers' multivariable
# ```Python
# from eofs.multivariate.standard import MultivariateEof
# msolver = MultivariateEof([data1, data2, data3])
# eofs_data1, eofs_data2, eofs_data3 = msolver.eofs()
# pcs = msolver.pcs()
# ```
# 
# COSAS QUE ARREGLAR
# ------------------
# 
# ***
# FUNCIONES
# ---------
# plotEOF
# eofMODIS



import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
# plt.style.use('seaborn-whitegrid')
#plt.style.use('dark_background')
#get_ipython().run_line_magic('matplotlib', 'inline')
from matplotlib.gridspec import GridSpec

from netCDF4 import Dataset
# import h5py
from datetime import datetime, timedelta

import os

from pyproj import Proj, transform, CRS
os.environ['PROJ_LIB'] = r'C:\Anaconda3\pkgs\proj4-4.9.3-vc14_5\Library\share'

from eofs.standard import Eof




# #### plotEOF



def plotEOF(eofmap, pcs, eofvar='eofs', normPCs=False, fvar=None,
            rmap=.1, rserie=100):
    """Generar gráfico con los resultados del análisis EOF
    
    Entradas:
    ---------
    eofmap:  array(nmodes,m,p). 'nmodes' es el número de modos extraídos de la descomposición y 'm' y 'p' las dimensiones del mapa
    pcs:     array(n,nmodes). Donde n es el número de pasos temporales
    eofvar:  string. Nombre de la variable a mostrar en los mapas: 'eofs'; 'corr', correlación; 'var', varianza explicada
    normPCs: boolean. Si en los gráficos de los PCs los valores se muestran normalizados o no
    fvar:    array. Varianza total explicada por cada uno de los modos
    rmap:    float. Valor de redondeo de los mapas
    rserie:  float. Valor de redondeo de las series
    """
    
    n = eofmap.shape[0]
    fig = plt.figure(figsize=(3*3.5, n*3.5))
    gs = GridSpec(n, 3, figure=fig)
    
    if eofvar == 'eofs':
        mapmax = np.ceil(max(abs(np.nanmin(eofmap)), np.nanmax(eofmap)) / rmap) * rmap
        mapmin = -mapmax
    elif eofvar == 'corr':
        mapmin, mapmax = -1, 1
    elif eofvar == 'var':
        mapmin = 0
        r = 10
        mapmax = np.ceil(max(abs(np.nanmin(eofmap)), np.nanmax(eofmap)) / rmap) * rmap
    
    if normPCs == False:
        r = 500
        pcmax = np.ceil(max(abs(pcs.min()), pcs.max()) / rserie) * rserie

    for i in range(n):
        ax = fig.add_subplot(gs[i, 0])
        im = ax.imshow(eofmap[i,:,:], cmap='coolwarm', vmin=mapmin, vmax=mapmax)
        ax.contour(eofmap[i,:,:], np.linspace(mapmin, mapmax, 5), colors='k', linewidths=.5)
        ax.contour(eofmap[i,:,:], 0, colors='k', linewidths=1)
        ax.axis('off')
        if fvar is not None:
            title = 'EOF-' + str(i+1) + ' (' + str(int(fvar[i] * 100)) + '%)'
        else:
            title = 'EOF-' + str(i+1)
        ax.set_title(title, fontsize=13);
        ax = fig.add_subplot(gs[i, 1:])
        if normPCs == True:
            ax.fill_between(np.arange(0, pcs.shape[0]), 0, pcs[:,i] / np.std(pcs[:,i]),
                            color='grey', alpha=.4)
            ax.set(xlim=(0, pcs.shape[0]), ylim=(-3, 3))
            ax.set_ylabel('unidades normalizadas', fontsize=11)
        else:
            ax.fill_between(np.arange(0, pcs.shape[0]), 0, pcs[:,i], color='grey', alpha=.8)
            ax.set(xlim=(0, pcs.shape[0]), ylim=(-pcmax, pcmax))
        if i < n - 1:
            ax.set_xticklabels([])
        ax.set_title('PC-' + str(i+1), fontsize=13);
    # plt.tight_layout()

    # leyenda eofmaps
    cbar_ax = fig.add_axes([0.15, 0.09, 0.18, 0.01])
    cbar_ax.tick_params(labelsize=11)
    cb = plt.colorbar(im, cax=cbar_ax, orientation='horizontal')
    if eofvar == 'corr':
        label = 'correlacion (-)'
    elif eofvar == 'var':
        label = 'varianza explicada (%)'
    elif eofvar == 'eofs':
        label = '(mm)'
    cb.set_label(label, fontsize=13)


# #### eofMODIS



def eofMODIS(data, lats, nmodes, coordsIn='epsg:4326', lons=None, plot=None,
             normPCs=True, rmap=.1, rserie=100):
    """Hace un análisis EOF (empirical orthogonal functions) sobre los datos.
    
    Entradas:
    ---------
    data:     array (n,m,p). Las filas representan los pasos temporales, para los que hay una matriz (m, p) de la variable de estudio
    lats:     array (m,). Latitud de las filas de 'data'
    nmodes:        integer. Número de modos (tanto para EOFs como PCs) a extraer de la descomposición EOF
    coordsIn: string. Código epsg con el sistema de coordenadas de 'lats'. Por defecto WGS84 en coordenadas geográficas
    lons:     array (p,). Longitud de las columnas de 'data'. Sólo es necesario si 'coordsIn' difiere de 'epsg:4326'
    plot:     string. Si se quiere mostrar el gráfico de EOFs y PCs, se debe introducir la variable de interés: 'eofs', valores absolutos de los EOFs; 'corr', correlación; 'var', varianza explicada
    normPCS:  boolean. Si se quieren mostrar en el gráfico de PCs sus valores normalizados o no
    rmap:    float. Valor de redondeo de los mapas
    rserie:  float. Valor de redondeo de las series
    
    Salidas:
    --------
    Como métodos de la función.
        pcs:   array (n,nmodes). Series de los PCs para cada modo
        eofs:  array (nmodes,m,p). Mapa de los EOFs para cada modo
        corr:  array (nmodes,m,p). Para cada modo, mapa de correlación entre el PC y la serie temporal de cada celda
        var:   array (nmodes,m,p). Para cada modo, mapa de varianza explicada
        fvar:  array. Fracción de la varianza total explicada por cada uno de los modos (no sólo por lo 'nmodes' seleccionados)
    Si plot!=None, gráfico con los mapas de los EOFs y las series de los PCs.
    """
    
    if coordsIn != 'epsg:4326':
        if lons is None:
            print("ERROR. 'lons' es necesario para transformar las coordenadas")
        coordsIn = Proj(init=coordsIn)
        WGS84 = Proj(init='epsg:4326')
        lon = lons[int(len(lons) / 2)]
        lats = [transform(coordsIn, WGS84, lon, lat)[1] for lat in lats]       
    
    # pesos
    wgts = np.sqrt(np.cos(np.deg2rad(lats)))[:, np.newaxis]
    
    # crear un 'solver'
    solver = Eof(data, weights=wgts) #, weights=weights_array, center=True, ddof=1)
    
    # extraer resultados
    pcs = solver.pcs(npcs=nmodes)        # componentes principales
    eofs = solver.eofs(neofs=nmodes)     # empirical ortogonal functions (autovectores)
    lambdas = solver.eigenvalues()  # autovalores
    
    # fracción de varianza explicada 
    fvar = lambdas / np.sum(lambdas)
    
    # matriz F: filas, pasos temporales; columnas, puntos en el espacio
    F = data.reshape((data.shape[0], data.shape[1] * data.shape[2]))
    # correlación entre PCs y la serie de cada celda
    corr = np.ones((nmodes, F.shape[1])) * np.nan
    for j in range(F.shape[1]):
        if np.isnan(F[:,j]).sum() ==  len(F[:,j]):
            continue
        for i in range(nmodes):
            corr[i,j] = np.corrcoef(pcs[:,i], F[:,j])[0,1]
    corr = corr.reshape((nmodes, data.shape[1], data.shape[2]))
    
    # varianza entre los PCs y la serie de cada celda
    var = corr**2 * 100

    # retornar resultados como métodos
    eofMODIS.pcs = pcs
    eofMODIS.eofs = eofs
    eofMODIS.correlation = corr
    eofMODIS.explainedVariance = var
    eofMODIS.fractionVariance = fvar
    
    # gráficos
    if plot is not None:
        if plot == 'corr':
            mapa = corr
        elif plot == 'var':
            mapa = var
        elif plot == 'eofs':
            mapa = eofs
        plotEOF(mapa, pcs, eofvar=plot, normPCs=normPCs, fvar=fvar,
                rmap=rmap, rserie=rserie)






