FROM terradue/l1-binder:3.0

MAINTAINER Terradue S.r.l

USER ${NB_USER}

COPY --chown=${NB_USER}:${NB_GID} . ${HOME}

RUN /opt/anaconda/bin/conda env create --file ${HOME}/environment.yml && /opt/anaconda/bin/conda clean -a -y

RUN /opt/anaconda/envs/env_s3/bin/python -m ipykernel install --name kernel_s3

ENV PREFIX /opt/anaconda/envs/env_s3

RUN test -f ${HOME}/postBuild && chmod +x ${HOME}/postBuild && ${HOME}/postBuild || exit 0

WORKDIR ${HOME}
