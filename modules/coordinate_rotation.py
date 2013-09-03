"""Collection of functions for changing spherical
coordinate system.

To import:
module_dir = os.path.join(os.environ['HOME'], 'data_processing')
sys.path.insert(0, module_dir)

Included functions:
adjust_lon_range
  --  Express longitude values in desired 360 degree interval

rotation_matrix  
  --  Get the rotation matrix or its inverse
rotate_cartesian  
  --  Convert from geographic cartestian coordinates (x, y, z) to
      rotated cartesian coordinates (xrot, yrot, zrot)  
rotate_spherical
  --  Convert from geographic spherical coordinates (lat, lon) to
      rotated spherical coordinates (latrot, lonrot)

angular_distance
  --  Calculate angular distance between two points on a sphere
rotation_angle
  --  Find angle of rotation between the old and new north pole.

plot_equator
  --  Plot the rotated equator

Reference:
Rotation theory: http://www.ocgy.ubc.ca/~yzq/books/MOM3/s4node19.html

Required improvements:
1. In rotation_angle(), what do I do when side a or b of the spherical
   triangle is equal to zero (and hence no triangle exists)? This occurs 
   when the point of interest (C) is at the same point as the old (A) or 
   new (B) north pole. 
2. I've come across a number of issues related to numerical precision.
   These have been covered over with makeshfit functions like _filter_tiny()
   and _arccos_check(), however I would prefer if these functions weren't 
   required.
3. Many of the functions lack assertions (e.g. assert that the input is a 
   numpy array).
4. Look for opportunities to process data as multidimensional arrays, instead
   of using mesh/flatten or looping.
   
"""

#############################
## Import required modules ##
#############################

import math
import numpy
from mpl_toolkits.basemap import Basemap
import matplotlib.pyplot as plt

import MV2
import css

import sys
import os 
module_dir = os.path.join(os.environ['HOME'], 'modules')
sys.path.insert(0, module_dir)
import netcdf_io as nio

import pdb


##########################################
## Switching between coordinate systems ##
##########################################

def switch_axes(data, lats, lons, new_np, pm_point=None, invert=False):
    """Take some data on a regular grid (lat, lon), rotate the axes 
    (according to the position of the new north pole) and regrid to 
    a regular grid with the same resolution as the original
    
    Note inputs for css.Cssgrid:
    - lats_rot and loDefault range = [0, 360)
    
    Input and output can be in radians or degrees.
    
    """

    phi, theta, psi = north_pole_to_rotation_angles(new_np[0], new_np[1], prime_meridian_point=pm_point)   

    lats_rot, lons_rot = rotate_spherical(lats, lons, phi, theta, psi, invert=invert)

    grid_instance = css.Cssgrid(lats_rot, lons_rot, lats, lons)
    if numpy.rank(data) == 3:
        data_rot = numpy.zeros(numpy.shape(data))
        for tstep in range(0, numpy.shape(data)[0]):
	    regrid = grid_instance.rgrd(data[tstep, :, :].flatten())
	    data_rot[tstep, :, :] = numpy.transpose(regrid)
    else: 
        regrid = grid_instance.rgrd(data.flatten())
	data_rot = numpy.transpose(regrid)
        
    #### NOTE: the regridding of rgrd seems to be fairly accurate (i.e. when you give it 
    #### the same input and output grid) except at the poles (ie when the lat = 90 or -90)
    #### This may relate to the problems at the poles the css2c and csc2s have - I'm not
    #### sure if rgrd uses these functions.
    
    return data_rot


###########################
## Numerical adjustments ##
###########################

def _filter_tiny(data, threshold=0.000001):
    """Convert values of magnitude < threshold to zero"""

    return numpy.where(numpy.absolute(data) < threshold, 0.0, data)
 

def adjust_lon_range(lons, radians=True, start=0.0):
    """Express longitude values in the 360 degree (or 2*pi radians)
    interval that begins at start.

    Default range = [0, 360)
    
    Input and output can be in radians or degrees.
    """
    
    lons = nio.single2list(lons, numpy_array=True)    
    
    interval360 = 2.0*numpy.pi if radians else 360.0
    end = start + interval360    
    
    less_than_start = numpy.ones([len(lons),])
    while numpy.sum(less_than_start) != 0:
        lons = numpy.where(lons < start, lons + interval360, lons)
        less_than_start = lons < start
    
    more_than_end = numpy.ones([len(lons),])
    while numpy.sum(more_than_end) != 0:
        lons = numpy.where(lons >= end, lons - interval360, lons)
        more_than_end = lons >= end

    return lons


