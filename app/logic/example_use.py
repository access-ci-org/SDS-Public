from pathlib import Path
import re


#########################################################################
#   find_example_use                                                    #
#       Search for and retrieve example usage of a specified software   #
#       from text files in a given directory.                           #
#   parameters:                                                         #
#       software_name {str}: Name of the software to search for         #
#       example_use_dir {str}: Directory path to search for example     #
#           usage files (default: 'data/exampleUse')                    #
#   return:                                                             #
#       {str or bool}: Content of the first matching file if found,     #
#           False if an error occurs or no match is found               #
#   notes:                                                              #
#       - Searches for case-insensitive matches in file names           #
#       - Returns the entire content of the first matching file         #
#########################################################################
def find_example_use(software_name, example_use_dir = 'data/exampleUse'):

    normalized_software_name = re.escape(software_name).lower()
    
    # software name pattern to search for in the files
    pattern = re.compile(normalized_software_name, re.IGNORECASE)   

    example_use_path = Path.cwd() / example_use_dir

    try:
        for file_path in example_use_path.iterdir():
            if pattern.search(file_path.stem):  # get only the file name (with extensions like .txt)
                with open(file_path, 'r') as file:
                    example_use = file.read()
                    return example_use

    except Exception as e:
        print(e)
        return False
        