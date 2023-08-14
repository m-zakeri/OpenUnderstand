import oudb.api as und

from oudb.fill import fill
from understand.main import runner
from os import path, getcwd
from extract_class_api import ExtractClassAPI

# Clone projects

# sp = SourceProvider()
# sp.start_clone_projects("Source_id_0")
# sp.start_clone_projects("Source_id_1")
# sp.start_clone_projects("Source_id_2")
# sp.start_clone_projects("Source_id_3")

# create db for projects

# db = und.create_db(
#     dbname="xerces2-j.oudb",
#     project_dir="/home/y/Desktop/iust/Openundertand_testing_api/projects_bench/xerces2-j",
# )
# fill(udb_path=path.join(getcwd(), "../xerces2-j.oudb"))
# _db = und.open(dbname="xerces2-j.oudb")
# runner(
#     path_project="/home/y/Desktop/iust/Openundertand_testing_api/projects_bench/xerces2-j"
# )
# classes = _db.ents("Type Class ~Unknown ~Anonymous")
# print(len(classes))


# und.create_db(
#     dbname="/home/y/Desktop/iust/Openundertand_testing_api/udb_projects/xerces2-j.und",
#     project_dir="/home/y/Desktop/iust/Openundertand_testing_api/projects_bench/xerces2-j",
# )
#
# # test Extract class
#
# eca = ExtractClassAPI(udb_path="xerces2-j.oudb")
#
# eca.get_source_class_map()

import argparse
import configparser

def save_config(repo_address, db_address, engine_address, log_address):
    config = configparser.ConfigParser()
    config['DEFAULT'] = {'repo_address': repo_address, 'db_address': db_address, 'engine_address': engine_address, 'log_address': log_address}
    with open('config.ini', 'w') as configfile:
        config.write(configfile)

def parse_arguments():
    parser = argparse.ArgumentParser(description='CLI for setting configuration options')

    parser.add_argument('-r', '--repo_address', type=str, help='Repository address')
    parser.add_argument('-udb', '--db_address', type=str, help='Database SQLite address')
    parser.add_argument('-e', '--engine_address', type=str, help='Engine address (C++ or Python)')
    parser.add_argument('-l', '--log_address', type=str, help='App log address')

    args = parser.parse_args()

    repo_address = args.repo_address if args.repo_address else 'default_repo'
    db_address = args.db_address if args.db_address else 'default_db'
    engine_address = args.engine_address if args.engine_address else 'default_engine'
    log_address = args.log_address if args.log_address else 'default_log'

    save_config(repo_address, db_address, engine_address, log_address)

if __name__ == '__main__':
    parse_arguments()