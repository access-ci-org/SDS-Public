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

# Enable and start Docker service
systemctl enable docker
systemctl start docker

# Verify Docker is running
docker --version
systemctl status docker
```

### Step 1 -- Configure Docker access and open ports (as root)

```bash
# Create a new user for SDS
adduser sds
passwd sds

# Add 'sds' to docker group
usermod -aG docker sds

# Allow passwordless docker for user 'sds'
echo "sds ALL=(ALL) NOPASSWD:/usr/bin/docker" > /etc/sudoers.d/sds
chmod 440 /etc/sudoers.d/sds

# Open required ports for HTTP (80) and app traffic (8080)
firewall-cmd --permanent --add-port=8080/tcp
# Also open the following if you want https/ssl
# firewall-cmd --permanent --add-port=443/tcp

firewall-cmd --reload

# Verify firewall settings
firewall-cmd --list-ports
```

### Step 2 - Create config.yaml file

```bash
# switch to the sds user
su -l sds

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
mkdir -p spider_data container_data
cd spider_data

# create one directory for each resource/HPC system
mkdir resource1

# Transfer data to the VM hosting sds
# for example:
# From where you have the lmod spider data copy/move your `module spider` data into the appropriate directory
scp your/resource1/spider_data/file sds@your_domain_or_ip:/home/sds/spider_data/resource1/
# or
cp your/resource1/spider_data/file ~/spider_data/resource1/

# return to sds base directory
cd ~
```

It is also possible to display container information and other data on SDS. View the
`SDS_SETUP.md` file on how. Or contact Sandesh <sla302@uky.edu> for help.

### Step 4 - Build and Start Docker Container

```bash
# Download the latest container image
docker image pull public.ecr.aws/access-ci-org-public-containers/support/standalone-sds:latest

# Run the container
docker run -d -p 8080:80 --mount type=bind,source="./config.yaml",target="/sds/config.yaml" -v ./spider_data:/sds/spider_data --name sds public.ecr.aws/access-ci-org-public-containers/support/standalone-sds:latest


# See SDS_SETUP.md for more detailed instructions.

# Verify the container is running
docker ps -a
```

---

**That's it!**

The website will be running and accessible on port **8080** (e.g. <your_ip_address>:8080)

If you would like to enable ssl for your service, view the `SDS_SETUP.md` file or contact Sandesh.

If you run into any trouble, have questions, or would like to request new features email Sandesh (<sla302@uky.edu>). We would be happy to help!

---

### Optional - Restarting the Container and Pruning Files

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
docker image rm public.ecr.aws/access-ci-org-public-containers/support/standalone-sds:latest

# remove all unused cache
docker system prune
```
