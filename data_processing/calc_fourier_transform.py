"""
Filename:     calc_fourier_transform.py
Author:       Damien Irving, d.irving@student.unimelb.edu.au

"""

# Import general Python modules

import sys, os
import argparse
import numpy
from scipy import fftpack
from copy import deepcopy
import pdb

# Import my modules #

cwd = os.getcwd()
repo_dir = '/'
for directory in cwd.split('/')[1:]:
    repo_dir = os.path.join(repo_dir, directory)
    if directory == 'phd':
        break

modules_dir = os.path.join(repo_dir, 'modules')
sys.path.append(modules_dir)

try:
    import netcdf_io as nio
    import coordinate_rotation as crot
except ImportError:
    raise ImportError('Must run this script from anywhere within the phd git repo')


# Define functions #


def apply_lon_filter(data, lon_bounds):
    """Set all values outside of the specified longitude range [lon_bounds[0], lon_bounds[1]] to zero."""
    
    # Convert to common bounds (0, 360) #
 
    lon_min = crot.adjust_lon_range(lon_bounds[0], radians=False, start=0.0)
    lon_max = crot.adjust_lon_range(lon_bounds[1], radians=False, start=0.0)
    lon_axis = crot.adjust_lon_range(data.getLongitude()[:], radians=False, start=0.0)

    # Make required values zero #
    
    ntimes, nlats, nlons = data.shape
    lon_axis_tiled = numpy.tile(lon_axis, (ntimes, nlats, 1))
    
    new_data = numpy.where(lon_axis_tiled < lon_min, 0.0, data)
    
    return numpy.where(lon_axis_tiled > lon_max, 0.0, new_data)


def power_spectrum(signal_fft, sample_freq):
    """Calculate the power spectrum for a given Fourier Transform"""
    
    pidxs = numpy.where(sample_freq > 0)
    freqs, power = sample_freq[pidxs], numpy.abs(sig_fft)[pidxs]
    
    return freqs, power
    

def filter_signal(signal, indep_var, min_freq, max_freq):
    """Filter a signal by performing a Fourier Tranform and then
    an inverse Fourier Transform for a selected range of frequencies"""
    
    sig_fft, sample_freq = fourier_transform(signal, indep_var)
    filtered_signal = inverse_fourier_transform(sig_fft, sample_freq, min_freq=min_freq, max_freq=max_freq)
    
    return filtered_signal


def fourier_transform(signal, indep_var):
    """Calculate the Fourier Transform.
    
    Input arguments:
        indep_var  ->  Independent variable (i.e. time axis or longitude axis)
    
    Output:
        sig_fft    ->  Coefficients obtained from the Fourier Transform
        freqs      ->  Wave frequency associated with each coefficient
        power      ->  Power associated with each frequency (i.e. abs(sig_fft))
    
    """
    
    spacing = indep_var[1] - indep_var[0]
    sample_freq = fftpack.fftfreq(signal.size, d=spacing) * signal.size * spacing  # i.e. in units of cycles per length of domain
    sig_fft = fftpack.fft(signal)
    
    return sig_fft, sample_freq


def inverse_fourier_transform(coefficients, sample_freq, min_freq=None, max_freq=None, exclude=None):
    """Inverse Fourier Transform.
    
    Input arguments:
        max_freq, min_freq   ->  Can filter to only include a certain
                                 frequency range. 
	exclude              ->  Can exclude either the 'positive' or 
	                         'negative' half of the Fourier spectrum  
                                 
    """
    
    assert exclude in ['positive', 'negative', None]
    
    coefs = deepcopy(coefficients)  # Deep copy to prevent side effects
                                    # (shallow copy not sufficient for complex
				    # things like numpy arrays)
    
    if exclude == 'positive':
        coefs[sample_freq > 0] = 0
    elif exclude == 'negative':
        coefs[sample_freq < 0] = 0
    
    if (max_freq == min_freq) and max_freq:
        coefs[numpy.abs(sample_freq) != max_freq] = 0
    
    if max_freq:
        coefs[numpy.abs(sample_freq) > max_freq] = 0
    
    if min_freq:
        coefs[numpy.abs(sample_freq) < min_freq] = 0
    
    result = fftpack.ifft(coefs)
    
    return result


def main(inargs):
    """Run the program."""
    
    # Read input data #
    
    indata = nio.InputData(inargs.infile, inargs.variable, 
                           **nio.dict_filter(vars(inargs), ['time', 'latitude']))
    
    assert indata.data.getOrder()[-1] == 'x', \
    'This is setup to perform the fourier transform along the longitude axis'
    
    # Apply longitude filter (i.e. set unwanted longitudes to zero) #
    
    data_masked = apply_lon_mask(indata.data, inargs.longitude) if inargs.longitude else indata.data
    
    # Perform the filtering #
    
    if inargs.outtype == 'filter':
        method = 'Fourier transform filtered'
    elif inargs.outtype == 'hilbert':
        method = 'Hiblert transformed'
    
    if inargs.filter:
        min_freq, max_freq = inargs.filter
	filter_text = '%s with frequency range: %s to %s' %(method, min_freq, max_freq)
    else:
        min_freq = max_freq = None
	filter_text = '%s with all frequencies retained' %(method)
    
    outdata = numpy.apply_along_axis(filter_signal, -1, data_masked, indata.data.getLongitude()[:], min_freq, max_freq)
    if inargs.outtype == 'hilbert':
        outdata = numpy.abs(outdata)
    
    
    # Write output file #

    var_atts = {'id': indata.data.id,
                'standard_name': method+' '+indata.data.long_name,
                'long_name': method+' '+indata.data.long_name,
                'units': indata.data.units,
                'history': filter_text}

    outdata_list = [outdata,]
    outvar_atts_list = [var_atts,]
    outvar_axes_list = [indata.data.getAxisList(),]

    nio.write_netcdf(inargs.outfile, " ".join(sys.argv), 
                     indata.global_atts, 
                     outdata_list,
                     outvar_atts_list, 
                     outvar_axes_list)


if __name__ == '__main__':

    extra_info =""" 
example (vortex.earthsci.unimelb.edu.au):

author:
  Damien Irving, d.irving@student.unimelb.edu.au

"""

    description='Perform Fourier Transform along lines of constant latitude'
    parser = argparse.ArgumentParser(description=description,
                                     epilog=extra_info, 
                                     argument_default=argparse.SUPPRESS,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument("infile", type=str, help="Input file name")
    parser.add_argument("variable", type=str, help="Input file variable")
    parser.add_argument("outfile", type=str, help="Output file name")
			
    # Input data options
    parser.add_argument("--latitude", type=float, nargs=2, metavar=('START', 'END'),
                        help="Latitude range over which to perform Fourier Transform [default = entire]")
    parser.add_argument("--longitude", type=float, nargs=2, metavar=('START', 'END'), default=None,
                        help="Longitude range over which to perform Fourier Transform (all other values are set to zero) [default = entire]")
    parser.add_argument("--time", type=str, nargs=3, metavar=('START_DATE', 'END_DATE', 'MONTHS'),
                        help="Time period [default = entire]")

    # Output options
    parser.add_argument("--filter", type=int, nargs=2, metavar=('LOWER', 'UPPER'), default=None,
                        help="Range of frequecies to retain in filtering [e.g. 3,3 would retain the wave that repeats 3 times over the domain")
    parser.add_argument("--outtype", type=str, default='filter', choices=('filter', 'hilbert'),
                        help="The output can be a filtered signal or a hilbert transform")

  
    args = parser.parse_args()            

    print 'Input files: ', args.infile
    print 'Output file: ', args.outfile  

    main(args)