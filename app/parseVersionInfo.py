import re
import pandas as pd

RP_NAMES = [
    'aces', 'anvil', 'bridges-2', 'DARWIN', 'delta', 'expanse', 'faster', 
    'jetstream', 'kyric', 'ookami', 'stampede-3'
]

# Skip RPs that don't currently have spider outputs
SKIPPED_RPS = {'DARWIN'}

# I/O Locations
SPIDER_DIRECTORY = './data/spiderOutput/'
SPIDER_POSTFIX = '_spider_output.txt'
OUTPUT_DIRECTORY = './data/CSV/versionInfo.csv'


#################################################################
#   parse_version_info                                          #
#       Converts a module_spider line into a formatted tuple    #
#       Args:                                                   #
#           line: single line taken from a module_spider file   #
#       Return:                                                 #
#           software: software name                             #
#           versions: cleaned up version information as a list  #
#################################################################
def parse_version_info(line):
    # Split the input into two parts for processing
    software, versions = line.split(": ") 
    # 'Compile' the software name plus '/' as a regex pattern
    pattern = re.compile(rf'{re.escape(software)}/')
    # 'Substitute' the pattern for an empty string    
    versions = pattern.sub('', versions) 
    # Make software uniformly lowercase. Important later,
    # once we start merging them together               
    software = software.split("/")[0].lower()           
                                                        
    return software, versions


#########################################################################
#   spider_to_dictionary                                                #
#       Creates a Dictionary from a module_spider file                  #
#       Args:                                                           #
#           input_file: single module_spider file                       #
#       Functions:                                                      #
#           parse_version_info: Processing per line of the file         #
#       Return:                                                         #
#           version_info_dict: Dictionary of software:version tuples    #           
#########################################################################
def spider_to_dictionary(input_file):
    version_info_dict = {}
    with open(input_file, 'r') as infile:
        for line in infile:
            # Find Lines that start with two white spaces, 
            # which is how module_spider is formatted
            if (re.match(r'^ {2}(?!\s)', line)):
                # Strip off whitespace from tuple                        
                software, versions = parse_version_info(line.strip()) 
                # Add tuple to dictionary  
                version_info_dict[software] = versions                  
        infile.close()
        return version_info_dict


#####################################################################
#   generate_RP_dictionaries                                        #
#       Creates a Dictionary of RP Software Dictionaries            #
#       Functions:                                                  #
#           spider_to_dictionary: Create individual RP Dictionaries #
#       Return:                                                     #
#           rp_dict: Dictionary -> {RP Name:RP Dictionary}          #
#####################################################################
def generate_rp_dictionaries():
    rp_dict = {}
    # For each RP
    for rp_name in RP_NAMES:  
        # Skip RPs without module_spider configured                                                
        if rp_name not in SKIPPED_RPS:                                           
            # Find module_spider file
            file_name = SPIDER_DIRECTORY + rp_name + SPIDER_POSTFIX
            # Store RP Dictionary under RP Name           
            rp_dict[rp_name] = spider_to_dictionary(file_name)                   
    return rp_dict


#####################################################################
#   convert_RP_dict_to_DataFrame                                    #
#       Convert Combined RP Dictionary to Pandas DataFrame          #
#       Functions:                                                  #
#           generate_RP_dictionaries: Create Dictionary per RP      #
#       Return:                                                     #
#           df: DataFrame with Combined Version Info                #
#####################################################################
def convert_rp_dict_to_df():
    combined_VI_dict = {}
    rp_VI_dict = generate_rp_dictionaries()

    # Combine Dictionaries together to be added to DataFrame
    for rp_name in RP_NAMES:
        if rp_name in SKIPPED_RPS:
            continue
        else:
            # For each software in each RP Dictionary
            for software in rp_VI_dict[rp_name]:
                rp_version_info = rp_name + ": " + rp_VI_dict[rp_name].get(software) # Formatted String
                # If software key already exists in dictionary, append RP Version Info to the same key
                #   otherwise, key is overwritten by most-recent value
                if software in combined_VI_dict:
                    combined_VI_dict[software] = combined_VI_dict[software] + "\n" + rp_version_info
                else:   
                    combined_VI_dict[software] = rp_version_info
    
    # Create DataFrame from Combined Dictionary
    df = pd.DataFrame.from_dict(combined_VI_dict, orient='index', columns=['Version Info'])
    df.index.name = 'Software'                              # Define Index of DataFrame
    df.reset_index(inplace=True)                            # Include Index in DataFrame
    df.to_csv(OUTPUT_DIRECTORY,index=False) # Write DataFrame to CSV (Testing Purposes)
    return df


#############################################################################
#   add_version_info_to_table  \                                            #
#       Add Combined RP Version Info DataFrame to Static DataFrame          #
#       Args:                                                               #
#           static_df: DataFrame from Static Table                          #
#       Functions:                                                          #
#           convert_RP_dict_to_df: Create DataFrame from RP Dictionary      #
#       Return:                                                             #
#           merged_df: Static DataFrame merged with Version Info DataFrame  #
#############################################################################
def add_version_info_to_table(static_df):
    version_df = convert_rp_dict_to_df()
    # 'Left' Join returns all rows from static_df
    # and adds version_df to them based on the
    # matching 'Software' column in both
    merged_df = static_df.merge(version_df, how='left', on='Software')  
    return merged_df





### IGNORE #######################################################
# Implementation for outputting to a text file instead of a dict #
# In case we ever want this in the future                        #
##################################################################
'''
input_files = {Put Input Files Here}
output_file = 'Put Output File Here'

# Output to a .txt File
def processVersionInfo(input_files, output_file):
    processed_lines = set()
    with open(output_file, 'w') as outfile:
        for input_file in input_files:
            with open(input_file, 'r') as infile:
                for line in infile:
                    if (re.match(r'^ {2}(?!\s)', line)):    # Find Lines that start with two white spaces, 
                                                            # which is currently how this file is formatted
                        processed_line = parseVersionInfo(line.strip())
                        if processed_line not in processed_lines:                            
                            outfile.write(processed_line + '\n')
                            processed_lines.add(processed_line)


# Parse Version Numbers into CSV-Usable Text
def parseVersionInfo(line):
    
    software, versions = line.split(": ")               # Select everything before the colon as the pattern
    pattern = re.compile(rf'{re.escape(software)}/')    # 'Compile' the software name + / as a regex pattern
    versions = pattern.sub('', versions)                # 'Substitute' software name for an empty string
    versions = re.sub(r', ', ',', versions)             # Trim white space between versions
    
    return f"{software}:{versions.strip()}"

# Testing, Deletes output_file first before running
if os.path.exists(output_file):
    os.remove(output_file)
processVersionInfo(input_files, output_file)
'''