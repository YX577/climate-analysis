# zw_composites.mk
#
# Description: Calculate composite for variable of interest (e.g. tas, pr, sic)
#
# Composite methods:
#   conventional: calculate composite mean variable for times where index exceeds threshold
#   reverse: calculate composite mean index for times where variable anomaly exceeds threshold 
#
# Thresholds:
#   upper: e.g. > 90th percentile
#   lower: e.g. < 10th percentile  
#
# To execute:
#   make -n -B -f zw_composites.mk  (-n is a dry run) (-B is a force make)

# Define marcos
include zw_config.mk
include zw_base.mk

all : ${TARGET}

# Baseline data

## Calculate the anomaly for the variable of interest and apply temporal averaging
COMP_VAR_ORIG=${DATA_DIR}/${COMP_VAR}_${DATASET}_surface_daily_${GRID}.nc
COMP_VAR_ANOM_RUNMEAN=${DATA_DIR}/${COMP_VAR}_${DATASET}_surface_${TSCALE_LABEL}-anom-wrt-all_native.nc
${COMP_VAR_ANOM_RUNMEAN} : ${COMP_VAR_ORIG} 
	cdo ${TSCALE} -ydaysub $< -ydayavg $< $@
	bash ${CDO_FIX_SCRIPT} $@ ${COMP_VAR}


# Composite envelope (with contour overlay)

## Step 1: Get the composite mean envelope
COMP_ENV_FILE=${COMP_DIR}/env${VAR}-composite_zw_${METRIC}${METRIC_HIGH_THRESH}-${ENV_WAVE_LABEL}_env-${VAR}_${DATASET}_${LEVEL}_${TSCALE_LABEL}_${GRID}.nc 
${COMP_ENV_FILE} : ${ENV_3D} ${DATE_LIST} 
	${PYTHON} ${DATA_SCRIPT_DIR}/calc_composite.py $< env${VAR} $@ --date_file $(word 2,$^) 

## Step 2: Get the composite mean contour
CONTOUR_ZONAL_ANOM_RUNMEAN_COMP=${COMP_DIR}/${CONTOUR_VAR}-composite_zw_${METRIC}${METRIC_HIGH_THRESH}-${ENV_WAVE_LABEL}_env-${VAR}_${DATASET}_${LEVEL}_${TSCALE_LABEL}_native-zonal-anom.nc 
${CONTOUR_ZONAL_ANOM_RUNMEAN_COMP} : ${CONTOUR_ZONAL_ANOM_RUNMEAN} ${DATE_LIST} 
	${PYTHON} ${DATA_SCRIPT_DIR}/calc_composite.py $< ${CONTOUR_VAR} $@ --date_file $(word 2,$^)

## Step 3: Plot
COMP_ENV_PLOT=${COMP_DIR}/env${VAR}-composite_zw_${METRIC}${METRIC_HIGH_THRESH}-${ENV_WAVE_LABEL}_env-${VAR}-${CONTOUR_VAR}_${DATASET}_${LEVEL}_${TSCALE_LABEL}_${GRID}-zonal-anom.png
${COMP_ENV_PLOT} : ${COMP_ENV_FILE} ${CONTOUR_ZONAL_ANOM_RUNMEAN_COMP}
	bash ${VIS_SCRIPT_DIR}/plot_composite.sh $(word 1,$^) env${VAR} $(word 2,$^) ${CONTOUR_VAR} $@ ${PYTHON} ${VIS_SCRIPT_DIR}


# Conventional variable composite, upper threshold of PWI

## Step 1: Calculate variable composite 
COMP_VAR_PWI_FILE=${COMP_DIR}/${COMP_VAR}-composite_zw_${METRIC}${METRIC_HIGH_THRESH}-${ENV_WAVE_LABEL}_env-${VAR}_${DATASET}_${LEVEL}_${TSCALE_LABEL}-anom-wrt-all_${GRID}.nc 
${COMP_VAR_PWI_FILE} : ${COMP_VAR_ANOM_RUNMEAN} ${DATE_LIST} 
	${PYTHON} ${DATA_SCRIPT_DIR}/calc_composite.py $< ${COMP_VAR} $@ --date_file $(word 2,$^) --region sh 

