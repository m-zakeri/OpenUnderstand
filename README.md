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

### Options

- `-r`, `--repo_address`: Address of the repository (Optional)
- `-udb`, `--db_address`: Address of the SQLite database (Optional)
- `-e`, `--engine_address`: Use the engine (C++ or Python) (Optional)
- `-l`, `--log_address`: Address of the log file (Optional)

3. Provide the desired values for the options you want to set. If any option is not provided, default values will be used.

4. Once the script finishes, a `config.ini` file will be generated with the provided or default values.

## Example

To set up the configuration options with specific addresses, run the following command:

#### python main.py -r repo_address -udb db_address -e engine_address -l log_address 

This will save the provided addresses in the `config.ini` file.

If you don't provide any options, default values will be used for all addresses.

#### python main.py

This will generate a `config.ini` file with default values.

#### [DEFAULT]
#### repo_address: default_repo
#### db_address: default_db
#### engine_address: default_engine
#### log_address: default_log

Feel free to modify the default values directly in the `config.ini` file.



