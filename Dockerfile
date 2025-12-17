FROM continuumio/miniconda3:latest

# install nginx and other dependencies
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
	libmagic1 \
	nginx \
	supervisor \
	&& rm -rf /var/lib/apt/lists/*

# update packages of base conda install
# the packages in base conda install don't get used but are updated anyway to remove any CVEs
RUN conda update --all -y

# accept channel anaconda tos
RUN conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
RUN conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r

# add conda-forge and remove unused channels
RUN conda config --file /root/.condarc --add channels conda-forge
RUN conda config --file /root/.condarc --remove channels defaults

# create directories
WORKDIR /sds
RUN mkdir -p /var/log/supervisor

# copy application files
COPY . /sds/

# setup application
RUN cd /sds && \
	chmod +x setup.sh && \
	./setup.sh

# copy nginx config
COPY nginx.conf /etc/nginx/sites-available/default

# copy supervisor configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# make entrypoint executable
RUN chmod +x /sds/entrypoint.sh

EXPOSE 80 443

# user supervisor to manage both nginx and sds
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]

