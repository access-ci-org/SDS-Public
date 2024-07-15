import json
import glob
import os
import pandas as pd
import numpy as np

from app.makeRPDocLinks import create_full_doc_url
from app.parseVersionInfo import add_version_info_to_table
from app.parseJSONInfo import json_sanitizer

CURATED_INPUT_DIRECTORY = './data/CSV/ACCESS_Software.csv'
CURATED_OUTPUT_DIRECTORY = './data/CSV/staticTable.csv'

GENERATED_INPUT_DIRECTORY = "./data/JSON"
GENERATED_OUTPUT_DIRECTORY = './data/CSV/generatedTable.csv'

FINAL_OUTPUT_DIRECTORY = './data/CSV/softwareTable.csv'

JSON_KEYS = [
    'Software', 
    'AI Description', 
    'Core Features', 
    'General Tags', 
    'Software Type', 
    'Software Class',
    'Research Field',
    'Research Area',
    'Research Discipline'
    ]

COLUMN_ORDER = [
    'Software', 'RP Name', 'Software Type', 'Software Class', 'Research Field',
    'Research Area', 'Research Discipline', 'Software Description', 
    'Core Features', 'General Tags', "Software's Web Page", 
    'Software Documentation', 'Example Software Use', 'RP Software Documentation', 
    'Version Info', 'AI Description', 'Example Use'
    ]

MERGE_COLUMNS = [
    'Software Type', 'Software Class', 'Research Area', 'Research Discipline']

DEFINE_AI_COLUMNS = [
    'Software Type', 'Software Class', 'Research Field', 'Research Area', 'Research Discipline',
    'Core Features', 'General Tags', 'AI Description', 'Example Use'
]
#########################################################################
#   create_software_table                                               #
#       Creates a combined DataFrame from our curated information and   # 
#       our AI-generated information into a DataFrame ready for HTML    #
#       Functions                                                       #
#           create_curated_table(): Loads curated data into DataFrame   #
#           create_generated_table(): Loads AI data into DataFrame      #
#       Return:                                                         #
#           df: Pandas DataFrame of completed combined Table            #
#########################################################################
def create_software_table():
    # Read cached tables if they exist
    # Otherwise recreate as little as necessary
    try:
        merged_DF = pd.read_csv(FINAL_OUTPUT_DIRECTORY)
        print("Software table found!")
    except:
        print("Software table not found. Creating...")
        try:
            curated_table_DF = pd.read_csv(CURATED_OUTPUT_DIRECTORY, na_filter=False)
            print("Curated Table found!")
        except:
            curated_table_DF = create_curated_table()
            print("Static table not found. Creating...")
        try:
            generated_table_DF = pd.read_csv(GENERATED_OUTPUT_DIRECTORY, na_filter=False)
            print("AI Generated table found!")
        except:
            generated_table_DF = create_generated_table('f')
            print("AI Generated table not found. Creating...")

        # Merge tables by index
        merged_DF = curated_table_DF.merge(generated_table_DF, how='left', on='Software', suffixes=('_static', '_generated'))
        merged_DF = merged_DF.replace('', np.nan)
        
        # Combine matching columns, prioritizing the AI Generated information
        for column in MERGE_COLUMNS:
            merged_DF[column] = merged_DF[column + '_generated'].combine_first(merged_DF[column + '_static'])
        
        # Drop the unmerged versions of columns
        merged_DF = merged_DF.drop(columns=[column + '_static' for column in MERGE_COLUMNS]
                                  + [column + '_generated' for column in MERGE_COLUMNS] )
        merged_DF = merged_DF.replace(np.nan, '')
        
        # Add 'Example Use' modals to table
        merged_DF.insert(16, 'Example Use', '')

        # Finalize table
        merged_DF = merged_DF[COLUMN_ORDER]
        for col in merged_DF.columns:
            if col in DEFINE_AI_COLUMNS:
                merged_DF.rename(columns={col : '✨' + col}, inplace=True)

        # Cache the table for future use
        merged_DF.to_csv(FINAL_OUTPUT_DIRECTORY,index=False)


    return merged_DF