#################################
## Coordinate system rotations ##
#################################

def rotation_matrix(phir, thetar, psir, inverse=False):
    """Get the rotation matrix or its inverse.
    Inputs angles are expected in radians.
    Reference: http://www.ocgy.ubc.ca/~yzq/books/MOM3/s4node19.html
    Note that the transformation matrix (and its inverse) given in
    the reference is exactly correct - I checked the derivation by hand.
    """
    
    for angle in [phir, thetar, psir]:
        assert 0.0 <= math.fabs(angle) <= 2*math.pi, \
	"Input angles must be in radians [0, 2*pi]" 
    
    matrix = numpy.empty([3, 3])
    if not inverse:
	matrix[0,0] = (numpy.cos(psir) * numpy.cos(phir)) - (numpy.cos(thetar) * numpy.sin(phir) * numpy.sin(psir))
	matrix[0,1] = (numpy.cos(psir) * numpy.sin(phir)) + (numpy.cos(thetar) * numpy.cos(phir) * numpy.sin(psir))
	matrix[0,2] = numpy.sin(psir) * numpy.sin(thetar)

	matrix[1,0] = -(numpy.sin(psir) * numpy.cos(phir)) - (numpy.cos(thetar) * numpy.sin(phir) * numpy.cos(psir))
	matrix[1,1] = -(numpy.sin(psir) * numpy.sin(phir)) + (numpy.cos(thetar) * numpy.cos(phir) * numpy.cos(psir))
	matrix[1,2] = numpy.cos(psir) * numpy.sin(thetar)

	matrix[2,0] = numpy.sin(thetar) * numpy.sin(phir)
	matrix[2,1] = -numpy.sin(thetar) * numpy.cos(phir)
	matrix[2,2] = numpy.cos(thetar)

    else:
	matrix[0,0] = (numpy.cos(psir) * numpy.cos(phir)) - (numpy.cos(thetar) * numpy.sin(phir) * numpy.sin(psir))
	matrix[0,1] = -(numpy.sin(psir) * numpy.cos(phir)) - (numpy.cos(thetar) * numpy.sin(phir) * numpy.cos(psir))
	matrix[0,2] = numpy.sin(thetar) * numpy.sin(phir) 

	matrix[1,0] = (numpy.cos(psir) * numpy.sin(phir)) + (numpy.cos(thetar) * numpy.cos(phir) * numpy.sin(psir))
	matrix[1,1] = -(numpy.sin(psir) * numpy.sin(phir)) + (numpy.cos(thetar) * numpy.cos(phir) * numpy.cos(psir))
	matrix[1,2] = -numpy.sin(thetar) * numpy.cos(phir)

	matrix[2,0] = numpy.sin(thetar) * numpy.sin(psir)
	matrix[2,1] = numpy.sin(thetar) * numpy.cos(psir)
	matrix[2,2] = numpy.cos(thetar)

    return matrix


def rotate_cartesian(x, y, z, phir, thetar, psir, invert=False):
    """Rotate cartestian coordinate system (x, y, z) according to a rotation 
    about the origial z axis (phir), new z axis after the first rotation (thetar),
    and about the final z axis (psir).
    
    Invert can be true or false.
    Input angles are expected in degrees.
    """

    phir_rad = numpy.deg2rad(phir)
    thetar_rad = numpy.deg2rad(thetar)
    psir_rad = numpy.deg2rad(psir)

    input_matrix = numpy.array([x.flatten(), y.flatten(), z.flatten()])
    A = rotation_matrix(phir_rad, thetar_rad, psir_rad, inverse=invert)
        
    dot_product = numpy.dot(A, input_matrix)
    xrot = dot_product[0, :]
    yrot = dot_product[1, :]
    zrot = dot_product[2, :]
    
    return xrot, yrot, zrot
    

