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

# unprivileged runtime user; nginx binds :80 via capability instead of root.
# /var/log/supervisor stays writable so operator nginx configs that predate
# the single-data-mount layout (and still log there) don't kill nginx
RUN useradd -m -u 1000 sds \
	&& setcap 'cap_net_bind_service=+ep' /usr/sbin/nginx \
	&& sed -i '/^user /d' /etc/nginx/nginx.conf \
	&& chown -R sds:sds /var/lib/nginx /var/log/nginx /var/log/supervisor /run

WORKDIR /sds
RUN chown sds:sds /sds

# build the conda env before copying the app, so code changes don't
# invalidate this layer and force a full env rebuild
COPY env.yaml setup.sh /sds/
RUN chmod +x setup.sh && ./setup.sh

# copy application files (sds-owned: the app writes table.csv/table.json,
# app/static/last_updated.txt, and app/data/api_response.json at runtime)
COPY --chown=sds:sds . /sds/

# install the self-contained MCP server into the env. pyproject already
# declares `mcp>=1.0.0` (env.yaml omits it), so this pulls the SDK and exposes
# the `sds-mcp` console script that supervisord launches.
RUN /sds/env/SDS_ENV/bin/python -m pip install -e /sds/mcp

# copy nginx config
COPY nginx.conf /etc/nginx/sites-available/default

# copy supervisor configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# make the boot and app-launcher scripts executable
RUN chmod +x /sds/boot.sh /sds/entrypoint.sh

ENV SDS_DATA_DIR=/sds/data

EXPOSE 80 443

# probe through nginx so one check covers the proxy chain and Flask. SSL-only
# deployments have no :80 listener, so fall back to the 443 vhost (-k: the
# cert names the site, never 127.0.0.1); generous start period absorbs
# first-boot data ingestion
HEALTHCHECK --interval=10s --timeout=5s --start-period=120s --retries=3 \
	CMD curl -fsS http://127.0.0.1:80/ || curl -fsSk https://127.0.0.1:443/ || exit 1

# root boot window: mount-ownership fixup and nginx preflight, then drops to
# the sds user for good (see boot.sh)
CMD ["/sds/boot.sh"]