#########################################################################
#   create_curated_table                                                #
#       Generate a DataFrame from our manually-curated CSV data         #
#       Functions                                                       #
#           create_full_doc_URL: Populate RP Documentation Cells        #
#           add_version_info_to_table: Add Version info into DataFrame  #
#       Return:                                                         #
#           df: Pandas DataFrame of completed curated Table             #
#########################################################################
def create_curated_table():
    df = pd.read_csv(CURATED_INPUT_DIRECTORY,na_filter=False)  # CSV generated from Google Sheets

    # Ensure uniform capitalization across cells
    df['RP Name'] = df['RP Name'].str.title()
    df['Software Type'] = df['Software Type'].str.title()
    df['Software Class'] = df['Software Class'].str.title()
    df['Research Area'] = df['Research Area'].str.title()
    df['Research Discipline'] = df['Research Discipline'].str.title()

    # Ensure DARWIN is always capitalized
    df['RP Name'] = df['RP Name'].str.replace('darwin', 'DARWIN')

    # Table Column Formatting
    df.rename(columns={'Software Documentation/Link' : 'Software Documentation'}, inplace=True)
    df.rename(columns={'Example Software Use (link)' : 'Example Software Use'}, inplace=True)

    # Description Source Formatting
    df['Software Description'] = df['Software Description'].str.replace(
        'Description Source:', '\nDescription Source: ')

    # Make Example Links on separate lines
    df['Example Software Use'] = df['Example Software Use'].str.replace(' , ', ' \n')

    # Populate 'RP Software Documentation' Field
    df['RP Software Documentation'] = df.apply(
        lambda row: create_full_doc_url(row['Software'], row['RP Name']), axis=1)

    # This really needs to be fixed. If we don't want these columns, get rid of them. 
    # If we do, populate them.
    empty_columns = ['Area-specific Examples', 'Containerized Version of Software',
                     'RP Documentations for Software', 'Pathing']
    df.drop(empty_columns,axis=1,inplace=True)
    
    # Add Version Info to DataFrame
    df = add_version_info_to_table(df)
    df['Version Info'] = df['Version Info'].str.title()

    # Convert DataFrame back to CSV
    df.to_csv(CURATED_OUTPUT_DIRECTORY,index=False)
    
    # Export DataFrame to App
    return(df)


#################################################################
#   create_generated_table                                      #
#       Prepares a DataFrame from a directory of JSON files     #   
#       generated by an AI to fill holes in our curated table   # 
#       Functions                                               #
#           json_sanitizer: Ensures JSON files are in a         # 
#               consistent format that eases processing         #
#       Parameters:
#           override:
#       Return:                                                 #
#           df: Pandas DataFrame of completed generated table   #
#################################################################
def create_generated_table(override):
    software_dict = {}
    # Stage the JSON Directory 
    for file in glob.glob(os.path.join(GENERATED_INPUT_DIRECTORY, '*.json')):
        # Filter out improperly created or fragmented JSON objects
        # These are usually due to some random text we added to filter them out intentionally
        # This way they don't break the entire script
        try:
            # If the JSON is correctly formatted but needs to be processed
            # Use this flag to force the sanitizer to run
            if override.lower() == 't':
                force_run = True
            else:
                force_run = False
            # Check if JSON has been formatted properly  
            for key in JSON_KEYS:
                with open(file, 'r') as infile:
                    data = json.load(infile)
                if key not in data.keys() or force_run:
                    json_sanitizer(file)
                    force_run = False                
        except:
            print("Error reading: " + file)
            continue

        # Stage JSON data to be added to dictionary
        software_name = data['Software'].lower()
        
        # Additional overhead for specific file(s)
        # Thanks Ookami
        if software_name == '7-zip':     
            software_name = '7z'
            data['Software'] = '7z'
        
        # Add JSON data to dictionary
        software_dict[software_name] = data

    # Alphabetizes the dictionary, mostly for user friendly CSV generation
    # Easier to make sure the CSV is doing what we want this way
    sorted_dict = dict(sorted(software_dict.items()))

    # Create the DataFrame
    df = pd.DataFrame.from_dict(sorted_dict, orient='index', columns=['Software', 
        'AI Description', 'Core Features', 'General Tags', 'Software Type', 
        'Software Class', 'Research Field', 'Research Area', 'Research Discipline'], )
    # Ensure uniformity in Software names, since this will be the index
    df['Software'] = df['Software'].str.lower()
    df.set_index('Software', inplace=True)
    # Generate a CSV to 'cache' this information
    df.to_csv(GENERATED_OUTPUT_DIRECTORY)

    return df