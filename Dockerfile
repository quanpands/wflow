FROM ubuntu:18.04
RUN apt-get update --fix-missing

WORKDIR /opt
ADD requirements.txt requirements.txt

RUN apt install -yq python3-minimal python3-pip \
    && pip3 install --upgrade pip \
    && pip install -r requirements.txt

# GDAL https://launchpad.net/ubuntu/+source/gdal/2.2.3+dfsg-2
RUN apt install -y wget cmake gcc g++ git qtbase5-dev \
       libboost-all-dev libncurses5-dev libxml2 libxml2-utils libxslt1-dev libxerces-c-dev libqwt-qt5-dev \
       libpython3.6-dev libpython-dev \
       gdal-bin gdal-data libgdal-dev libgdal20 \
       python3-numpy python3-docopt python3-setuptools python3-gdal
#       libpython2.7-dev \

COPY . /opt/wflow/
WORKDIR /opt/wflow/pcraster/pcraster-4.2.0/pcraster-4.2.0
# RUN wget http://pcraster.geo.uu.nl/pcraster/4.2.0/pcraster-4.2.0.tar.bz2 \
#     && tar xf pcraster-4.2.0.tar.bz2 && cd pcraster-4.2.0 \
RUN mkdir build && cd build \
    && cmake -DFERN_BUILD_ALGORITHM:BOOL=TRUE -DCMAKE_INSTALL_PREFIX:PATH=/usr/local/pcraster -DPYTHON_EXECUTABLE:FILEPATH=/usr/bin/python3 .. \
    && cmake --build . \
    && cpack
#     && make install
# RUN python3 --version \
#     && pip3 --version \
#     && pip --version \
#     && gdalinfo --version


# # Install wflow, Org
# RUN git clone --recursive 'https://github.com/openstreams/wflow' \
#     && cd wflow/wflow-py && apt-get install -y python-setuptools && python setup.py install

# # Install wflow, Error
# RUN git clone --recursive 'https://github.com/openstreams/wflow' \
#     && cd wflow \
#     && apt-get install -y python-setuptools \
#     && python setup.py install
# >>
#   Traceback (most recent call last):
#   File "setup.py", line 15, in <module>
#   with open(os.path.join(here, "README.rst"), encoding="utf-8") as f:
#   TypeError
#   :
#   'encoding' is an invalid keyword argument for this function

# Install wflow, Success
WORKDIR /opt/wflow/wflow
RUN export CPLUS_INCLUDE_PATH=/usr/include/gdal \
    && export C_INCLUDE_PATH=/usr/include/gdal \
    && python3 setup.py install

# Set pcraster environment
ENV PYTHONPATH "${PYTONPATH}:/usr/local/pcraster/python" 
ENV PATH "${PATH}:/usr/local/pcraster/bin"
# RUN export PYTHONPATH && export PATH
RUN pip3 install psq

# # Add application code.
# ADD . app/
# WORKDIR app/hydro_model_generator_wflow/
# 
# EXPOSE 8080
# CMD gunicorn -b :$PORT hydro_model_generator_wflow:app
