# HPC Software Documentation Service

# What is the SDS
The Software Documentation Service (SDS) is a tool designed to display the software available on different HPC systems.

For HPC end users it is a way to easily determine which software are available on which clusters as well as any relevant
documentation, software type classification, example use, descriptions, etc.

For HPC admins, it is an easy way to provide documentation for software on their systems.
All they need to do is provide the names of the software and which cluster they are available on and the SDS tool will provide the rest.

# Table of Contents
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

# Setting up the Application
**Bash or Zsh terminals are recommended**\
**Windows machine: Install Miniconda or Anaconda manually**

The SDS tool is meant to exist independent of any HPC clusters and should not be run on any critical systems.
The recommended method is to run the application inside of a VM and copy/add any important information to it.

1. Clone the repo into your local machine: `git clone -b stand-alone --single-branch https://github.com/access-ci-org/SDS-Public/tree/stand-alone.git`
2. Follow instructions to set [Config Variables](#config-variables)
3. Follow instructions in [Data Preparation](#data-preparation) to properly provide data for SDS

That should be all the necessary setup

## Running the Application
### Using Docker
1. Make sure [docker](https://docs.docker.com/engine/install/) is installed on your machine
2. Make sure you have the relevant data available based on [Data Preparation](#data-prepration)
3. Run `sudo docker-compose up -d`
    - The website will be available in 5 or so seconds at `localhost:8080` (and <your_ip_address>:8080)
    - You can stop the services by running `sudo docker-compose down`
    - To rebuild the image each time run: `sudo docker-compose up -d --build`
4. If you want to enable ssl certificates for your website, make the following changes:
    - In the `nginx.conf` file, comment out the entrie first `server {` entry and uncomment the entire second `server {` entry.
    - In the `docker-compose.yml` file, comment out the ` - "808:80"` line and uncomment the ` - "443:443"`
    - In the `docker-compose.yml` uncomment the `# - ./ssl:/etc/nginx/ssl`
      - This expects the ssl certificates to be in the project directory. If your ssl certificates are somehwere else,
        change the `./ssl` portion to be the path to the directory where the certificates are stored.

### Running Locally
1. Run `source setup.sh` to setup your environment
2. Run `python reset_database.py` to create and load your database
 - You can pass in three different arguments to `reset_database.py`. Type `python reset_database.py -h` for more info. Read the entire help message before continuing.
3. To exclude some softwares from being displayed on the website, add them to the `software_blacklist.txt` file in the project directory. A basic list of blacklisted names is already provided
4. Run the application with `flask run`

# Config Variables
- Create a `config.yaml` file in the project folder.
- If you would like to use the SDS api to obtain and display more information about your software then request and api key from Sandesh (sla302@uky.edu).
- Inside the `config.yaml` file, add the following:
```
api:
  use_api: False
  api_key: "your api key here"
  use_curated_info: False
  use_ai_info: False
styles:
  primary_color: "your primary color here"
  secondary_color: "your secondary color"
  site_title: "Title for website here"
  logo: "logo file name"
general:
  user_name: default admin user
  password: default admin password
  share_software: False
  show_container_page: True
```

- Set `use_api` to `True` to connect to a remote SDS database (using the `sds_api_key`). Default: False
- `api_key` API key to the sds website, you can obtain one here: (link to website or email of people to contact)
- Set `use_curated_info` to `True` to display curated information (such as software descriptions, link to software webpage, etc). If no software descriptions are provided and `use_curated_info` is set to true then it will use informaton from the api call to add descriptions. Default: False
- Set `use_ai_info` to `True` to display AI generated information (such as AI descriptions, Software example use, etc.) on your website. Default: False
- Set `primary_color` and `secondary_color` to set the colors (in hexadecimal, e.g. #1B365D) for the website. Different shades of these two colors are used in the website. Darker, monochromatic, colors are recommended. Default Primary: #1b365d, Default Secondary: #324a6d
- Set `site_title` to be the main title you want for your website. Default: SDS
- Set `logo` to be the relative path to the image you want to display as your logo.
- Set `user_name` and `password` to be the default admin user for your website
- Set `share_software` to be `True` if you want to share the names of the software available on your resources with us. This inforamtion will be used to identify software for which we need to collect curated data. It may also be used to help other institutions identify what software is available at different institutions. Default is `False`.
- Set `show_container_page` to be `False` if you either don't want the container page to be accessible. Default is `True`


# Data Preparation
The SDS tool requires the names of the software available on each system. You can provide this information in two different ways: curated and/or raw output.

### Curated
- Curated data should be in the form of a CSV with the following requirements
  - If you are using docker, then the file must be named `software.csv`
  - The first line must have column names and the following columns are necessary
 (only the software column needs any data): software, resource, software_description, software_versions.
  - `resource` in this case refers to a specific cluster
  - Here is an example of a CSV file:
```
software,software_description,software_versions,resource
ACTC,ACTC converts independent triangles into triangle strips or fans.,1.1,cluster1
ACTC,ACTC converts independent triangles into triangle strips or fans., 1.3,cluster1
ANTLR,,"2.7.7-Java-11,2.6",cluster2
```
A `software.csv`file with just the columns is already provided.

### Raw Output

#### Collector Script:
For obtaining the raw output, use the `collector.py` script located in this repo.
The `COLLECTOR.md` file goes over how to use it. The `collector.py` file will create the proper directory structure for each type of data.

#### Manual
If you would rather collect the data manually, the rest of the section will cover how format that data

The raw output of a specific command or supported file types (SDS will parse it and extract the software info)
All files for this section must be within subdirectories. The name of each subdirectory
should be the name of a resource to which the files belong. `resource` refers to a specific cluster.
- `module spider` output (lmod)
  - If you use lmod for managing packages/environments then run `module spider` on your
 system and save the output to a text file
  - If you are using the docker, then the parent directory must be named `spider_data`
- Container definition (`.def`) file
  - You can also provide container definition files within the proper resource directory
 and the SDS tool will attempt to parse it and extract any relevant software information.
 The name of the `.def` is treated as the container name.
  - If you are using the version of sds docker, then the parent directory must be named `spider_data`
  - Aside from the raw `.def` file, you can also add curated information for specific containers.
 All csv files must have a software_name and (container_file or definition_file) columns.
 Here is the complete list of supported columns: `software_name, software_versions, container_name,
 definition_file, container_file, notes, command`.
    - If no container_name is provided then the definition_file name will be used as container name.
     The csv file is meant to supplement the `.def` files so that you can provide data the parser may have missed,
     or provide extra information for specific containers (such as `notes` on how to run them)
  - You can also provide only the `.csv` file, `.def` files or both. Information will only be added to and not overwritten.
  - Here is an example `.csv` file or a container:
```
  software_name,software_versions,container_name,definition_file,container_file,container_description,notes,command
  adapterremoval,2.3.2,,/share/singularity/adapterremoval.def,/share/singularity/adapterremoval.sinf,singularity run --app adapterremoval232 /share/singularity/share/singularity/afterqc.sinf AdapterRemoval
  afterqc,0.9.7,,/share/singularity/afterqc,/share/singularity/afterqc.sinf,singularity run --app afterqc097 /share/singularity/share/singularity/afterqc.sinf python /usr/local/Miniconda3/envs/afterqc-0.9.7/bin/after.py -1 R1.fq.gz
```

Here is an example of a proper directory structure for the data:
```
SDS
  ├──container_data/
  |    └── {resource_name}/
  |         ├── {resource_name}.csv    # CSV file with container metadata
  |         └── {preserved_directory_structure}/
  |             └── {definition_files}  # Original definition files with paths preserved
  |
  └──spider_data/
  |    └── {resource_name}/
  |        └── {resource_name}_spider.txt  # Complete output from module spider
  |
  └──software.csv
```

## Parser
The built in parser will attempt to gather software information based on the data provided, but it may not always be successful depending on your naming scheme.
You can define how the built in parser parses your information. View the **`PARSER.md`** file for more details on standard formats and how to modify the parsers.
