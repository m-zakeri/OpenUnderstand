import os.path
from os import path, getcwd
import argparse
import configparser


def save_config(
    repo_address: str,
    db_address: str,
    db_name: str,
    log_address: str,
    engine_core: str = "Python",
) -> None:
    config = configparser.ConfigParser()
    config.read("config.ini")

    # Update or create the 'DEFAULT' section
    if not config.has_section("Config"):
        config.add_section("Config")

    config.set("Config", "repo_address", repo_address)
    config.set("Config", "db_address", db_address)
    config.set("Config", "db_name", db_name)
    config.set("Config", "engine_core", engine_core)

    # Update or create the 'Logging' section
    if not config.has_section("Logging"):
        config.add_section("Logging")

    config.set("Logging", "filename", log_address)
    config.set("Logging", "level", "DEBUG")

    with open("config.ini", "w") as configfile:
        config.write(configfile)
        configfile.close()


def parse_arguments() -> None:
    parser = argparse.ArgumentParser(
        description="CLI for setting configuration options"
    )
    parser.add_argument(
        "-r", "--repo_address", type=str, help="Repository address of project"
    )
    parser.add_argument(
        "-dba", "--db_address", type=str, help="Database SQLite address"
    )
    parser.add_argument("-dbn", "--db_name", type=str, help="Database SQLite name file")
    parser.add_argument(
        "-e",
        "--engine_core",
        type=str,
        help="Engine for parser usage (C++ or Python)",
    )
    parser.add_argument(
        "-l", "--log_address", type=str, help="App log name address file"
    )
    args = parser.parse_args()
    repo_address = (
        args.repo_address if args.repo_address else path.join(getcwd(), "project")
    )
    db_address = args.db_address if args.db_address else path.join(getcwd())
    db_name = args.db_name if args.db_name else "default.oudb"
    engine_core = args.engine_core if args.engine_core else "Python"
    log_address = (
        args.log_address if args.log_address else path.join(getcwd(), "app.log")
    )
    save_config(
        repo_address=repo_address,
        db_address=db_address,
        db_name=db_name,
        engine_core=engine_core,
        log_address=log_address,
    )
    start_parsing()


def start_parsing(
    repo_address: str = None,
    db_address: str = None,
    db_name: str = None,
    engine_core: str = None,
    log_address: str = None,
):
    from openunderstand.oudb.api import create_db
    from openunderstand.oudb.fill import fill
    from openunderstand.ounderstand.runner import runner
    from openunderstand.ounderstand import symbol_table
    from openunderstand.oudb.models import (drop_shadowed_use_refs, drop_orphan_placeholders,
                                            drop_external_inverse_refs,
                                        drop_nonvariable_deref_refs,
                                            merge_placeholder_entities,
                                            relabel_nondynamic_calls)

    if (
        repo_address is not None
        and db_address is not None
        and db_name is not None
        and engine_core is not None
        and log_address is not None
    ):
        save_config(
            repo_address=repo_address,
            db_address=db_address,
            db_name=db_name,
            engine_core=engine_core,
            log_address=log_address,
        )
    try:
        config = configparser.ConfigParser()
        config.read("config.ini")
    except Exception as e:
        raise Exception(
            "please init all input values of start_parsing() function or run command line cli openunderstand \n - >> this error occur because of config.ini not exist"
        )
    create_db(
        dbname=config["Config"]["db_name"],
        project_dir=config["Config"]["repo_address"],
        db_path=config["Config"]["db_address"],
    )
    fill(udb_path=config["Config"]["db_address"])
    # Index every declaration first: the per-file passes cannot resolve a
    # name declared in another file without it.
    symbol_table.build(config["Config"]["repo_address"])

    runner(path_project=config["Config"]["repo_address"])

    # Passes run in a fixed order, and several create placeholder entities
    # before the define pass has declared the real ones. Fold them together
    # once everything has been written.
    merge_placeholder_entities()
    relabel_nondynamic_calls()
    # After merging, so the endpoints a Use shares with its more specific
    # variant have already been folded onto the same entity rows.
    drop_nonvariable_deref_refs()
    drop_shadowed_use_refs()
    drop_external_inverse_refs()
    drop_orphan_placeholders()


if __name__ == "__main__":
    parse_arguments()
