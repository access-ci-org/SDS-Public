FROM continuumio/miniconda3:latest

WORKDIR .

RUN mkdir /sds/

COPY . /sds/

RUN cd /sds && \
	chmod +x setup.sh && \
	./setup.sh

RUN chmod +x /sds/entrypoint.sh

EXPOSE 8080

ENTRYPOINT ["/sds/entrypoint.sh"]