def rotate_spherical(lat_axis, lon_axis, phir, thetar, psir, invert=False):
    """Rotate spherical coordinate system (lat, lon) according to the rotation 
    about the origial z axis (phir), new x axis after the first rotation (thetar),
    and about the final z axis (psir).
    
    Inputs and outputs are all in degrees. Longitudes are output [0, 360]
    Output is a flattened lat and lon array, with element-wise pairs corresponding 
    to every grid point.
    """
    
    lons, lats = nio.coordinate_pairs(lon_axis, lat_axis) 
    
    x, y, z = css.cssgridmodule.css2c(lats, lons)
    xrot, yrot, zrot = rotate_cartesian(x, y, z, phir, thetar, psir, invert=invert)
    latrot, lonrot = css.cssgridmodule.csc2s(xrot, yrot, zrot)
    
    #### At the poles, csc2s produces longitude values that are 180 degrees out of
    #### phase with the original data.
    #### It also outputs lons that are (-180, 180), but this is not really a problem.

    
    return latrot, _adjust_lon_range(lonrot) 


############################
## Spherical trigonometry ##
############################

def _arccos_check(data):
    """Adjust for precision errors when using numpy.arccos
    
    numpy.arccos is only defined [-1, 1]. Sometimes due to precision
    you can get values that are very slightly > 1 or < -1, which causes
    numpy.arccos to be undefinded. This function adjusts for this.
        
    """
    
    data = numpy.clip(data, -1.0, 1.0)
    
    return data


def angular_distance(lat1deg, lon1deg, lat2deg, lon2deg):
    """Find the angular distance between two points on
    the sphere.
    
    Calculation taken from http://www.movable-type.co.uk/scripts/latlong.html
    
    Assumes a sphere of unit radius.
    
    Input in degrees. Output in radians.
    """

    lat1 = numpy.deg2rad(lat1deg)
    lon1 = numpy.deg2rad(lon1deg)
    lat2 = numpy.deg2rad(lat2deg)
    lon2 = numpy.deg2rad(lon2deg)

    angular_dist = numpy.arccos(numpy.sin(lat1)*numpy.sin(lat2) + numpy.cos(lat1)*numpy.cos(lat2)*numpy.cos(lon2 - lon1))
    #calc taken from http://www.movable-type.co.uk/scripts/latlong.html
    #says it is based on the spherical law of cosines, but I need to verfiy this
      
    return _filter_tiny(angular_dist)
    

def rotation_angle(latA, lonA, latB, lonB, latsC, lonsC, reshape=None):
    """For a given point on the sphere, find the angle of rotation 
    between the old and new north pole.
    
    Formulae make use of spherical triangles and are based 
    on the spherical law of cosines. 
    
    Inputs:
      Point A = Location of original north pole
      Point B = Location of new north pole
      Point C = Point of interest
      reshape = Reshaped dimensions of output array
      
      Input in degrees
      
      There can be only one specified original and new north pole, 
      but multiple points of interest.
    
    Output:
      Angle C = Rotation angle between old and new north pole
      Output in radians
      
    ERROR TO FIX:
      When both the old and new pole are the same and the latitude=90,
      the rotation angle is pi, not zero.
    """
    
    ##Some assertions (e.g. latA, lonA, latB, lonB must be len=1, while latC and lonC do not 
    ##Perhaps change names of latA etc to something more meaningful (e.g. new_np_lat)?

    latsC = nio.single2list(latsC)
    lonsC = nio.single2list(lonsC)

    latA_flat = numpy.repeat(latA, len(lonsC))
    lonA_flat = numpy.repeat(lonA, len(lonsC))
    latB_flat = numpy.repeat(latB, len(lonsC))
    lonB_flat = numpy.repeat(lonB, len(lonsC))

    a_vals = angular_distance(latB_flat, lonB_flat, latsC, lonsC)
    b_vals = angular_distance(latA_flat, lonA_flat, latsC, lonsC)
    c_vals = angular_distance(latA_flat, lonA_flat, latB_flat, lonB_flat)

    #### QUICK FIX - MUST BE REPLACED BY A FIX FOR WHEN locationC = locationA or locationB, which makes a or b zero
    a_vals = numpy.where(a_vals == 0.0, 1.0, a_vals)
    b_vals = numpy.where(b_vals == 0.0, 1.0, b_vals)
    ####

    #angleA_magnitude = numpy.arccos((numpy.cos(a) - numpy.cos(b)*numpy.cos(c)) / (numpy.sin(b)*numpy.sin(c)))
    #angleB_magnitude = numpy.arccos((numpy.cos(b) - numpy.cos(c)*numpy.cos(a)) / (numpy.sin(c)*numpy.sin(a)))
    angleC_magnitude = numpy.arccos(_arccos_check((numpy.cos(c_vals) - numpy.cos(a_vals)*numpy.cos(b_vals)) / (numpy.sin(a_vals)*numpy.sin(b_vals))))

    angleC = _rotation_sign(angleC_magnitude, lonB_flat, lonsC)
    
