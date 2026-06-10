FROM anaconda/miniconda:latest

# install nginx and other dependencies
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
	curl \
	libcap2-bin \
	libmagic1 \
	nginx \
	supervisor \
	&& rm -rf /var/lib/apt/lists/*

# the image's root condarc ships tos-gated defaults; replace with conda-forge
RUN printf 'channels:\n  - conda-forge\n' > /opt/miniconda3/.condarc

# update packages of base conda install
# the packages in base conda install don't get used but are updated anyway to remove any CVEs
RUN conda update --all -y

# unprivileged runtime user; nginx binds :80 via capability instead of root
RUN useradd -m -u 1000 sds \
	&& setcap 'cap_net_bind_service=+ep' /usr/sbin/nginx \
	&& sed -i '/^user /d' /etc/nginx/nginx.conf \
	&& chown -R sds:sds /var/lib/nginx /var/log/nginx /run

WORKDIR /sds
RUN chown sds:sds /sds

# build the conda env before copying the app, so code changes don't
# invalidate this layer and force a full env rebuild
COPY env.yaml setup.sh /sds/
RUN chmod +x setup.sh && ./setup.sh

# copy application files (sds-owned: the app writes table.csv/table.json,
# app/static/last_updated.txt, and app/data/api_response.json at runtime)
COPY --chown=sds:sds . /sds/

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

# reconcile host-mount ownership (older deployments wrote as root), then drop
# root for good; chown may no-op on root-squashed NFS where nothing is
# root-owned anyway
CMD ["sh", "-c", "mkdir -p /sds/data/state/logs && { chown -R sds:sds /sds/data || true; } && exec env HOME=/home/sds USER=sds LOGNAME=sds setpriv --reuid sds --regid sds --init-groups /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf"]

