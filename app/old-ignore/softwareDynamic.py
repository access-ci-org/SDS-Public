import pandas as pd
import json
import os

directory_path = "./dynamicSearch/software_all_json"
def fix_files(): #used to remove chatgpt fluff from json files
    for filename_ in os.listdir(directory_path):
        filename = directory_path+'/'+filename_
        with open(filename, 'r') as file:
            text = file.readlines()
            if (text[0].startswith('`')):
                del text[0]  # Remove the first line
                del text[-1]  # Remove the last line

        with open(filename, 'w') as file:  # Open the file in 'w' mode to clear it
            file.writelines(text)
#fix_files()

def txt_to_json():
    for filename in os.listdir(directory_path):        
        if filename.endswith('.txt'):
            os.rename(directory_path+'/'+filename, directory_path+'/'+filename[:-4]+'.json')

def extract_key_value(data, key_columns):
    """
    Extracts a value based on a list of potential key columns from the given data.
    Returns the extracted value and the cleaned data without the extracted key.
    """
    extracted_value = None

    # Check for software name in the provided columns
    for key in key_columns:
        if key in data:
            extracted_value = data.pop(key)
            break

    return extracted_value, data

def read_and_transform_json(file_path, filename):
    try:
        with open(file_path, 'r') as file:
            original_data = json.load(file)

        data = {}
        software_name_value = None

        # Check for nested structure and extract if necessary
        if isinstance(original_data, dict) and len(original_data.items()) == 1:
            software_name_value, nested_data = next(iter(original_data.items()))
            data = nested_data
            data['software name'] = software_name_value
        else:
            data = original_data

        # Flatten additional_tags and convert list values into comma-separated strings
        flattened_data = {}

        aTags_columns = ['additionalTags', 'additional tags', 'additional_tags']

        for key, value in data.items():
            if key in aTags_columns and isinstance(value, dict):
                for inner_key, inner_value in value.items():
                    flattened_data[inner_key] = ', '.join(inner_value) if isinstance(inner_value, list) else inner_value
            elif isinstance(value, list):
                flattened_data[key] = ', '.join(value)
            else:
                flattened_data[key] = value

        attributes_columns = {
            'software name': ['software_name', 'tool', 'software', 'softwareName', 'software name', 'Software Name'],
            'overview': ['comprehensive_overview', 'overview', 'comprehensiveOverview', 'comprehensive overview', 'Comprehensive Overview'],
            'core features': ['core_features', 'coreFeatures', 'core features', 'Core Features'],
            'tags': ['general_tags', 'general tags', 'generalTags', 'General Tags'],
            'additional tags': ['additionalTags', 'additional tags', 'additional_tags', 'Additional Tags', 'specific_tags'],
            'research area': ['research_area_tags', 'research_area', 'research area', 'researchArea', 'Research Area'],
            'research discipline': ['discipline_tags', 'research_discipline', 'research discipline', 'researchDiscipline', 'discipline', 'Research Discipline', 'specific_discipline', 'research_discipline_tags'],
            'software type': ['software_type_tags', 'software_type', 'softwareType', 'software type', 'Software Type'],
            'software class': ['software_class_tags', 'software_class', 'softwareClass', 'software class', 'Software Class'],
            'research field': ['field_of_science_tags', 'field_of_science', 'specific_field_of_science', 'specific_field', 'Field of Science', 'field of science', 'technology_field', 'research_field', 'Scientific Field', 'subfield_of_science']
        }

        for attribute, columns in attributes_columns.items():
            value, flattened_data = extract_key_value(flattened_data,columns)

            if value:
                if isinstance(value, dict):
                    flattened_data.update(value)
                else:
                    flattened_data[attribute] = value

        for attribute, columns in attributes_columns.items():
            for column in columns:

                if column in flattened_data.keys() and column is not attribute:
                    temp = flattened_data[column]
                    flattened_data[attribute] = flattened_data[attribute] + ', ' + temp
                    flattened_data.pop(column)

        flattened_data['software name'] = filename[:-5]

        return flattened_data
    except json.JSONDecodeError:
        print(f"Skipping file due to JSONDecodeError: {file_path}")
        return None

