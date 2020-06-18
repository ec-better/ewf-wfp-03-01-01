import os
import sys

import gdal
import numpy as np
import math
from py_snap_helpers import *

def get_mask(flag, lqsf):
    
    pixel_classif_flags = {'INVALID': 1,
                             'WATER': 2,
                             'LAND': 4,
                             'CLOUD': 8,
                             'CLOUD_AMBIGUOUS': 8388608,
                             'CLOUD_MARGIN': 16777216,
                             'SNOW_ICE': 16,
                             'INLAND_WATER': 32,
                             'TIDAL': 64,
                             'COSMETIC': 128,
                             'SUSPECT': 256, 
                          'HISOLZEN': 512,
                          'SATURATED': 1024,
                          'WV_FAIL': 2048,
                          'OGVI_FAIL': 4096,
                          'OTCI_FAIL': 8192,
                          'LRAYFAIL': 16384,
                          'OGVI_CLASS_BAD': 32768,
                          'OGVI_CLASS_WS': 65536,
                          'OGVI_CLASS_CSI': 131072,
                          'OGVI_CLASS_BRIGHT': 262144,
                          'OGVI_CLASS_INVAL_REC': 524288,
                          'OTCI_BAD_IN': 1048576,
                          'OTCI_CLASS_ANG': 2097152,
                          'OTCI_CLASS_CLSN': 4194304
                          }
    
    
    b1 = int(math.log(pixel_classif_flags[flag], 2))
    b2 = b1
    
    return _capture_bits(lqsf.astype(np.int64), b1, b2)

def _capture_bits(arr, b1, b2):
    
    width_int = int((b1 - b2 + 1) * "1", 2)
 
    return ((arr >> b2) & width_int).astype('uint8')

def export_s3(bands):

    ds = gdal.Open(bands[0])
    
    width = ds.RasterXSize
    height = ds.RasterYSize

    input_geotransform = ds.GetGeoTransform()
    input_georef = ds.GetProjectionRef()
    
    ds = None
    
    driver = gdal.GetDriverByName('GTiff')
    
    output = driver.Create('s3.tif', 
                       width, 
                       height, 
                       len(bands), 
                       gdal.GDT_Float32)

    output.SetGeoTransform(input_geotransform)
    output.SetProjection(input_georef)
    
    for index, band in enumerate(bands):
        print(band)
        temp_ds = gdal.Open(band) 
        
        band_data = temp_ds.GetRasterBand(1).ReadAsArray()
        output.GetRasterBand(index+1).WriteArray(band_data)
        
    output.FlushCache()
    
    return True

def read_s3(bands):

    gdal.UseExceptions()
    
    stack = []
    
    for index, band in enumerate(bands):
        
        temp_ds = gdal.Open(band) 
 
        if not temp_ds:
            raise ValueError()
            
        stack.append(temp_ds.GetRasterBand(1).ReadAsArray())
      
    return np.dstack(stack)


def s3_olci_import(idepix, **kwargs):
   
    options = dict()
    
    operators = ['Read', 
                 'Idepix.Sentinel3.Olci',
                 'Reproject',
                 'Write']
    
    for operator in operators:
            
        print('Getting default values for Operator {}'.format(operator))
        parameters = get_operator_default_parameters(operator)
        
        options[operator] = parameters

    for key, value in kwargs.items():
        
        print('Updating Operator {}'.format(key))
        options[key.replace('_', '-')].update(value)
     
    mygraph = GraphProcessor()
    
    for index, operator in enumerate(operators):
    
        print('Adding Operator {} to graph'.format(operator))
        if index == 0:            
            source_node_id = ''
        
        else:
            source_node_id = operators[index - 1]
       
        if operator == 'Idepix.Olci':
            
            mygraph.add_node(operator,
                             operator, 
                             idepix, source_node_id)
        else:
            mygraph.add_node(operator,
                             operator, 
                             options[operator], source_node_id)
    
    mygraph.run()
    
    
def s3_rgb_composite(red, green, blue, classif_flags, geo_transform, projection_ref, output_name, hfact=5.0):

    rgb_r = np.zeros(red.shape)
    rgb_g = np.zeros(red.shape)
    rgb_b = np.zeros(red.shape)
    
    mask_cloud = get_mask('IDEPIX_CLOUD', classif_flags)

    mask = (red == -10000) | (green == -10000) | (blue == -10000) | (red > 1) | (green > 1) | (blue > 1) 
    
    rgb_r = np.where(mask,
                     0,
                     red*255).astype(np.uint8)
    
    rgb_g = np.where(mask,
                     0,
                     green*255).astype(np.uint8)
    
    rgb_b = np.where(mask,
                     0,
                     blue*255).astype(np.uint8)
    
    alpha = np.where(mask, 
                     0,
                     255).astype(int)

    # contrast enhancement
    ContrastEnhancement = otbApplication.Registry.CreateApplication('ContrastEnhancement')

    rgb_data = np.dstack([rgb_r, rgb_g, rgb_b])
    
    ContrastEnhancement.SetVectorImageFromNumpyArray('in', rgb_data)
    
    ContrastEnhancement.SetParameterOutputImagePixelType('out', 
                                                         otbApplication.ImagePixelType_uint8)
    ContrastEnhancement.SetParameterFloat('nodata', 0.0)
    ContrastEnhancement.SetParameterFloat('hfact', hfact)
    ContrastEnhancement.SetParameterInt('bins', 256)
    ContrastEnhancement.SetParameterInt('spatial.local.w', 500)
    ContrastEnhancement.SetParameterInt('spatial.local.h', 500)
    ContrastEnhancement.SetParameterString('mode', 'lum')

    ContrastEnhancement.Execute()

    ce_data = ContrastEnhancement.GetVectorImageAsNumpyArray('out')
            
    rgb_r = None
    rgb_g = None
    rgb_b = None

    driver = gdal.GetDriverByName('GTiff')

    output = driver.Create(output_name, 
                           ce_data.shape[1], 
                           ce_data.shape[0], 
                           4, 
                           gdal.GDT_Byte)

    output.SetGeoTransform(geo_transform)
    output.SetProjection(projection_ref)
    output.GetRasterBand(1).WriteArray(ce_data[:,:,0])
    output.GetRasterBand(2).WriteArray(ce_data[:,:,1])
    output.GetRasterBand(3).WriteArray(ce_data[:,:,2])
    output.GetRasterBand(4).WriteArray(alpha)
    
    output.FlushCache()
    
    output = None
    
    return rgb_r, rgb_g, rgb_b, alpha