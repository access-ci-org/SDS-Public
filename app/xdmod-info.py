##################################################
#               XDMOD-DATA TUTORIAL              #
# FROM: https://github.com/ubccr/xdmod-notebooks #
# Source: XDMoD-Data-First-Example.ipynb         #
##################################################

# Display Pandas DataFrames as Markdown Tables
from IPython.display import display, Markdown
def display_df_md_table(df):
    return display(Markdown(df.replace('\n', '<br/>', regex=True).to_markdown()))

# XMMod Theme for Plotly plots
import plotly.express as px
import plotly.io as pio
import xdmod_data.themes
pio.templates.default = "timeseries"

######################
### REQUIRED SETUP ###
######################
# Required modules/updates should be handled by the env
# If not, update env.yaml. Use this as a last resort:
# import sys
# ! {sys.executable} -m pip install --upgrade xdmod-data python-dotenv tabulate

# Step 1 - Create XDMod Env File
from pathlib import Path
from os.path import expanduser
xdmod_data_env_path = Path(expanduser('~/xdmod-data.env'))
try:
    with open(xdmod_data_env_path):
        pass
except FileNotFoundError:
    with open(xdmod_data_env_path, 'w') as xdmod_data_env_file:
        xdmod_data_env_file.write('XDMOD_API_TOKEN=')
    xdmod_data_env_path.chmod(0o600)

# Step 2 - Create and store your API Key
# Use this to obtain an API Key: https://github.com/ubccr/xdmod-data#api-token-access
# Open the xdmod-data.env file and paste your token after XDMOD_API_TOKEN=
# Save the file, then continue

# Load contents of xdmod-data.env into the environment
# Prints 'True' if successful
from dotenv import load_dotenv
load_dotenv(xdmod_data_env_path, override=True)

# Initialize the XDMod Data Warehouse
from xdmod_data.warehouse import DataWarehouse
dw = DataWarehouse('https://xdmod.access-ci.org')

#####################
### QUICK EXAMPLE ###
#####################
# Get Data
with dw:
    data = dw.get_data(
        duration=('2023-01-01', '2023-04-30'),
        realm='Jobs',
        metric='Number of Users: Active',
    )
display(data) # Data is a Pandas DataFrame

# Plot the Data
plot = px.line(data, y='Number of Users: Active')
plot.show()

# Additional Processing
# Add column to DataFrame for the day of the week
data['Day Name'] = data.index.strftime('%a')
display(data)

plot = px.box(
    data,
    x='Day Name',
    y='Number of Users: Active',
    category_orders={'Day Name': ('Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat')},
)
plot.show()
###################
### END EXAMPLE ###
###################

####################
### INSTRUCTIONS ###
####################
# Use this as a template for making Warehouse calls
# Use runtime context of Python's 'with' statement to wrap XDMod Queries
# Store the result, then execute calculations outside the runtime context
with dw:
    # XDMoD queries would go here
    pass
# Data processing would go here
pass

# Default parameters of get_data()
with dw:
    data = dw.get_data(
        duration='Previous month',
        realm='Jobs',
        metric='CPU Hours: Total',
        dimension='None',
        filters={},
        dataset_type='timeseries',
        aggregation_unit='Auto',
    )

### Duration ##
###############
# Provides time constraints of the data to be fetched from the XDMod Warehouse
# Option 1: Start and End Times
with dw:
    data = dw.get_data(duration=('2023-01-01', '2023-04-30'))

# Option 2: Duration String Values
# These can be found with get_durations() method:
with dw:
    durations = dw.get_durations()
display(durations)
# Duration Options
'''
'Yesterday', '7 day', '30 day', '90 day', 'Month to date', 'Previous month', 
'Quarter to date', 'Previous quarter', 'Year to date', 'Previous year',
'1 year', '2 year', '3 year', '5 year', '10 year',
'2024', '2023', '2022', '2021', '2020', '2019', '2018'
'''

### Realm ###
#############
# Category of data in XDMod Data Warehouse
# These can be found with describe_realms() method:
with dw:
    realms = dw.describe_realms()
display_df_md_table(realms)
'''
id	        label
Accounts	Accounts
Allocations	Allocations
Cloud	    Cloud
Gateways	Gateways
Jobs	    Jobs
Requests	Requests
SUPREMM	    SUPREMM
'''

### Metric ###
##############
# Statistics which we are trying to gather
# These can be found with describe_metrics(realm) method:
with dw:
    metrics = dw.describe_metrics('Jobs')
