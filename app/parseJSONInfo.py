import json

# Various words and phrases that AI may use to label the related fields
# It's safe to expand these as necessary
SOFTWARE_ALIASES = [
    'tool', 
    'software_name', 
    'software name', 
    'Software Name', 
    'software'
    'Software'
    ]
DESCRIPTION_ALIASES = [
    'overview', 
    'comprehensive_overview', 
    'Comprehensive Overview', 
    'comprehensive overview'
    'AI Description'
    ]
FEATURES_ALIASES = [
    'core features', 
    'Core Features', 
    'core_features'
    ]
GEN_TAG_ALIASES = [
    'general tags', 
    'General Tags', 
    'general_tags'
    ]
ADD_TAG_ALIASES = [
    'additional tags', 
    'Additional Tags', 
    'additional_tags'
    ]
# Since every JSON should have a description, this is the most consistent way 
# to find if data has been nested
NESTED_KEY_PATH = [
    'overview', 
    'comprehensive_overview', 
    'Comprehensive Overview', 
    'comprehensive overview'
    ]
# These are used to find nested tags in an 'additional tags' field in JSONs
ADD_TAGS_TO_FIX = [
    'software_type',
    'software_class',
    'research_field',
    'research_area',
    'research_discipline',
    'field_of_science'
    ]

# Dictionary of common acronyms that should be capitalized
# Make sure to capitalize the first letter of each entry (text is titled)
# This ensures you don't erroneously grab random strings mid-word 
# (such as 'thiNGS' or 'kiDNApper')
# Add to this dictionary as necessary
COMMON_ACRONYMS_DICT = {
    'Aws':'AWS', 'Cli ':'CLI ', 'Dna':'DNA', 'Fea ':'FEA ', 'Gpu':'GPU', 'Gui ':'GUI ', 
    'Hpc':'HPC', 'Hts':'HTS', 'Ldap':'LDAP', 'Ngs':'NGS', 'Rna':'RNA', 'Sql':'SQL', 
    'Tls':'TLS', 'Xml':'XML' 
    }
