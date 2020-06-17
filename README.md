# Sentinel-3 RGB composites

## Conda environment

Dependencies:

- snap
- ipykernel
- otb
- gdal>2.2.2
- poppler<0.66
- pystac

Create the conda environment with:

```bash
conda env create -f environment.yml 
```

## Run on Binder

Click the badge below to test it on Binder

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gl/terradue-ogctb16%2Feoap%2Fd169-jupyter-nb%2Feo-processing-sentinel-3-olci-composite-stac/master?urlpath=lab)

Note: you have to stage the EO data. Binder available RAM may be a limitation to run the SNAP step

## Stage the EO data

Use `instac` to stage the EO data.

```bash
conda install instac
```

then 

```bash
stage-in -c stage-in.yml -t /workspace/data/s3
```

## Build

Use https://build.terradue.com/job/t2pc/job/pipeline-repo2nbdocker/

