# HPC Software Documentation Service

## What is the SDS?

The Software Documentation Service (SDS) is a tool designed to display the software available on different HPC systems.

For HPC end users it is a way to easily determine which software are available on which clusters as well as any relevant
documentation, software type classification, example use, descriptions, etc.

For HPC admins, it is an easy way to provide documentation for software on their systems.
All they need to do is provide the names of the software and which cluster they are available on and the SDS tool will provide the rest.

## SDS Quick Start

The following explains how to setup and run SDS on a Linux system using Docker.
If you would like to discuss implementing the SDS at you institution please contact Sandesh at <sla302@uky.edu>.
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

### Step 1 – Configure Docker access and open ports (as root)

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
firewall-cmd --permanent --add-port=80/tcp
firewall-cmd --permanent --add-port=8080/tcp
firewall-cmd --reload

# Verify firewall settings
firewall-cmd --list-ports
```

### Step 2 - Download the repo and create config.yaml file

```bash
# switch to the sds user
su -l sds

# Clone the SDS repository
git clone https://github.com/access-ci-org/SDS-Public.git
cd SDS-Public/

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
mkdir spider_data
cd spider_data

# create one directory for each resource/HPC system
mkdir resource1

# Transfer data to the VM hosting sds
# for example:
# From where you have the lmod spider data copy/move your `module spider` data into the appropriate directory
scp your/resource1/spider_data/file sds@your_domain_or_ip:/home/sds/SDS-Public/spider_data/resource1/
# or
cp your/resource1/spider_data/file ~/SDS-Public/spider_data/resource1/

# return to sds base directory
cd ~/SDS-Public/
```

It is also possible to display container information on SDS. View the
`SDS_SETUP.md` file on how. Or contact Sandesh <sla302@uky.edu> for help

### Step 4 - Build and Start Docker Container

```bash
# Build and start in detached (daemon) mode
sudo docker compose up --build -d

# Verify running containers
sudo docker ps

# All logs will can be found in the logs directory (~/SDS-Public/logs)
# Modifying the following directories and files will automatically update the SDS within the container:
# config.yaml, spider_data, container_data, software_uses, software.csv
```

---

**That's it!**

The website will be running and accessible on port **8080** (e.g. <your_ip_address>:8080)

If you would like to enable ssl for your service, view the `SDS_SETUP.md` file or contact Sandesh.

If you run into any trouble or have questions email Sandesh (<sla302@uky.edu>). We would be happy to help!

---

### Optional - Restarting the Container and Pruning Files

Stop and start the container

```bash
# Stop running container
sudo docker compose down

# Rebuild and start again in detached mode
sudo docker compose up --build -d
```

For quick stop/start (no rebuild):

```bash
sudo docker compose stop
sudo docker compose start
```

If you notice that some changes aren't being applied, run the following:

```bash
# Stop running container
sudo docker compose down

# Prune docker system files
sudo docker system prune

# Rebuild and start again in detached mode
sudo docker compose up --build -d
```