#########################################################################
#   json_sanitizer                                                      #
#       Converts AI-generated JSON software files into a uniform format #
#        for to facilitate programmatic manipulation                    #
#       Parameters:                                                     #
#           file: the file to be formatted                              #
#########################################################################
def json_sanitizer(file):
    file_name = file.split('JSON/')[1]
    print("Sanitizing file: " + file_name)

    # Open JSON File
    with open(file, 'r') as infile:
        data = json.load(infile)
    
    # This is the structure we want by the end:
    #{
    #   Software: {}
    #   AI Description: {}
    #   Core Features: {}
    #   General Tags: {}
    #   Software Type: {}
    #   Software Class: {}
    #   Research Field: {}
    #   Research Area: {}
    #   Research Discipline: {}
    #}
    # Sometimes Research Field ends up at the bottom. This is fine.
    # Python dictionaries don't care about order, we do this for visual clarity

    ###########################################
    # 1) Check if the data we want is nested  #
    ###########################################
    # Search for nested tags
    # If found, move everything out of the nest and purge the old structure
    #print("1: Checking JSON structure")
    software_name = list(data.keys())[0]   
    for key in NESTED_KEY_PATH:
        if key in data[software_name]:
            data['Software'] = software_name.lower()
            #print("software_name moved!")

            for key in data[software_name]:
                data[key] = data[software_name][key]
                #print(key + " moved!")

            data.pop(software_name)
            #print("Unpacking complete!")

            # Save the file and exit the loop
            with open(file, 'w') as infile:
                json.dump(data, infile, indent=4)
                break
    
    ############################################################
    # 2) Standardize the tags that exist into a uniform format #
    ############################################################
    #print("2: Checking JSON keys")

    #print("Checking software name...")
    # Check 'Software'
    for software_error in SOFTWARE_ALIASES:
        if software_error in data:
            data['Software'] = data.pop(software_error)
            #print("Software name fixed!")      

    #print("Checking description...")
    # Check 'AI Description'
    for description_error in DESCRIPTION_ALIASES:
        if description_error in data.keys():
            data['AI Description'] = data.pop(description_error)
            #print("Overview name fixed!")

    #print("Checking core features...")
    # Check 'Core Features'
    for features_error in FEATURES_ALIASES:
        if features_error in data:
            data['Core Features'] = data.pop(features_error)
            #print("Features fixed!")

    #print("Checking general tags...")
    # Check 'General Tags'
    for tags_error in GEN_TAG_ALIASES:
        if tags_error in data:
            data['General Tags'] = data.pop(tags_error)
            #print("General tags fixed!")
    
    # Capitalize tags for better searching
    count = 0
    for general_tag in data['General Tags']:
        general_tag = general_tag.title()
        data['General Tags'][count] = general_tag
        count = count + 1

    # Check for 'Additional Tags'
    # These tend to get nested, but we want them loose to display them more easily in the table
    # If a particular one doesn't exist, create it as a blank field
    
    # Remove tags from 'Additional Tags' nest
    #print("Checking additional tags...")
    for additional_error in ADD_TAG_ALIASES:
        #print(aError)
        if additional_error in data:
            for tag in ADD_TAGS_TO_FIX:
                if tag in data[additional_error]:
                    data[tag] = data[additional_error][tag] 
                    data[additional_error].pop(tag)
                else:
                    data[tag] = ""
            data.pop(additional_error)
           
    # Sanitize tag names and contents
    for tag in ADD_TAGS_TO_FIX:
        # Check for missing or null values, which will break things later on
        if tag not in data or data[tag] is None:
            data[tag] = ""
        # Break lists into strings
        if tag in data:
            match tag:
                case 'software_type':
                    if data['Software Type'] is None:
                        data['Software Type'] = data.pop('software_type')
                    else:
                        data.pop('software_type')
                        # This is done in each case to preserve formatting
                        # Purely for visual clarity to the reader
                        # Easier to tell if data was sanitized properly
                        data['Software Type'] = data.pop('Software Type')
                
                case 'software_class':
                    if data['Software Class'] is None:
                        data['Software Class'] = data.pop('software_class')
                    else:
                        data.pop('software_class')
                        data['Software Class'] = data.pop('Software Class')
                
                case 'research_field':
                    if data['Research Field'] is None:
                        data['Research Field'] = data.pop('research_field')
                    else:
                        data.pop('research_field')
                        data['Research Field'] = data.pop('Research Field')
                
                case 'field_of_science':
                    if 'Research Field' not in data or data['Research Field'] is None:
                            data['Research Field'] = data.pop('field_of_science')
                    else:
                        data.pop('field_of_science')
                        data['Research Field'] = data.pop('Research Field')
                
                case 'research_discipline':
                    if data['Research Discipline'] is None:
                        data['Research Discipline'] = data.pop('research_discipline')
                    else:
                        data.pop('research_discipline')
                        data['Research Discipline'] = data.pop('Research Discipline')
               
                case 'research_area':
                    if data['Research Area'] is None:
                        data['Research Area'] = data.pop('research_area')
                    else:
                        data.pop('research_area')
                        data['Research Area'] = data.pop('Research Area')            

    # Turn lists into strings, and do basic text formatting on them
    for element in data:
        if isinstance(data[element], list):
            list_str = ""
            for str in data[element]:
                if list_str == "":
                    list_str = str
                else:
                    list_str = list_str + ", " + str
                data[element] = list_str.title()

        # Capitalize known/common acronyms for professionalism
        for acronym in COMMON_ACRONYMS_DICT:
            if acronym in data[element]:
                data[element] = data[element].replace(acronym, COMMON_ACRONYMS_DICT[acronym])

        # Replace 'And' in anything but software names and descriptions
        if element not in SOFTWARE_ALIASES or element not in DESCRIPTION_ALIASES:
            if "And" in data[element]:
                data[element] = data[element].replace("And", "&")
            
    # Save updated JSON file
    with open(file, 'w') as infile:
        json.dump(data, infile, indent=4)
    #print("Formatting complete!")