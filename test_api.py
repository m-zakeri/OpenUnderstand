import sys
from os import getcwd
from os.path import join
sys.path.append(join(getcwd(), "openunderstand"))
sys.path.append(join(getcwd(), "openunderstand", "oudb"))
sys.path.append(join(getcwd(), "openunderstand", "utils"))

import openunderstand.ounderstand as und

_db = und.open("D:\openunderstand2\OpenUnderstand\mydb.udb")

print(
    len(
        _db.ents("class")
       )
    )