def generalized_combine_dfs(df, merge_dfs):
    for merge_df, merge_key in merge_dfs:
        # Create temporary columns for case-insensitive comparison
        df_temp_key = f"{merge_key}_temp"
        merge_df_temp_key = f"{merge_key}_temp"
        df[df_temp_key] = df[merge_key].str.lower()
        merge_df[merge_df_temp_key] = merge_df[merge_key].str.lower()
        
        # Perform the merge
        df = pd.merge(df, merge_df, left_on=df_temp_key, right_on=merge_df_temp_key, how='left', suffixes=('', '_y'))
        
        # Cleanup: remove temporary and duplicate columns
        df.drop(columns=[df_temp_key, merge_df_temp_key] + [col for col in df.columns if col.endswith('_y')], inplace=True)
    return df


def combine_dfs(df, rpAndSoftware, linksOnly):

    #move column 'software name' to the beginning
    df = df[['software name']+[col for col in df.columns if col != 'software name']]

    #move column 'overview' to be second from the left
    col= df.pop('overview')
    df.insert(1,col.name,col)

    # create temp columns for case-insensitive comparison
    df['software_name_temp'] = df['software name'].str.lower()
    rpAndSoftware['software_name_temp'] =rpAndSoftware['software name'].str.lower()

    merged_df = pd.merge(df, rpAndSoftware, left_on='software_name_temp', right_on='software_name_temp', how='left')

    # cleanup after merge
    merged_df.drop('software name_y', axis=1, inplace=True)
    merged_df.rename(columns={'software name_x': 'software name'}, inplace=True)

    linksOnly['software_name_temp'] = linksOnly['software name'].str.lower()
    merged_df = pd.merge(merged_df,linksOnly, left_on='software_name_temp', right_on='software_name_temp', how='left')

    # cleanup after merge
    merged_df.drop('software name_y', axis=1, inplace=True)
    merged_df.rename(columns={'software name_x': 'software name'}, inplace=True)

    # drop the temp columns after merge
    merged_df.drop(['software_name_temp'], axis=1,inplace=True)


    col= merged_df.pop('RP Name')
    merged_df.insert(1,col.name,col)

    return(merged_df)


directory_path = "./dynamicSearch/software_all_json"
data_dicts=[]
def make_df():
    for filename in os.listdir(directory_path):
        if filename.endswith('.json'):
            file_path = os.path.join(directory_path, filename)
            data = read_and_transform_json(file_path, filename)
            if data is not None:
                data_dicts.append(data)

    df = pd.DataFrame(data_dicts)
    df.fillna('',inplace=True)

    rpAndSoftware = pd.read_csv('./dynamicSearch/rp-software-map.csv')
    rpAndSoftware.rename(columns={'Software': 'software name'}, inplace=True)

    linksOnly = pd.read_csv('./dynamicSearch/softwareLinksOnly.csv')
    linksOnly.rename(columns={'Software': 'software name'}, inplace=True)

    merge_dfs=[(rpAndSoftware,'software name'),(linksOnly,'software name')]
    df = generalized_combine_dfs(df, merge_dfs)

    column_order =['software name', 'RP Name']
    rest_of_columns = [col for col in df.columns if col not in column_order]
    final_order = column_order + rest_of_columns
    df = df[final_order]

    empty_columns = ['additional tags', 'other_tags', 'other']
    
    df.drop(empty_columns,axis=1,inplace=True)

    df.rename(columns={'overview':'Description'},inplace=True)
    
    return df

df = make_df()

output_file_path = './dynamicSearch/combined_data.csv'
df.to_csv(output_file_path,index=False)