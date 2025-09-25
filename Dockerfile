FROM continuumio/miniconda3:latest

# install nginx and other dependencies
RUN apt-get update && apt-get install -y \
	libmagic1 \
	nginx \
	supervisor \
	&& rm -rf /var/lib/apt/lists/*

# create directories
WORKDIR /sds
RUN mkdir -p /var/log/supervisor

# copy application files
COPY . /sds/

# setup aplication
RUN cd /sds && \
	chmod +x setup.sh && \
	./setup.sh

# copy nginx config
COPY nginx.conf /etc/nginx/sites-available/default
# Remove default nginx config and create symlink
RUN rm -f /etc/nginx/sites-enabled/default && \
    ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/

# copy supervisor configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# make entrypoint executable
RUN chmod +x /sds/entrypoint.sh

EXPOSE 80 443

# user supervisor to manage both nginx and sds
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]

