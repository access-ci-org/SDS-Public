# HPC Software Documentation Service

## What is the SDS?

The Software Documentation Service (SDS) is a tool designed to display the software available on different HPC systems.

For HPC end users it is a way to easily determine which software are available on which clusters as well as any relevant
documentation, software type classification, example use, descriptions, etc.

For HPC admins, it is an easy way to provide documentation for software on their systems.
All they need to do is provide the names of the software and which cluster they are available on and the SDS tool will provide the rest.

## SDS Quick Start

The following explains how to setup and run SDS on a Linux system using Docker.
If you would like to discuss implementing the SDS at you institution or would like a walk through of the sds and its setup, please contact Sandesh at <sla302@uky.edu>.
You can find a more detailed set of instructions with information on different features in the `SDS_SETUP.md` file.

---

### Step 0 - Ensure Docker is installed

```bash
# Install Docker (choose one based on your system)
dnf install -y docker
# or
yum install -y docker
# or, on Debian/Ubuntu
apt install -y docker.io

# Enable and start Docker service
systemctl enable docker
systemctl start docker

# Verify Docker is running
docker --version
systemctl status docker
```

### Step 1 -- Configure Docker access and open ports

```bash
# Add your user to the docker group so you can run `docker` without sudo
sudo usermod -aG docker $USER
# Log out and back in (or run `newgrp docker`) for the group change to take effect

# Open port 8080 for the SDS website
sudo firewall-cmd --permanent --add-port=8080/tcp
# Also open 443 if you want https/ssl
# sudo firewall-cmd --permanent --add-port=443/tcp
sudo firewall-cmd --reload

# Verify firewall settings
sudo firewall-cmd --list-ports
```

### Step 2 - Create config.yaml file

```bash
# Create a working directory for SDS and move into it
mkdir ~/sds && cd ~/sds

# Create default config file.
# Edit this to add your API key (contact Sandesh <sla302@uky.edu> to get an api key)
cat << EOF > config.yaml
api:
  use_api: False
  api_key: "your api key here"
  use_curated_info: False
  use_ai_info: False
styles:
  primary_color: ""
  secondary_color: ""
  site_title: "SDS"
  logo: ""
general:
  user_name: user
  password: user
  share_with_devs: True
EOF
```

### Step 3 - Prepare and load data

```bash
mkdir -p data/spider_data data/container_data

# Create one subdirectory per resource/HPC system, e.g.
mkdir -p data/spider_data/<resource_name>
```

Transfer your `module spider` output for each cluster into the matching `data/spider_data/<resource_name>/` directory (any method — scp, rsync, cp from a mounted filesystem).

It is also possible to display container information and other data on SDS. View the
`SDS_SETUP.md` file on how. Or contact Sandesh <sla302@uky.edu> for help.

### Step 4 - Build and Start Docker Container

```bash
# Download the latest container image and tag it with a short local alias
docker image pull public.ecr.aws/access-ci-org-public-containers/support/standalone-sds:latest
docker tag public.ecr.aws/access-ci-org-public-containers/support/standalone-sds:latest sds-image:latest

# Run the container
docker run -d --name sds \
  -p 8080:80 \
  --mount type=bind,source="./config.yaml",target="/sds/config.yaml" \
  -v ./data:/sds/data \
  sds-image:latest

# Verify the container is running
docker ps -a
```

SDS stores its state (database, logs, cached analytics, etc.) under `./data/state/` on the host. As long as you keep that directory, container replacement is non-destructive.

See `SDS_SETUP.md` for more detailed instructions on additional data types, SSL, log locations, and tuning.

---

**That's it!**

The website will be running and accessible on port **8080** (e.g. <your_ip_address>:8080)

If you would like to enable ssl for your service, view the `SDS_SETUP.md` file or contact Sandesh.

If you run into any trouble, have questions, or would like to request new features email Sandesh (<sla302@uky.edu>). We would be happy to help!

---

### Optional - Restarting the Container and Pruning Files

Data changes hot-reload — edit files in `./data/` and SDS picks them up without a restart. You only need to stop and start the container if you change `config.yaml` or want to add a new mount.

Stop and start the container

```bash
docker stop sds
docker start sds
```

If you want to delete the container and images

```bash
# Stop running container
docker stop sds
docker rm sds

# view existing images
docker image ls
# delete existing image
docker image rm sds-image:latest

# remove all unused cache
docker system prune
```

### Upgrading from the multi-mount layout

If your existing deployment uses separate mounts for `software.csv`, `container_data/`, `spider_data/`, etc., run the migration script on the host (with the container stopped):

```bash
bash migrate_data_layout.sh
```

It moves your existing files into `./data/`, refuses to clobber anything, and prints the new `docker run` command to use. Then re-run with the single `-v ./data:/sds/data` mount as in Step 4.

**Don't forget to update any scripts that push data to the SDS VM** (cron jobs, rsync wrappers, post-deploy hooks, etc.). Destination paths shift from `~/spider_data/<resource>/`, `~/container_data/<resource>/`, etc. to `~/sds/data/spider_data/<resource>/`, `~/sds/data/container_data/<resource>/`, etc.
