FROM ubuntu:18.04
# Add and install dependencies.
ADD requirements.txt requirements.txt

RUN apt-get update --fix-missing && apt install -yq python3-minimal python3-pip\
    && pip3 install --upgrade pip \
    && pip install -r requirements.txt \
    && apt install -y cmake gcc g++ git libboost-all-dev libgdal-dev libncurses5-dev \
    libpython2.7-dev libpython3.6-dev libpython-dev libqwt-qt5-dev libxerces-c-dev \
    libxml2 libxml2-utils libxslt1-dev python-numpy qtbase5-dev python-docopt wget \
    && wget http://pcraster.geo.uu.nl/pcraster/4.2.0/pcraster-4.2.0.tar.bz2 \
    && tar xf pcraster-4.2.0.tar.bz2 && cd pcraster-4.2.0 \
    && mkdir build && cd build \
    && cmake -DFERN_BUILD_ALGORITHM:BOOL=TRUE -DCMAKE_INSTALL_PREFIX:PATH=$HOME/pcraster .. \
    && cmake --build . \
    && make install
# Install wflow
RUN git clone --recursive 'https://github.com/openstreams/wflow' \
    && cd wflow/wflow-py && apt-get install -y python-setuptools && python setup.py install
ENV PYTHONPATH "${PYTONPATH}:$HOME/pcraster/python"
ENV PATH "${PATH}:$HOME/pcraster/bin"
RUN export PYTHONPATH && export PATH
RUN pip install psq

# # Add application code.
# ADD . app/
# WORKDIR app/hydro_model_generator_wflow/
# 
# EXPOSE 8080
# CMD gunicorn -b :$PORT hydro_model_generator_wflow:app
