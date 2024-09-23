from IPython.display import display
from dotenv import load_dotenv
from xdmod_data.warehouse import DataWarehouse
from pathlib import Path
from os.path import expanduser

def fetch_xdmod_data():
    xdmod_data_env_path = Path(expanduser('~/xdmod-data.env'))

    # Load xdmod-data.env into environment
    load_dotenv(xdmod_data_env_path, override=True)

    # Initialize XDMoD Warehouse
    dw = DataWarehouse('https://xdmod.access-ci.org')

    # Grab data
    with dw:
        data = dw.get_data(
            duration=('30 day'),
            realm='SUPREMM',
            metric='Number of Jobs Submitted',
            dimension='Application',
            dataset_type='timeseries',
        )

    # Display data
    display(data) # Data is a Pandas DataFrame
    data.to_csv('./data/CSV/xdmod.csv',index=True)



fetch_xdmod_data()