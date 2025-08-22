# HPC Software Documentation Service

The Software Documentation Service (SDS) is a tool designed to display the software available on different HPC systems.  

For HPC end users it is a way to easily determine which software are available on which clusters as well as any relevant 
documentation, software type classification, example use, descriptions, etc.  

For HPC admins, it is an easy way to provide documentation for software on their systems.
All they need to do is provide the names of the software and which cluster they are available on and the SDS tool will provide the rest.

# Setting up the application
**Bash or Zsh terminals are recommended**  
**Windows machine: Install Miniconda or Anaconda manually**  

The SDS tool is meant to exist independent of any HPC clusters and should not be run on any critical systems.
The recommended method is to run the application inside of a VM and copy/add any important information to it.

1. Clone the repo into your local machine: `git clone <URL>.git`
2. Follow instructions to set [Config Variables](#config-variables)

That should be all the necessary setup

## Running the application

1. Run `source setup.sh` to setup your environment
2. Run the application with `flask run & python pull_api.py`
  - pull_api.py continuously runs and pulls new software data from the  [SDS_API](https://github.com/access-ci-org/Support-ARA-DB) every 24 hours
  - To close the application use CTRL+C, then run 'fg' to view the background flask app, followed by CTRL+C again.

## Config Variables
- Create a `config.yaml` file in the project folder.  
- Inside the `config.yaml` file, add the following:  
```
api:
  api_key: "your api key here"
  version: "SDS_API version"
styles:
  primary_color: "your primary color here"
  secondary_color: "your secondary color"
  site_title: "Title for website here"
```

- `api_key` API key to the sds website, you can obtain one by contacting Sandesh.
- `version` Version of the SDS_API that you are using. Current functionality intended for version 0.1
- Set `primary_color` and `secondary_color` to set the colors (in hexadecimal, e.g. #1B365D) for the website. Different shades of these two colors are used. Darker, monochromatic, colors are recommended. Default Primary: #1b365d, Default Secondary: #324a6d  
- Set `site_title` to be the main title you want for your website. Default: SDS