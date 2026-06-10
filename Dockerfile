FROM anaconda/miniconda:latest

# install nginx and other dependencies
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
	curl \
	libmagic1 \
	nginx \
	supervisor \
	&& rm -rf /var/lib/apt/lists/*

# the image's root condarc ships tos-gated defaults; replace with conda-forge
RUN printf 'channels:\n  - conda-forge\n' > /opt/miniconda3/.condarc

# update packages of base conda install
# the packages in base conda install don't get used but are updated anyway to remove any CVEs
RUN conda update --all -y

# create supervisor log directory
WORKDIR /sds
RUN mkdir -p /var/log/supervisor

# build the conda env before copying the app, so code changes don't
# invalidate this layer and force a full env rebuild
COPY env.yaml setup.sh /sds/
RUN chmod +x setup.sh && ./setup.sh

# copy application files
COPY . /sds/

# copy nginx config
COPY nginx.conf /etc/nginx/sites-available/default

# copy supervisor configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# make entrypoint executable
RUN chmod +x /sds/entrypoint.sh

ENV SDS_DATA_DIR=/sds/data

EXPOSE 80 443

# probe through nginx so one check covers the proxy chain and Flask;
# generous start period absorbs first-boot data ingestion
HEALTHCHECK --interval=10s --timeout=5s --start-period=120s --retries=3 \
	CMD curl -fsS http://127.0.0.1:80/ || exit 1

# use supervisord to manage both nginx and sds
CMD ["sh", "-c", "mkdir -p /sds/data/state/logs && exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf"]

