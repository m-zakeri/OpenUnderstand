# OpenUnderstand
![OpenUnderstand Logo](docs/figs/OpenUnderstand_Logo.png)

An open-source implementation of Understand API in Python.

## Useful links

* OpenUnderstand Documentation Website: [www.m-zakeri.github.io/OpenUnderstand.](https://m-zakeri.github.io/OpenUnderstand/)

# Configuration Setup Script

This script allows you to set up and save configuration options using command-line arguments.

## Prerequisites

- Python 3.x

## Usage

1. Open a terminal or command prompt.

2. Run the script with the following command:

## Options

- `-r`, `--repo_address`: Address of the repository (Optional)
- `-udb`, `--db_address`: Address of the SQLite database (Optional)
- `-e`, `--engine_address`: Use the engine (C++ or Python) (Optional)
- `-l`, `--log_address`: Address of the log file (Optional)

3. Provide the desired values for the options you want to set. If any option is not provided, default values will be used.

4. Once the script finishes, a `config.ini` file will be generated with the provided or default values.


*************************************************************
To set up the configuration options with specific addresses, run the following command:

    python openunderstand.py [-r REPO_ADDRESS] [-dba DB_ADDRESS] [-dbn DB_NAME] [-e ENGINE_CORE] [-l LOG_ADDRESS]
 
## Arguments
* -r, --repo_address: Repository address of the project.
* -dba, --db_address: Database SQLite address.
* -dbn, --db_name: Database SQLite name file.
* -e, --engine_core: Engine for parser usage (C++ or Python).
* -l, --log_address: App log name address file.



This will save the provided addresses in the `config.ini` file.

If you don't provide any options, default values will be used for all addresses.

    python openunderstand.py


This will generate a `config.ini` file with default values.

#### [DEFAULT]
* repo_address: default_repo
* db_address: default_db
* db_name: default_db_name
* engine_address: default_engine
* log_address: default_log

Feel free to modify the default values directly in the `config.ini` file.
****************************************
## Default Values
If an argument is not provided, the following default values will be used:

**repo_address:** Current working directory with "project" appended.

**db_address:** Current working directory.

**db_name:** "default.oudb".

**engine_core:** "Python".

**log_address:** Current working directory with "app.log" appended.

 
### Examples

1.Set the repository address to "/path/to/repo":
    
    python openunderstand.py -r /path/to/repo

2.Set the database address to "/path/to/db", the database name to "database.oudb", and the engine core to "C++":

    python cli.py -dba /path/to/db -dbn database.oudb -e C++

3.Set the log address to "/path/to/log/file.log":

    python cli.py -l /path/to/log/file.log