## Step 2: Calculate the contour composite (already done for composite envelope above)

## Step 3: Plot
COMP_VAR_PWI_PLOT=${COMP_DIR}/${COMP_VAR}-composite_zw_${METRIC}${METRIC_HIGH_THRESH}-${ENV_WAVE_LABEL}_env-${VAR}-${CONTOUR_VAR}_${DATASET}_${LEVEL}_${TSCALE_LABEL}-anom-wrt-all_${GRID}.png
${COMP_VAR_PWI_PLOT} : ${COMP_VAR_PWI_FILE} ${CONTOUR_ZONAL_ANOM_RUNMEAN_COMP}
	bash ${VIS_SCRIPT_DIR}/plot_composite.sh $(word 1,$^) ${COMP_VAR} $(word 2,$^) ${CONTOUR_VAR} $@ ${PYTHON} ${VIS_SCRIPT_DIR}


# Conventional variable composite, upper threshold of PWI + El Nino

## Step 1: Combine date lists

	${PYTHON} ${DATA_SCRIPT_DIR}/combine_dates.py $@ 


## Step 2: Calculate variable composite 

## Step 3: Calculate contour composite

## Step 4: Plot


# Conventional variable composite, lower threshold of PWI

## Step 1: Generate list of dates for use in composite creation
ANTI_DATE_LIST=${COMP_DIR}/dates_zw_${METRIC}${METRIC_LOW_THRESH}-${ENV_WAVE_LABEL}_env-${VAR}_${DATASET}_${LEVEL}_${TSCALE_LABEL}_${GRID}-${MER_METHOD}.txt 
${ANTI_DATE_LIST}: ${WAVE_STATS}
	${PYTHON} ${DATA_SCRIPT_DIR}/parse_wave_stats.py $< ${METRIC} --date_list $@ --metric_threshold ${METRIC_LOW_THRESH} --threshold_direction less

## Step 2: Get the composite variable mean
ANTICOMP_VAR_FILE=${COMP_DIR}/${COMP_VAR}-composite_zw_${METRIC}${METRIC_LOW_THRESH}-${ENV_WAVE_LABEL}_env-${VAR}_${DATASET}_${LEVEL}_${TSCALE_LABEL}-anom-wrt-all_${GRID}.nc 
${ANTICOMP_VAR_FILE} : ${COMP_VAR_ANOM_RUNMEAN} ${ANTI_DATE_LIST} 
	${PYTHON} ${DATA_SCRIPT_DIR}/calc_composite.py $< ${COMP_VAR} $@ --date_file $(word 2,$^) --region sh

## Step 3: Get the composite mean contour
CONTOUR_ZONAL_ANOM_RUNMEAN_ANTICOMP=${COMP_DIR}/${CONTOUR_VAR}-composite_zw_${METRIC}${METRIC_LOW_THRESH}-${ENV_WAVE_LABEL}_env-${VAR}_${DATASET}_${LEVEL}_${TSCALE_LABEL}_native-zonal-anom.nc 
${CONTOUR_ZONAL_ANOM_RUNMEAN_ANTICOMP} : ${CONTOUR_ZONAL_ANOM_RUNMEAN} ${ANTI_DATE_LIST} 
	${PYTHON} ${DATA_SCRIPT_DIR}/calc_composite.py $< ${CONTOUR_VAR} $@ --date_file $(word 2,$^) --region sh

## Step 4: Plot
ANTICOMP_VAR_PLOT=${COMP_DIR}/${COMP_VAR}-composite_zw_${METRIC}${METRIC_LOW_THRESH}-${ENV_WAVE_LABEL}_env-${VAR}-${CONTOUR_VAR}_${DATASET}_${LEVEL}_${TSCALE_LABEL}-anom-wrt-all_${GRID}.png
${ANTICOMP_VAR_PLOT} : ${ANTICOMP_VAR_FILE} ${CONTOUR_ZONAL_ANOM_RUNMEAN_ANTICOMP}
	bash ${VIS_SCRIPT_DIR}/plot_composite.sh $(word 1,$^) ${COMP_VAR} $(word 2,$^) ${CONTOUR_VAR} $@ ${PYTHON} ${VIS_SCRIPT_DIR}


