def custom_lmod_parser(name: str, versions: list[str], software_info: list[dict]):
    """
    Define your custom parsing function here.
    Change the values of name and versions as necessary
    Must return all three items

    Args:
        name (str): software name identified by the parser
        version (list): list of versions identified by the parser
        software_info (dict): list of dictionaries containg 'name', 'versions', and 'discription'
            of all software in current file

    Return:
        name (str): software name identified by custom parser
        version (list): list of versions identified by the custom parser
        software_info (dict): list of dictionaries containg 'name', 'versions', and 'discription'
            of all software in current file (optionally modifed by the custom parser)
    """
    # pp(name)
    # pp(versions)
    # pp(software_info)
    return name, versions, software_info