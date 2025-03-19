FROM continuumio/miniconda3:latest

WORKDIR .

RUN mkdir /sds/

RUN apt-get update && apt-get install -y libmagic1

COPY . /sds/

RUN cd /sds && \
	chmod +x setup.sh && \
	./setup.sh

RUN chmod +x /sds/entrypoint.sh

EXPOSE 8080

ENTRYPOINT ["/sds/entrypoint.sh"]
