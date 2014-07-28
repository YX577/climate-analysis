# zw3_tscale_analysis.mk
#
# There are two parts to the timescale analysis. An objective part (using plot_freq_spectrum.py to calculate the average 
# spectra over the entire time period) and a visual part (which is detailed here). 
#
# The overall aim of the visual part is to reproduce the images I showed in a previous meeting with Ian, for 3-years of 
# individual days for a running mean of 1, 5, 30, 90, 180 days. Those images had three panels:
#  - A map of the wave envelope with zonal streamfunction anomaly over the top (/visualisation/plot_envelope.py)
#  - One map of the power spectrum and the other of each component of the Fourier Transform (/testing/plot_hilbert.py)
#
# To execute:
#   make -n -B -f zw3_tscale_analysis.mk  (-n is a dry run) (-B is a force make)


### Define marcos ###

include zw3_tscale_analysis_config.mk

## Phony target
all : ${TARGET}

### Wave envelope map ###

## Step 1a: Apply temporal averaging to the meridional wind data (for a limited time period)
${PDATA_DIR}/va_Merra_250hPa_${TSCALE_LABEL}_native.nc : ${DATA_DIR}/va_Merra_250hPa_daily_native.nc
	cdo ${TSCALE} -${PERIOD} $< $@
	ncatted -O -a axis,time,c,c,T $@

## Step 1b: Regrid the meridional wind data
${PDATA_DIR}/va_Merra_250hPa_${TSCALE_LABEL}_${GRID}.nc : ${PDATA_DIR}/va_Merra_250hPa_${TSCALE_LABEL}_native.nc
	cdo remapcon2,${GRID} $< $@
	ncatted -O -a axis,time,c,c,T $@

## Step 1c: Extract the wave envelope
${RWID_DIR}/env-${WAVE_LABEL}-va_Merra_250hPa_${TSCALE_LABEL}_${GRID}.nc : ${PDATA_DIR}/va_Merra_250hPa_${TSCALE_LABEL}_${GRID}.nc
	${CDAT} ${DATA_SCRIPT_DIR}/calc_fourier_transform.py $< va $@ ${WAVE_SEARCH}

## Step 2a: Calculate the streamfunction zonal anomaly
${PDATA_DIR}/sf_Merra_250hPa_daily-zonal-anom_native.nc : ${PDATA_DIR}/sf_Merra_250hPa_daily_native.nc       
	${ZONAL_ANOM_METHOD} $< sf $@
	ncatted -O -a axis,time,c,c,T $@

## Step 2b: Apply temporal averaging to the zonal streamfunction data (for a limited time period)
${PDATA_DIR}/sf_Merra_250hPa_${TSCALE_LABEL}-zonal_anom_native.nc : ${PDATA_DIR}/sf_Merra_250hPa_daily-zonal-anom_native.nc
	cdo ${TSCALE} -${PERIOD} $< $@
	ncatted -O -a axis,time,c,c,T $@

## Step 3: Plot the envelope
${RWID_DIR}/figures/env-${WAVE_LABEL}-va_Merra_250hPa_${TSCALE_LABEL}_${GRID}_${PLOT_END}.png : ${RWID_DIR}/env-${WAVE_LABEL}-va_Merra_250hPa_${TSCALE_LABEL}_${GRID}.nc ${PDATA_DIR}/sf_Merra_250hPa_${TSCALE_LABEL}-zonal_anom_native.nc
	${CDAT} ${VIS_SCRIPT_DIR}/plot_envelope.py $< env ${TSCALE_LABEL} --contour $(word 2,$^) sf --time ${PLOT_START} ${PLOT_END} none --projection spstere --ofile $@