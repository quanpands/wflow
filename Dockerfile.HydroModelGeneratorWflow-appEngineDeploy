FROM ubuntu:18.04
# Add and install dependencies.
ADD requirements.txt requirements.txt
# Add application code.
ADD . app/

# Install PCRaster
RUN apt-get update && apt-get install -y python3.6 python3-pip \
    && pip3 install -r requirements.txt \
    && apt install -y cmake gcc g++ git qtbase5-dev libncurses5-dev libqwt-qt5-dev \
    libxerces-c-dev libboost-all-dev libgdal-dev python3-numpy python3-docopt wget \
    && wget http://pcraster.geo.uu.nl/pcraster/4.2.0/pcraster-4.2.0.tar.bz2 \
    && tar xf pcraster-4.2.0.tar.bz2 && cd pcraster-4.2.0 \
    && mkdir build && cd build \
    && cmake -DFERN_BUILD_ALGORITHM:BOOL=TRUE -DCMAKE_INSTALL_PREFIX:PATH=$HOME/pcraster \
    -DPYTHON_EXECUTABLE:FILEPATH=/usr/bin/python3 .. \
    && cmake --build . \
    && make install

# Install wflow
RUN apt-get install -y software-properties-common \
    && apt-add-repository ppa:ubuntugis/ubuntugis-unstable && apt-get update && apt-get install python3.6-gdal
# Install gdal
RUN apt-get update && apt-get install gdal-bin
# python3-gdal python3-numpy
RUN git clone 'https://github.com/openstreams/wflow' \
    && cd wflow && pip3 install -e .

# Install hydro-earth
RUN cd ../.. && git clone --recursive 'https://github.com/openearth/hydro-earth' \
    && cd hydro-earth && python3 setup.py install  && pip3 install -r requirements.txt && cd ..

# Install hydro-engine
RUN cd app/hydro_model_generator_wflow && git clone 'https://github.com/openearth/hydro-engine'

ENV DATASTORE_PROJECT_ID hydro-earth
# Need to copy over private file
ENV GOOGLE_APPLICATION_CREDENTIALS=/hydro-earth/hydroearth/config_privatekey.json
ENV PYTHONPATH $PYTHONPATH:$HOME/pcraster/python
ENV PATH $PATH:$HOME/pcraster/bin
ENV MODELTYPE wflow
ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8

WORKDIR app/hydro_model_generator_wflow/
