import sys
import os
from os import getcwd
from os.path import join

from collections import Counter

sys.path.append(join(getcwd(), "openunderstand"))
sys.path.append(join(getcwd(), "openunderstand", "oudb"))
sys.path.append(join(getcwd(), "openunderstand", "utils"))
import openunderstand.ounderstand as und
#_db = und.open("C:\\Users\\black\\OpenUnderstand\\JSON.udb")#dbents = _db.ents()
os.add_dll_directory("C:\\Program Files\\Scitools\\bin\\pc-win64")
sys.path.append("C:\\Program Files\\Scitools\\bin\\pc-win64\\Python")
def udb_open(address: str, refrence: str) -> (dict[str, dict], int):
    import understand
    db = understand.open(address)
    dbents = db.ents()
    print(f"-------------understand-------------")
    counter = 0
    refs_dict = {}
    for ents in dbents:
        for ref in ents.refs(refrence):
            counter += 1
            if (filename := ref.file().longname()) in refs_dict:
                refs_dict[filename].update({ref.line(): ref.ent().longname()})
            else:
                refs_dict[filename] = {ref.line(): ref.ent().longname()}

    return refs_dict, counter

def oudb_open(address: str, refrence: str) -> (dict[str, dict], int):
    _db = und.open(address)
    dbents = _db.ents()
    print(f"-------------open understand-------------")
    counter = 0
    refs_dict = {}
    for ents in dbents:
        for ref in ents.refs(refrence):
            counter += 1
            if (filename := ref.file().longname()) in refs_dict:
                refs_dict[filename].update({ref.line(): ref.ent().longname()})
            else:
                refs_dict[filename] = {ref.line(): ref.ent().longname()}

    return refs_dict, counter

if __name__ == "__main__":
    refrerence = "Declare"
    understand_refs, understand_counter = udb_open(
        address="C:\\Users\\USER\\OpenUnderstand\\benchmark\\calculator_app\\calculator_app.udb",
        refrence=refrerence,    )
    openund_refs, openund_counter = oudb_open(
        address="C:\\Users\\USER\\OpenUnderstand\\test_analysis\\openunderstand\\mydb.udb",
        refrence=refrerence,    )
    print(f"openund_counter: {openund_counter}")
    print(f"understand_counter: {understand_counter}")
    print("-------------")
    for i in understand_refs:
        if (un := understand_refs.get(i)) != (op := openund_refs.get(i)):
            print(f"File: {i}")
            print(f"openund: {op}")
            print(f"understand: {un}")
            print("-------------")