#    pdb.set_trace()
#    test = angleC > 0.1
#    error_lats = numpy.extract(test, latsC)
#    error_lons = numpy.extract(test, lonsC)
    
    if reshape:
        angleC = numpy.reshape(angleC, reshape)
    
    return _filter_tiny(angleC)


def _rotation_sign(angleC, lonB, lonC):
    """Determine the sign of the rotation angle.

    The basic premise is that grid points (lonC) with a longitude in the range of
    180 degrees less than the longitude of the new pole (lonB) have a negative angle.

    Not sure if this is a universal rule (i.e. this works for when the original
    north pole was at 90N, 0E) 

    """
    
    lonB = single2list(lonB, numpy_array=True)
    lonC = single2list(lonC, numpy_array=True)

    assert len(lonB) == len(lonC), \
    "Input arrays must be the same length"   

    lonB_360 = _adjust_lon_range(lonB, radians=False, start=0.0)
    lonC_360 = _adjust_lon_range(lonC, radians=False, start=0.0)

    new_start = lonB_360[0] - 180.0

    lonB_360 = _adjust_lon_range(lonB_360, radians=False, start=new_start)
    lonC_360 = _adjust_lon_range(lonC_360, radians=False, start=new_start)

    angleC_adjusted = numpy.where(lonC_360 < lonB_360, -angleC, angleC)

    return angleC_adjusted
   
    
#############################
## North pole manipulation ##
#############################

def north_pole_to_rotation_angles(latnp, lonnp, prime_meridian_point=None):
    """Convert position of rotated north pole to a rotation about the
    original z axis (phir) and new z axis after the first rotation (thetar).
    
    Input and output in degrees.
    
    The prime meridian point should be a list of length 2 (lat, lon), representing a
    point through which the prime meridian should travel.
    
    """

    psir = 90.0 - lonnp
    thetar = 90.0 - latnp 

    if prime_meridian_point:
        ## I don't fully understand the setting of phir
        assert len(prime_meridian_point) == 2, \
	'The prime point must be a list of length 2'
	pm_lat = prime_meridian_point[0] 
	pm_lon = prime_meridian_point[1] 
        lat_temp, phir = rotate_spherical(numpy.array([pm_lat,]), numpy.array([pm_lon,]), 0.0, thetar, psir)
    else:
        phir = 0.0
    
    return phir, thetar, psir    
			
              
################### 
## Visualisation ##
###################

def plot_equator(npole_lat, npole_lon, psir_deg, projection='cyl', ofile=False):
    """Plot the rotated equator"""

    phir, thetar = north_pole_to_rotation_angles(npole_lat, npole_lon)   #30.0, 0.0 gives a nice PSA line
    psir = numpy.deg2rad(psir_deg) 

    lonrot = numpy.arange(0, 360, 1) 
    latrot = numpy.zeros(len(lonrot))

    latgeo, longeo = rotated_to_geographic_spherical(numpy.deg2rad(latrot), numpy.deg2rad(lonrot), phir, thetar, psir)

    #print values to screen

    for i in range(0, len(latgeo)):
        print '(%s, %s) rotated becomes (%s, %s) geographic'  %(latrot[i], lonrot[i], numpy.rad2deg(latgeo[i]), numpy.rad2deg(longeo[i]))

    #create the plot
    if projection == 'nsper':
        h = 12000  #height of satellite, 
        lon_central = 235
        lat_central = -60
        map = Basemap(projection='nsper', lon_0=lon_central, lat_0=lat_central, satellite_height=h*1000.)
    else:
        map = Basemap(llcrnrlon=0, llcrnrlat=-90, urcrnrlon=360, urcrnrlat=90, projection='cyl')

    map.drawcoastlines()
    map.drawparallels(numpy.arange(-90,90,30),labels=[1,0,0,0],color='grey',dashes=[1,3])
    map.drawmeridians(numpy.arange(0,360,45),labels=[0,0,0,1],color='grey',dashes=[1,3])
    #map.drawmapboundary(fill_color='#99ffff')

    lats = numpy.rad2deg(latgeo)
    lons = numpy.rad2deg(longeo)
    x, y = map(lons, lats)
    map.scatter(x, y, linewidth=1.5, color='r')

    if ofile:
        plt.savefig(ofile)
    else:
        plt.show()