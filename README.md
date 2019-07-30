# MODELTYPE = wflow

Development

```
docker build -t wflow:base -f Dockerfile.AppEngineDeployBase .

docker build -t eu.gcr.io/hydro-earth/wflow-worker:test -f Dockerfile.AppEngineDeployFromBase .

docker run -it eu.gcr.io/hydro-earth/wflow-worker:test
docker run -it eu.gcr.io/hydro-earth/wflow-worker:test bash
```

Run [wflow-master@0870392](https://github.com/openstreams/wflow/commit/08703927039cd238602080b1e5edb4f746d66e75)

```
python model_generator_runner.py
```

```
docker pull eu.gcr.io/hydro-earth/wflow-worker

psqworker hydroearth.tasks.worker.models_queue 
```

## [clean docker](http://queirozf.com/entries/docker-examples-cleaning-up-unused-resources)

```
docker system prune

docker rm -vf $(docker ps -aq)

docker rmi $(docker images -qf dangling=true)

docker volume rm $(docker volume ls -qf dangling=true)
docker volume prune -f
```

# Google [Cloud](https://cloud.google.com/gcp/getting-started/#quick-starts)

## gcloud auth configure-docker

## gcloud auth login

## [deploy to Google App Engine](https://github.com/openearth/hydro-earth/wiki/Worker-Deployment-Instructions)

[App Engine](https://cloud.google.com/appengine/docs/)

Google Cloud SDK Shell

service: hydro-model-generator-wflow

```
gcloud container images list-tags eu.gcr.io/hydro-earth/wflow-worker

docker push eu.gcr.io/hydro-earth/wflow-worker:test
```

## Change the docker image tag from "test" to "latest" in Google Cloud Platform

require: app.yaml

```
cd hydro-model-generator-wflow-app-engine-deploy/

gcloud app deploy --image-url eu.gcr.io/hydro-earth/wflow-worker --project hydro-earth

gcloud app logs tail -s hydro-model-generator-wflow --project=hydro-earth
```

# Docker wflow:test, 20190729

## Change [tasks.py](https://github.com/openearth/hydro-earth/blob/master/hydroearth/tasks/tasks.py)

```
vim /usr/local/lib/python3.6/dist-packages/hydroearth-0.1.0-py3.6.egg/hydroearth/tasks/tasks.py

import subprocess

def build_model_cmd(model)

        cmd = ["python", "model_generator_runner.py"]
        cp = subprocess.run(cmd, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print('Building status {}, {}'.format(cp.returncode, cp.stderr))

    # filename = 'app-worker-run.cmd'
```

## Change [model_generator_runner.py](https://github.com/openearth/hydro-model-generator-wflow/blob/app-engine-deploy/hydro_model_generator_wflow/model_generator_runner.py)

```
vim /app/hydro_model_generator_wflow/model_generator_runner.py

Line 2:
import shutil

Line 42:
            ds["crs"] = "EPSG:{}".format(utm_epsg(region))

Line 65:
        print("=> general_options.hydro-engine.datasets.variable:", ds["variable"])

Line 81:
    if os.path.exists(output_dir):
        os.remove(output_dir)
    else:
        print("Can not delete {}".format(output_dir))

Line 90:
def delete_output_files(input_dir):
    shutil.rmtree(input_dir)
    
    origfolder = "hydro-engine/"
    for item in os.listdir(origfolder):
        if item.endswith(".tif"):
            os.remove(os.path.join(origfolder, item))
        if item.endswith(".tfw"):
            os.remove(os.path.join(origfolder, item))
    # pass
```

## Change [hydro_model_generator_wflow.py](https://github.com/openearth/hydro-model-generator-wflow/blob/app-engine-deploy/hydro_model_generator_wflow/hydro_model_generator_wflow.py)

```
vim /app/hydro_model_generator_wflow/hydro_model_generator_wflow.py

Line 111:
    ensure_dir_exists(case_template)
```

## Add [wflow_sbm_template](https://github.com/openearth/hydro-model-generator-wflow/blob/app-engine-deploy/hydro_model_generator_wflow/hydro_model_generator_wflow.py#L146)

```
# create static maps
dir_dest = os.path.join(case, "staticmaps")
# use custom inifile, default high res ldd takes too long
path_inifile = os.path.join(case, "data/staticmaps.ini")

```

## Change [static_maps.py](https://github.com/openearth/hydro-model-generator-wflow/blob/app-engine-deploy/hydro_model_generator_wflow/static_maps.py#L502)

```
vim /app/hydro_model_generator_wflow/static_maps.py

Line 495:
            lai_in = os.path.join(lai, "LAI00000.{:03d}.tif".format(month + 1))
            lai_out = os.path.join(dest_lai, "LAI00000.{:03d}.tif".format(month + 1))
```

## Change [wflow_example.yaml](https://github.com/openearth/hydro-model-generator-wflow/blob/app-engine-deploy/hydro_model_generator_wflow/wflow_example.yaml)

```
vim /app/hydro_model_generator_wflow/wflow_example.yaml

        -
            function: get-rivers
            variable: river
            source: earth-engine # earth-engine|local
            # the path can be either a file path for a local source,
            # or the id of a dataset on the hydro-engine
            path: hydro-engine/river.geojson
            crs: UTM
            cell_size: 1000.0
            region_filter: catchments-upstream
            catchment_level: 6
```

## Check hydroengine/[__init__.py](https://github.com/openearth/hydro-engine/blob/master/hydroengine/__init__.py)

```
vim /app/hydro_model_generator_wflow/hydro-engine/hydroengine/__init__.py


```

## 

```
```

# Netlify hydroengine_service

## Check hydroengine_service/[main.py](https://github.com/openearth/hydro-engine-service/blob/master/hydroengine_service/main.py)

```python
# HydroBASINS level 5
basins = {
    5: ee.FeatureCollection('users/gena/HydroEngine/hybas_lev05_v1c'),
    6: ee.FeatureCollection('users/gena/HydroEngine/hybas_lev06_v1c'),
    7: ee.FeatureCollection('users/gena/HydroEngine/hybas_lev07_v1c'),
    8: ee.FeatureCollection('users/gena/HydroEngine/hybas_lev08_v1c'),
    9: ee.FeatureCollection('users/gena/HydroEngine/hybas_lev09_v1c'),
}

# HydroSHEDS rivers, 15s
rivers = ee.FeatureCollection('users/gena/HydroEngine/riv_15s_lev06')

# HydroLAKES
lakes = ee.FeatureCollection('users/gena/HydroLAKES_polys_v10')

# available datasets for bathymetry
bathymetry = {
    'jetski': ee.ImageCollection('users/gena/eo-bathymetry/sandengine_jetski'),
    'vaklodingen': ee.ImageCollection('users/gena/vaklodingen'),
    'kustlidar': ee.ImageCollection('users/gena/eo-bathymetry/rws_lidar')
}

# graph index
index = ee.FeatureCollection('users/gena/HydroEngine/hybas_lev06_v1c_index')

monthly_water = ee.ImageCollection('JRC/GSW1_0/MonthlyHistory')
```

```python
@app.route('/get_raster', methods=['GET', 'POST'])

    raster_assets = {
        'dem': 'USGS/SRTMGL1_003',
        'hand': 'users/gena/global-hand/hand-100',
        'FirstZoneCapacity': 'users/gena/HydroEngine/static/FirstZoneCapacity',
        'FirstZoneKsatVer': 'users/gena/HydroEngine/static/FirstZoneKsatVer',
        'FirstZoneMinCapacity': 'users/gena/HydroEngine/static/FirstZoneMinCapacity',
        'InfiltCapSoil': 'users/gena/HydroEngine/static/InfiltCapSoil',
        'M': 'users/gena/HydroEngine/static/M',
        'PathFrac': 'users/gena/HydroEngine/static/PathFrac',
        'WaterFrac': 'users/gena/HydroEngine/static/WaterFrac',
        'thetaS': 'users/gena/HydroEngine/static/thetaS',
        'soil_type': 'users/gena/HydroEngine/static/wflow_soil',
        'landuse': 'users/gena/HydroEngine/static/wflow_landuse',
        'LAI01': 'users/gena/HydroEngine/static/LAI/LAI00000-001',
        'LAI02': 'users/gena/HydroEngine/static/LAI/LAI00000-002',
        'LAI03': 'users/gena/HydroEngine/static/LAI/LAI00000-003',
        'LAI04': 'users/gena/HydroEngine/static/LAI/LAI00000-004',
        'LAI05': 'users/gena/HydroEngine/static/LAI/LAI00000-005',
        'LAI06': 'users/gena/HydroEngine/static/LAI/LAI00000-006',
        'LAI07': 'users/gena/HydroEngine/static/LAI/LAI00000-007',
        'LAI08': 'users/gena/HydroEngine/static/LAI/LAI00000-008',
        'LAI09': 'users/gena/HydroEngine/static/LAI/LAI00000-009',
        'LAI10': 'users/gena/HydroEngine/static/LAI/LAI00000-010',
        'LAI11': 'users/gena/HydroEngine/static/LAI/LAI00000-011',
        'LAI12': 'users/gena/HydroEngine/static/LAI/LAI00000-012',
        'thickness-NASA': 'users/huite/GlobalThicknessNASA/average_soil_and_sedimentary-deposit_thickness',
        'thickness-SoilGrids': 'users/huite/SoilGrids/AbsoluteDepthToBedrock__cm',
    }

```