display_df_md_table(metrics)
'''
id	                                label	                                        description
avg_ace	                            ACCESS Credit Equivalents Charged: Per Job (SU)	The average amount of ACCESS Credit Equivalents charged per compute job.
                                                                                    The ACCESS Credit Equivalent is a measure of how much compute time was used on each resource.
                                                                                    One ACCESS Credit Equivalent is defined as one CPU Hour on SDSC Expanse (an AMD EPYC 7742 based compute resource).
                                                                                    The ACCESS Credit Equivalent allows comparison between usage of node-allocated, core-allocated and GPU-allocated
                                                                                    resources. It also allows a comparison between resources with different compute power per core.
                                                                                    The ACCESS allocations exchange calculator
                                                                                    lists conversion rates between an ACCESS Credit Equivalent and a service unit on a resource.

total_ace	                        ACCESS Credit Equivalents Charged: Total (SU)	The total amount of ACCESS Credit Equivalents charged.
                                                                                    The ACCESS Credit Equivalent is a measure of how much compute time was used on each resource.
                                                                                    One ACCESS Credit Equivalent is defined as one CPU Hour on SDSC Expanse (an AMD EPYC 7742 based compute resource).
                                                                                    The ACCESS Credit Equivalent allows comparison between usage of node-allocated, core-allocated and GPU-allocated
                                                                                    resources. It also allows a comparison between resources with different compute power per core.
                                                                                    The ACCESS allocations exchange calculator
                                                                                    lists conversion rates between an ACCESS Credit Equivalent and a service unit on a resource.

utilization	                        ACCESS Utilization (%)	                        The percentage of the ACCESS obligation of a resource that has been utilized by ACCESS jobs.
                                                                                    ACCESS Utilization: The ratio of the total CPU hours consumed by ACCESS jobs over a given time period divided by the total CPU hours 
                                                                                    that the system is contractually required to provide to ACCESS during that period. It does not include non-ACCESS jobs.
                                                                                    It is worth noting that this value is a rough estimate in certain cases where the resource providers don't provide accurate records 
                                                                                    of their system specifications, over time.

rate_of_usage	                    Allocation Usage Rate (XD SU/Hour)	            The rate of ACCESS allocation usage in XD SUs per hour.

rate_of_usage_ace	                Allocation Usage Rate ACEs (SU/Hour)	        The rate of ACCESS allocation usage in ACCESS Credit Equivalents per hour.

avg_cpu_hours	                    CPU Hours: Per Job	                            The average CPU hours (number of CPU cores x wall time hours) per ACCESS job.
                                                                                    For each job, the CPU usage is aggregated. For example, if a job used 1000 CPUs for one minute, it would be aggregated as 1000 CPU minutes or 16.67 CPU hours.

total_cpu_hours	                    CPU Hours: Total	                            The total CPU hours (number of CPU cores x wall time hours) used by ACCESS jobs.
                                                                                    For each job, the CPU usage is aggregated. For example, if a job used 1000 CPUs for one minute, it would be aggregated as 1000 CPU minutes or 16.67 CPU hours.

max_processors	                    Job Size: Max (Core Count)	                    The maximum size ACCESS job in number of cores.
                                                                                    Job Size: The total number of processor cores used by a (parallel) job.

min_processors	                    Job Size: Min (Core Count)	                    The minimum size ACCESS job in number of cores.
                                                                                    Job Size: The total number of processor cores used by a (parallel) job.

normalized_avg_processors	        Job Size: Normalized (% of Total Cores)	        The percentage average size ACCESS job over total machine cores.
                                                                                    Normalized Job Size: The percentage total number of processor cores used by a (parallel) job over the total number of cores on the machine.

avg_processors	                    Job Size: Per Job (Core Count)	                The average job size per ACCESS job.
                                                                                    Job Size: The number of processor cores used by a (parallel) job.

avg_job_size_weighted_by_ace	    Job Size: Weighted By ACEs (Core Count)	        The average job size weighted by charge in ACCESS Credit Equivalents (ACEs). Defined as
                                                                                    Average Job Size Weighted By ACEs: sum(i = 0 to n){job i core count*job i charge in ACEs}/sum(i = 0 to n){job i charge in ACEs}

avg_job_size_weighted_by_cpu_hours	Job Size: Weighted By CPU Hours (Core Count)	The average ACCESS job size weighted by CPU Hours. Defined as
                                                                                    Average Job Size Weighted By CPU Hours: sum(i = 0 to n){ job i core count * job i cpu hours}/sum(i = 0 to n){job i cpu hours}

avg_job_size_weighted_by_xd_su	    Job Size: Weighted By XD SUs (Core Count)	    The average ACCESS job size weighted by charge in XD SUs. Defined as
                                                                                    Average Job Size Weighted By XD SUs: sum(i = 0 to n){job i core count*job i charge in xd sus}/sum(i = 0 to n){job i charge in xd sus}

avg_nu	                            NUs Charged: Per Job	                        The average amount of NUs charged per ACCESS job.
                                                                                    NU - Normalized Units: Roaming allocations are awarded in XSEDE Service Units (SUs). 1 XSEDE SU is defined as one CPU-hour on a Phase-1 DTF cluster.
                                                                                    For usage on a resource that is charged to a Roaming allocation, a normalization factor is applied. The normalization factor is based on
                                                                                    the method historically used to calculate 'Normalized Units' (Cray X-MP-equivalent SUs), which derives from a resource's performance on the HPL
                                                                                    benchmark.
                                                                                    Specifically, 1 Phase-1 DTF SU = 21.576 NUs, and the XD SU conversion factor for a resource is calculated by taking its NU conversion factor
                                                                                    and dividing it by 21.576. The standard formula for calculating a resource's NU conversion factor is: (Rmax * 1000 / 191) / P
                                                                                    where Rmax is the resource's Rmax result on the HPL benchmark in Gflops and P is the number of processors used in the benchmark.
                                                                                    In the absence of an HPL benchmark run, a conversion factor can be agreed upon, based on that of an architecturally similar platform
                                                                                    and scaled according to processor performance differences.
                                                                                    Conversion to Roaming SUs is handled by the XSEDE central accounting system, and RPs are only required to report usage in local SUs for all allocations.
                                                                                    Defining an SU charge for specialized compute resources (such as visualization hardware) or non-compute resources (such as storage) is possible, 
                                                                                    but there is no XSEDE-wide policy for doing so.

total_nu	                        NUs Charged: Total	                            The total amount of NUs charged by ACCESS jobs.
                                                                                    See 'avg_nu' for details.

avg_node_hours	                    Node Hours: Per Job	                            The average node hours (number of nodes x wall time hours) per ACCESS job.

total_node_hours	                Node Hours: Total	                            The total node hours (number of nodes x wall time hours) used by ACCESS jobs.

active_allocation_count	            Number of Allocations: Active	                The total number of funded projects that used ACCESS resources.

active_institution_count	        Number of Institutions: Active	                The total number of institutions that used ACCESS resources.

job_count	                        Number of Jobs Ended	                        The total number of ACCESS jobs that ended within the selected duration.

running_job_count	                Number of Jobs Running	                        The total number of ACCESS jobs that are running.

started_job_count	                Number of Jobs Started	                        The total number of ACCESS jobs that started executing within the selected duration.

submitted_job_count	                Number of Jobs Submitted	                    The total number of ACCESS jobs that submitted/queued within the selected duration.

gateway_job_count	                Number of Jobs via Gateway	                    The total number of ACCESS jobs submitted through gateways (e.g., via a community user account) that ended within the selected duration.
                                                                                    Job: A scheduled process for a computer resource in a batch processing environment.

active_pi_count	                    Number of PIs: Active	                        The total number of PIs that used ACCESS resources.

active_resource_count	            Number of Resources: Active	                    The total number of active ACCESS resources.

active_person_count	                Number of Users: Active	                        The total number of users that used ACCESS resources.

expansion_factor	                User Expansion Factor	                        Gauging ACCESS job-turnaround time, it measures the ratio of wait time and the total time from submission to end of execution.
                                                                                    User Expansion Factor = ((wait duration + wall duration) / wall duration).

avg_waitduration_hours	            Wait Hours: Per Job	                            The average time, in hours, a ACCESS job waits before execution on the designated resource.
                                                                                    Wait Time: Wait time is defined as the linear time between submission of a job by a user until it begins to execute.

total_waitduration_hours	        Wait Hours: Total	                            The total time, in hours, ACCESS jobs waited before execution on their designated resource.
                                                                                    Wait Time: Wait time is defined as the linear time between submission of a job by a user until it begins to execute.

avg_wallduration_hours	            Wall Hours: Per Job	                            The average time, in hours, a job takes to execute.
                                                                                    In timeseries view mode, the statistic shows the average wall time per job per time period. 
                                                                                    In aggregate view mode the statistic only includes the job wall hours between the defined time range. 
                                                                                    The wall hours outside the time range are not included in the calculation.
                                                                                    Wall Time: Wall time is defined as the linear time between start and end time of execution for a particular job.

total_wallduration_hours	        Wall Hours: Total	                            The total time, in hours, ACCESS jobs took to execute.
                                                                                    Wall Time: Wall time is defined as the linear time between start and end time of execution for a particular job.

avg_su	                            XD SUs Charged: Per Job	                        The average amount of XD SUs charged per ACCESS job.
                                                                                    XD SU: 1 XSEDE SU is defined as one CPU-hour on a Phase-1 DTF cluster.
                                                                                    SU - Service Units: Computational resources on the XSEDE are allocated and charged in service units (SUs). 
                                                                                    SUs are defined locally on each system, with conversion factors among systems based on HPL benchmark results.
                                                                                    Current TeraGrid supercomputers have complex multi-core and memory hierarchies. 
                                                                                    Each resource has a specific configuration that determines the number (N) of cores that can be dedicated to a job without slowing the code (and other user and system codes). 
                                                                                    Each resource defines for its system the minimum number of SUs charged for a job running in the default batch queue, calculated as wallclock runtime multiplied by N. 
                                                                                    Minimum charges may apply.
                                                                                    Note: The actual charge will depend on the specific requirements of the job (e.g., the mapping of the cores across the machine, or the priority you wish to obtain).
                                                                                    Note 2: The SUs show here have been normalized against the XSEDE Roaming service. Therefore they are comparable across resources.

total_su	                        XD SUs Charged: Total	                        The total amount of XD SUs charged by ACCESS jobs.
                                                                                    See 'avg_su' for details.
'''

