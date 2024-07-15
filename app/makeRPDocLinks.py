# Hard-coded links to RP-specific Software Documentation
RP_URLS = {
    'Aces':'https://hprc.tamu.edu/software/aces/',
    'Anvil': 'https://www.rcac.purdue.edu/software/',
    'Bridges-2': 'https://www.psc.edu/resources/software/',
    'DARWIN': 'https://docs.hpc.udel.edu/software/',
    'Delta': 'https://docs.ncsa.illinois.edu/systems/delta/en/latest/user_guide/software.html',
    'Expanse':'https://www.sdsc.edu/support/user_guides/expanse.html#modules',
    'Faster':'https://hprc.tamu.edu/software/faster/',
    'Jetstream2':'',
    'Kyric':'',
    'Ookami':'https://www.stonybrook.edu/commcms/ookami/support/faq/software_on_ookami',
    'Rockfish':'',
    'Stampede-2':'https://tacc.utexas.edu/use-tacc/software-list/',
    'Stampede3':'https://tacc.utexas.edu/use-tacc/software-list/',
    'Ranch':'https://tacc.utexas.edu/use-tacc/software-list/',
    'OSG':'',
    'OSN':''
}
# Some RPs generate specific links to individual software in their documentation.
# Here, for the RPs that do this, we're using an algorithm to point to their
#   specific software pages.

#################################################################
#   create_full_doc_url                                         #
#       Generates RP-specific documentation links for the table #
#       Args:                                                   #
#           software_name: software as it appears on the table  #
#           rp_names: list of RPs with the software installed   #
#       Return:                                                 #
#           combined_urls: string of formatted RP URLs          #
#################################################################
def create_full_doc_url(software_name, rp_names):
    has_individual_software_page = ['Anvil','Bridges-2','DARWIN']   # RPs that have specific links per software
    rp_list = rp_names.split(',')                                     # For software installed on multiple systems,
                                                                    #   split the RPs into a list for processing

    urls=[]
    for rp in rp_list:
        rp_name = rp.strip()                 # Strip off any whitespace 
        rp_url = RP_URLS.get(rp_name)         # Grab URL from rp_urls dictionary based on rpName

        # For software with specific links
        if rp_name in has_individual_software_page:        
            full_url = f"{rp_name}: {rp_url}{software_name.lower()}"  # fullURL = rpName: rpUrl/softwareName
            
            # Extra Code for DARWIN links, which aren't constructed normally
            if rp_name == 'DARWIN':
                full_url = f"{full_url}/{software_name.lower()}"     # fullURL = rpName: rpUrl/softwareName/softwareName
        
        # For software from RPs with only generic documentation
        elif rp_url:
            full_url = f"{rp_name}: {rp_url}"
        
        # For software from RPs with no documentation at all
        else:
            full_url=''
        
        # Combine URLs across multiple RPs
        if full_url:
            urls.append(full_url)

    # Format URLs so each is on a separate line in the table cell
    combined_urls = ' \n'.join(urls)
    return combined_urls