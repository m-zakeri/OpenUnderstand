import os
import sys

# Resolve project paths relative to this file so the script runs on any
# machine and in CI, instead of relying on hard-coded absolute paths.
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

sys.path.append(os.path.join(PROJECT_ROOT, "openunderstand"))
sys.path.append(os.path.join(PROJECT_ROOT, "openunderstand", "oudb"))
sys.path.append(os.path.join(PROJECT_ROOT, "openunderstand", "utils"))
sys.path.append(os.path.join(PROJECT_ROOT, "openunderstand", "metrics"))
import openunderstand.ounderstand as und

# Database path is resolved relative to the project root, replacing the
# previous hard-coded absolute path (/home/y/Desktop/...).
_db = und.open(os.path.join(PROJECT_ROOT, "mydb.udb"))

# und_all_results = {}
# for ent in _db.ents("Class"):
#     ent_name = ent.name()
#     print(ent.metric(["CountDeclMethodAll"]))
#     all_methods = ent.metric(["CountDeclMethodAll"]).get("CountDeclMethodAll", 0)
#     und_all_results[ent_name] = all_methods

und_all_results = {}
for ent in _db.ents("Class"):
    ent_name = ent.name()
    print(ent.metric(["CountDeclClassVariable"]))
    all_methods = ent.metric(["CountDeclClassVariable"]).get(
        "CountDeclClassVariable", 0
    )
    und_all_results[ent_name] = all_methods

print(und_all_results)