### Dimension ###
#################
# Groupings of data
# These can be found with describe_dimensions(realm) method,
# which yields a DataFrame containing the list of valid dimensions for a given realm
with dw:
    dimensions = dw.describe_dimensions('Jobs')
display_df_md_table(dimensions)
'''
id	                    label	                    description
===========================================================================================================================================================
none	                None	                    Summarizes jobs reported to the ACCESS allocations service (excludes non-ACCESS usage of the resource).
allocation	            Allocation	                A funded project that is allowed to run jobs on resources.
fieldofscience	        Field of Science	        The field of science indicated on the allocation request pertaining to the running jobs.
gateway	                Gateway	                    A science gateway is a portal set up to aid submiting jobs to resources.
grant_type	            Grant Type	                A categorization of the projects/allocations.
jobsize	                Job Size	                A categorization of jobs into discrete groups based on the number of cores used by each job.
jobwaittime	            Job Wait Time	            A categorization of jobs into discrete groups based on the total linear time each job waited.
jobwalltime	            Job Wall Time	            A categorization of jobs into discrete groups based on the total linear time each job took to execute.
nsfdirectorate	        NSF Directorate	            The NSF directorate of the field of science indiciated on the allocation request pertaining to the running jobs.
nodecount	            Node Count	                A categorization of jobs into discrete groups based on node count.
pi	                    PI	                        The principal investigator of a project.
pi_institution	        PI Institution	            Organizations that have PIs with allocations.
pi_institution_country	PI Institution Country	    The country of the institution of the PI of the project associated with compute jobs.
pi_institution_state	PI Institution State	    The location of the institution of the PI of the project associated with the compute jobs.
parentscience	        Parent Science	            The parent of the field of science indiciated on the allocation request pertaining to the running jobs.
queue	                Queue	                    Queue pertains to the low level job queues on each resource.
resource	            Resource	                A resource is a remote computer that can run jobs.
resource_type	        Resource Type	            A categorization of resources into by their general capabilities.
provider	            Service Provider	        A service provider is an institution that hosts resources.
username	            System Username	            The specific system username of the users who ran jobs.
person	                User	                    A person who is on a PIs allocation, hence able run jobs on resources.
institution	            User Institution	        Organizations that have users with allocations.
institution_country	    User Institution Country	The name of the country of the institution of the person who ran the compute job.
institution_state	    User Institution State	    The location of the institution of the person who ran the compute job.
nsfstatus	            User NSF Status	            Categorization of the users who ran jobs.
'''
# For API methods that take realms, metrics, and/or dimensions, you can pass them by ID or Label:
with dw:
    data = dw.get_data(
        duration='10 year',
        realm='Allocations',
        metric='NUs: Allocated', # 'allocated_nu' also works
        dimension='Resource Type',  # 'resource_type' also works
    )