# Reverse composite, upper threshold

## Step 1: Calculate composite
COMP_METRIC_90PCT_FILE=${COMP_DIR}/${METRIC}-composite_zw_${COMP_VAR}90pct-${ENV_WAVE_LABEL}_env-${VAR}_${DATASET}_${LEVEL}_${TSCALE_LABEL}-anom-wrt-all_${GRID}.nc
${COMP_METRIC_90PCT_FILE} : ${COMP_VAR_ANOM_RUNMEAN} ${WAVE_STATS}
	${PYTHON} ${DATA_SCRIPT_DIR}/calc_index_composite.py $(word 1,$^) ${COMP_VAR} $(word 2,$^) ${METRIC} 90pct $@ --region sh

## Step 2: Plot
COMP_METRIC_90PCT_PLOT=${COMP_DIR}/${METRIC}-composite_zw_${COMP_VAR}90pct-${ENV_WAVE_LABEL}_env-${VAR}_${DATASET}_${LEVEL}_${TSCALE_LABEL}-anom-wrt-all_${GRID}.png
${COMP_METRIC_90PCT_PLOT} : ${COMP_METRIC_90PCT_FILE}
	bash ${VIS_SCRIPT_DIR}/plot_index_composite.sh $< ${METRIC} 90pct $@ ${PYTHON} ${VIS_SCRIPT_DIR}


# Reverse composite, lower threshold

## Step 1: Calculate composite
COMP_METRIC_10PCT_FILE=${COMP_DIR}/${METRIC}-composite_zw_${COMP_VAR}10pct-${ENV_WAVE_LABEL}_env-${VAR}_${DATASET}_${LEVEL}_${TSCALE_LABEL}-anom-wrt-all_${GRID}.nc
${COMP_METRIC_10PCT_FILE} : ${COMP_VAR_ANOM_RUNMEAN} ${WAVE_STATS}
	${PYTHON} ${DATA_SCRIPT_DIR}/calc_index_composite.py $(word 1,$^) ${COMP_VAR} $(word 2,$^) ${METRIC} 10pct $@ --include below --region sh

## Step 2: Plot
COMP_METRIC_10PCT_PLOT=${COMP_DIR}/${METRIC}-composite_zw_${COMP_VAR}10pct-${ENV_WAVE_LABEL}_env-${VAR}_${DATASET}_${LEVEL}_${TSCALE_LABEL}-anom-wrt-all_${GRID}.png
${COMP_METRIC_10PCT_PLOT} : ${COMP_METRIC_10PCT_FILE}
	bash ${VIS_SCRIPT_DIR}/plot_index_composite.sh $< ${METRIC} 10pct $@ ${PYTHON} ${VIS_SCRIPT_DIR}


# Reverse composite, upper threshold (absolute value anomalies)

## Step 1: Calculate composite
COMP_METRIC_90PCTABS_FILE=${COMP_DIR}/${METRIC}-composite_zw_${COMP_VAR}90pctabs-${ENV_WAVE_LABEL}_env-${VAR}_${DATASET}_${LEVEL}_${TSCALE_LABEL}-anom-wrt-all_${GRID}.nc
${COMP_METRIC_90PCTABS_FILE} : ${COMP_VAR_ANOM_RUNMEAN} ${WAVE_STATS}
	${PYTHON} ${DATA_SCRIPT_DIR}/calc_index_composite.py $(word 1,$^) ${COMP_VAR} $(word 2,$^) ${METRIC} 10pct $@ --absolute --region sh

## Step 2: Plot
COMP_METRIC_90PCTABS_PLOT=${COMP_DIR}/${METRIC}-composite_zw_${COMP_VAR}90pctabs-${ENV_WAVE_LABEL}_env-${VAR}_${DATASET}_${LEVEL}_${TSCALE_LABEL}-anom-wrt-all_${GRID}.png
${COMP_METRIC_90PCTABS_PLOT} : ${COMP_METRIC_90PCTABS_FILE}
	bash ${VIS_SCRIPT_DIR}/plot_index_composite.sh $< ${METRIC} 90pctabs $@ ${PYTHON} ${VIS_SCRIPT_DIR}



