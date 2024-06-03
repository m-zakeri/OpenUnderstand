import sys
from os import getcwd
from os.path import join

sys.path.append(join(getcwd(), "openunderstand"))
sys.path.append(join(getcwd(), "openunderstand", "oudb"))
sys.path.append(join(getcwd(), "openunderstand", "utils"))
from openunderstand.ounderstand.openunderstand import *

# for codart
start_parsing(
    repo_address="/home/y/Desktop/desktop_2./OpenUnderstand/benchmark/JSON",
    db_address="/home/y/Desktop/desktop_2./OpenUnderstand/benchmark/JSON",
    db_name="mydb.udb",
    engine_core="Python3",
    log_address="/home/y/Desktop/desktop_2./OpenUnderstand/benchmark/JSON/a.log",
)
# for local
# start_parsing(
#     repo_address=join(getcwd(), "benchmark", "JSON"),
#     db_address=getcwd(),
#     db_name="mydb.udb",
#     engine_core="Python3",
#     log_address=join(getcwd(), "a.log"),
# )