### Filters ###
###############
# Allow you to only include data which have certain values for given dimensions
# These can be found with get_filter_values(realm, dimension)
# which yields a DataFrame containing a list of valid filters for the given realm and dimension, which much be passed in as strings
with dw:
    filter_values = dw.get_filter_values('Jobs', 'Resource') # 'resource' also works
display_df_md_table(filter_values)
'''
id	    label
4	    ANL DTF
2759	ANL VIS
2903	Bridges 2 EM
2902	Bridges 2 GPU
2900	Bridges 2 RM
2966	Bridges2 GPU AI
5	    CALTECH DTF
2812	CCT LSU SUPERMIC
2899	Expanse
2901	Expanse GPU
2800	GATECH KEENELAND
2809	GATECH KIDS
3262	IACS Ookami
2214	IU BIGRED*
2769	IU QUARRY
1549	IU TIGER
3131	JHU Rockfish A100
3130	JHU Rockfish LM
3064	JHU Rockfish RM
2965	KyRIC
2765	LONI QUEENBEE
2758	NCAR FROST
2756	NCSA ABE
1566	NCSA COBALT
2015	NCSA COPPER
3031	NCSA DELTA CPU
3032	NCSA DELTA GPU
3	    NCSA DTF
2789	NCSA EMBER*
2795	NCSA FORGE
2779	NCSA LINCOLN
2018	NCSA TUNGSTEN
3560	neocortex sdflex.psc.access ci.org
2780	NICS ATHENA
2813	NICS DARTER
2767	NICS KRAKEN
2786	NICS NAUTILUS
1556	ORNL NSTG
2799	OSG
1580	PSC BIGBEN
2793	PSC BLACKLIGHT
2819	PSC BRIDGES
2833	PSC BRIDGES AI
2824	PSC BRIDGES GPU
2820	PSC BRIDGES LARGE
2817	PSC GREENFIELD
1554	PSC LEMIEUX
3527	PSC Neocortex
2770	PSC POPLE
1550	PSC RACHEL
3097	Purdue Anvil CPU
3132	Purdue Anvil GPU
2768	PURDUE BRUTUS
1551	PURDUE CLOUD
2020	PURDUE CONDOR
2218	PURDUE LEAR
1548	PURDUE RADON
2771	PURDUE STEELE
2766	PURDUE TERADRE
2014	SDSC BLUEGENE
2814	SDSC COMET
2828	SDSC COMET GPU
2783	SDSC DASH
1552	SDSC DATASTAR
2016	SDSC DATASTAR P655
2	    SDSC DTF
2796	SDSC GORDON
2792	SDSC TRESTLES
2825	STAMPEDE2 TACC
2823	Stanford XSTREAM
1547	TACC LONESTAR
2791	TACC LONESTAR4
2781	TACC LONGHORN
1553	TACC MAVERICK
2811	TACC MAVERICK2
2755	TACC RANGER
2775	TACC SPUR
2801	TACC STAMPEDE
3396	TACC STAMPEDE3
2815	TACC WRANGLER
3295	Texas A&M U FASTER
2999	UD DARWIN
3000	UD DARWIN GPU
'''
# For API methods that take filters as arguments, you must specify filters as a dictionary in which the keys are dimensions (labels of IDs) 
# and the values are string filter values (labels or IDs) or sequences of string filter values.
# For example, to return data for which the field of science is biophysics and the resource is either NCSA Detla GPU or TACC Stampede2:
with dw:
    data = dw.get_data(
        filters={
            'Field of Science': 'Biophysics', # 'fieldofscience': '246' also works
            'Resource': ( # 'resource' also works
                'NCSA DELTA GPU', # '3032' also works
                'STAMPEDE2 TACC', # '2825' also works
            ),
        },
    )

### Dataset Type ###
####################
# Can be either 'timeseries', in which data is grouped by time aggregation units,
# or 'aggregate', in which the data is aggregated across the entire duration.
with dw:
    data = dw.get_data(dataset_type='timeseries')

### Aggregation Unit ###
########################
# Specifies how data is aggregated by time.
# These can be found with get_aggregation_units() method:
with dw:
    display(dw.get_aggregation_units())
    
'''
'Auto', 'Day', 'Month', 'Quarter', 'Year'
'''