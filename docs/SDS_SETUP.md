
# SDS Setup

This page will go over, in detail, how to setup the SDS.
If you would like a simpler "quick start" guide, view the `README.md` file.

## Table of Contents

- [Setting up the Application](#setting-up-the-application)
  - [Running the Application](#running-the-application)
    - [Using Docker](#using-docker)
    - [Running Locally](#running-locally)
- [Data Preparation](#data-preparation)
  - [Curated](#curated)
  - [Raw Output](#raw-output)
    - [Collector Script](#collector-script)
    - [Manual](#manual)
  - [Parser](#parser)

## Setting up the Application

The SDS tool is meant to exist independent of any HPC clusters and should not be run on any critical systems.
The recommended method is to run the application inside of a VM and copy/add any important information to it.

1. Follow instructions to set [Config Variables](#config-variables)
2. Follow instructions in [Data Preparation](#data-preparation) to properly provide data for SDS

That should be all the necessary setup

## Running the Application

### Using Docker

1. Make sure [docker](https://docs.docker.com/engine/install/) is installed on your machine
2. Make sure you have the appropriate configs from [config-variables](#config-variables)
3. Download the image: `docker image pull public.ecr.aws/access-ci-org-public-containers/support/standalone-sds:latest`
4. Run `docker run -d -p 8080:80 --mount type=bind,source="./config.yaml",target="/sds/config.yaml" public.ecr.aws/access-ci-org-public-containers/support/standalone-sds:latest`
    - The website will be available in 5 or so seconds at `localhost:8080` (and <your_ip_address>:8080)
    - You can stop the services by running `sudo docker stop sds`
    - You can enter your container by running `sudo docker exec -it sds /bin/bash`

#### Adding Data

To add software data to the SDS, place your input files in a `./data/` directory next to your `config.yaml`. The container expects exactly one data mount at `/sds/data`. SDS reads user inputs from there and writes its own state under `./data/state/`.

First make sure you have the data in the form specified in the [Data Preparation](#data-preparation) section.

To mount:

- Stop and remove the existing container: `docker stop sds && docker rm sds`
- Re-run with `-v ./data:/sds/data` added:

```bash
sudo docker run --name sds -d -p 8080:80 \
  --mount type=bind,source="./config.yaml",target="/sds/config.yaml" \
  -v ./data:/sds/data \
  public.ecr.aws/access-ci-org-public-containers/support/standalone-sds:latest
```

To update the data just change files in `./data/` on the host — no need to touch the container. You only need to stop and re-run the container if you change `config.yaml` or want to add a new mount.

**Upgrading from the multi-mount layout?** If your existing deployment mounts `software.csv`, `container_data/`, etc. separately, run `bash migrate_data_layout.sh` from your repo root on the host. It moves your existing files into `./data/`, refuses to clobber anything, and prints the new run command. After that, update your compose file (or docker run) to use the single `-v ./data:/sds/data` mount.

#### File ownership

The container runs as an unprivileged user (UID 1000) and takes ownership of `./data` at startup, so everything SDS writes is owned by UID 1000 rather than root — no sudo needed to read or back up your data. Two host-specific notes:

- SELinux-enforcing hosts (RHEL/Rocky/Alma): add `:z` to the data volume (e.g. `-v ./data:/sds/data:z`) so the mount is labeled for container access.
- NFS-backed `./data` with `root_squash`: the startup ownership fixup is skipped; make sure the export allows UID 1000 to write.

#### Monitoring and Logs

All SDS logs are written to `/sds/data/state/logs/` inside the container, which appears on your host at `./data/state/logs/`. Files:

- `sds.log` — structured SDS application logs (rotates monthly)
- `api/api-requests.log` — one line per authenticated REST API request (timestamp, key prefix, key label, endpoint); rotates weekly, rotated files are kept indefinitely
- `sds-stdout.log` — raw stdout/stderr from the SDS process (startup output, crashes, anything that didn't go through the application logger)
- `nginx-access.log` / `nginx-error.log` — nginx request and error logs
- `nginx.log` — nginx process stdout captured by supervisord (usually empty)
- `supervisord.log` — process manager log; usually only interesting if services are failing to start

#### SSL Certificates

If you want to enable ssl certificates for your website, make the following changes:

First, make sure you have the SSL certificate and key stored in an appropriate location (a `./ssl` directory is fine)

The container runs all of its processes as an unprivileged user (UID 1000),
so the mounted certificate and key must be readable by UID 1000 — otherwise
nginx refuses to start and the container exits at boot with the permission
error (and the fix) in its logs. On the host (the commands below use `./ssl`
as a placeholder — substitute wherever your certificate and key actually
live):

```bash
chown -R 1000:1000 ./ssl
chmod 400 ./ssl/key.pem
```

Second, create `nginx.conf` file locally with the appropriate settings:

```bash
cat << 'EOF' > nginx.conf
error_log /sds/data/state/logs/nginx-error.log warn;

server {
    listen 443 ssl;
    server_name localhost;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # MCP endpoint; the upstream validates Host, so forward the proxy host
    location /mcp {
        proxy_pass http://127.0.0.1:9000;
        proxy_http_version 1.1;
        proxy_set_header Host $proxy_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_buffering off;
        proxy_read_timeout 3600s;
        proxy_set_header Connection "";
    }

    access_log /sds/data/state/logs/nginx-access.log;

    client_max_body_size 100M;
}
EOF
```

Third, stop and re-run the container with the following changes:

- Add the appropriate ports (change `-p 8080:80` to `-p 443:443`)
- Mount the new config to the container (`--mount type=bind,source="./nginx.conf",target="/etc/nginx/sites-available/default"`)

Here is an example command.

```bash
# stop and remove the container
docker stop sds && docker rm sds

# rerun the container with the appropriate port and mounts
# assumes ssl certs are in the ./ssl directory
docker run -d -p 443:443 --mount type=bind,source="./config.yaml",target="/sds/config.yaml" --mount type=bind,source="./nginx.conf",target="/etc/nginx/sites-available/default" -v ./ssl:/etc/nginx/ssl public.ecr.aws/access-ci-org-public-containers/support/standalone-sds:latest
```

#### Analytics and Website Titles

Both of these live under `./data/state/` and survive container replacement:

- `./data/state/websites/` — cached url:website_title mappings. Persisting this saves the time spent re-fetching titles when the container starts.
- `./data/state/analytics/` — recorded website analytics (visible after login in the Analytics tab). Persisting this means analytics history isn't lost when the container is replaced.

### Running Locally

1. Clone the repo into your local machine: `git clone https://github.com/access-ci-org/SDS-Public/tree/stand-alone.git`
2. Run `source setup.sh` to setup your environment
3. Run `python reset_database.py` to create and load your database
   - You can pass in three different arguments to `reset_database.py`. Type `python reset_database.py -h` for more info. Read the entire help message before continuing.

4. To exclude some softwares from being displayed on the website, add them to the `software_blacklist.txt` file in the project directory. A basic list of blacklisted names is already provided

5. Run the application with `flask run`
   - If you want to run the application with a watcher (which will automatically update the db and app when the data is updated). Run `python run.py` see `python run.py --help` for more information

## Config Variables

- Create a `config.yaml` file in the project folder.
- If you would like to use the SDS api to obtain and display more information about your software then request and api key from Sandesh (<sla302@uky.edu>).
- Inside the `config.yaml` file, add the following:

```yaml
api:
  use_api: False
  api_key: "your api key here"
  use_curated_info: False
  use_ai_info: False
styles:
  primary_color: ""
  secondary_color: ""
  site_title: "Title for website here"
  logo: ""
general:
  user_name: user
  password: password
  share_with_devs: True
```

To use a custom logo, place the image in your `./data/` directory and set `logo: "data/your_logo.svg"` — it reaches the container through the existing data mount, so no extra mount is needed.

*View the `CONFIGS.md` file for information on what these configs do and other available configs.*

## Data Preparation

The SDS tool requires the names of the software available on each system. You can provide this information in two different ways: curated and/or raw output.

### Curated

How it works: you provide sds the data it needs in the specific format it needs them

- Curated data should be in the form of a CSV with the following requirements
  - If you are using docker, then the file must be named `software.csv`
  - The first line must have column names and the following columns are necessary
 (only the software column needs any data): software, resource, software_description, software_versions.
  - `resource` in this case refers to a specific cluster
  - Here is an example of a CSV file:

```csv
software,software_description,software_versions,resource
ACTC,ACTC converts independent triangles into triangle strips or fans.,1.1,cluster1
ACTC,ACTC converts independent triangles into triangle strips or fans., 1.3,cluster1
ANTLR,,"2.7.7-Java-11,2.6",cluster2
```

A `software.csv`file with just the columns is already provided.

### Raw Output

How it works: you provide sds with the output of a few commands, the sds will automatically extract and format that data.

#### Collector Script

For obtaining the raw output, use the `collector.py` script located in this repo.
The `COLLECTOR.md` file goes over how to use it. The `collector.py` file will create the proper directory structure for each type of data.

#### Manual

If you would rather collect the data manually, the rest of the section will cover how to structure that data.

The raw output of a specific command or supported file types (SDS will parse it and extract the software info)
All files for this section must be within subdirectories. The name of each subdirectory
should be the name of a resource to which the files belong. `resource` refers to a specific cluster.

- `module spider` output (lmod)
  - If you use lmod for managing packages/environments then run `module spider` on your
 system and save the output to a text file
  - If you are using docker to run the SDS, then the parent directory must be named `spider_data`

- Container definition (`.def`) file
  - You can also provide container definition files within the proper resource directory
 and the SDS tool will attempt to parse it and extract any relevant software information.
 The name of the `.def` is treated as the container name.
  - Aside from the raw `.def` file, you can also add curated information for specific containers in a csv file or in a custom SDS comment block (see the `PARSER.md` file).
 All csv files must have a software_name and (container_file or definition_file) columns.
 Here is the complete list of supported columns: `software_name, software_versions, container_name,
 definition_file, container_file, notes, command`.
    - If no container_name is provided then the definition_file name will be used as container name.
     The csv file is meant to supplement the `.def` files so that you can provide data the parser may have missed,
     or provide extra information for specific containers (such as `notes` on how to run them)
  - You can also provide only the `.csv` file, `.def` files or both. Information will only be added to and not overwritten.
  - Here is an example `.csv` file or a container:

```csv
  software_name,software_versions,container_name,definition_file,container_file,container_description,notes,command
  adapterremoval,2.3.2,,/share/singularity/adapterremoval.def,/share/singularity/adapterremoval.sinf,singularity run --app adapterremoval232 /share/singularity/share/singularity/afterqc.sinf AdapterRemoval
  afterqc,0.9.7,,/share/singularity/afterqc,/share/singularity/afterqc.sinf,singularity run --app afterqc097 /share/singularity/share/singularity/afterqc.sinf python /usr/local/Miniconda3/envs/afterqc-0.9.7/bin/after.py -1 R1.fq.gz
```

- Custom defined example use
  - You can define custom example usage for each of your software. This is a good
    location to add any recommend slurm scripts or other instructions on how you want users to use
    your software.
  - Place the directory at `./data/software_uses/`.
  - All files within the `software_uses` directory should be the name of a software. If a software
    matching the provided file isn't found then the data is ignored. So if you have some example use
    for the software `python` your file with that information must be named `python` or `python.md`
  - All files are treated and formatted as Markdown files when being displayed on the website,
    regardless of whether it has the `.md` suffix.

Here is an example of a proper directory structure for the data:

```
SDS
  └── data/
       ├── container_data/
       |    └── {resource_name}/
       |         ├── {resource_name}.csv    # CSV file with container metadata
       |         └── {preserved_directory_structure}/
       |             └── {definition_files}  # Original definition files with paths preserved
       |
       ├── spider_data/
       |    └── {resource_name}/
       |        └── {resource_name}_spider  # Complete output from module spider
       |
       ├── software.csv
       |
       ├── software_uses/
       |    └── {software_name}.md
       |
       └── state/    # SDS-written: db, analytics, logs, cached website titles
```

*Note for container files: If you are defining your container file/definition file location by using the  SDS comment block (see PARSER.md file), you do not need to have a preserved directory structure. So your container_data directory structure would be like this,`container_data/{resource_name}/{definition_files}`*

## Parser

The built in parser will attempt to gather software information based on the data provided, but it may not always be successful depending on your naming scheme.
You can define how the built in parser parses your information. View the **`PARSER.md`** file for more details on standard formats and how to modify the parsers.
