#!/bin/bash --login
cd sds 
conda activate SDS_ENV
python reset_database.py -c_d container_data/ -csv_f aaa.csv -s_d spider_data/ 
which python
which flask
flask run
