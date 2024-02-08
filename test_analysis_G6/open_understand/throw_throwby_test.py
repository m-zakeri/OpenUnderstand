import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(script_dir, "..", os.pardir))
parent_dir_openunderstand = os.path.abspath(
    os.path.join(script_dir, "..", os.pardir, "openunderstand")
)
sys.path.append(parent_dir)
sys.path.append(parent_dir_openunderstand)

# Now import the 'openunderstand' module
import openunderstand.ounderstand as und
db = und.open("/path/to/openunderstand/database.udb")
dbents = db.ents()

print("-------------open Understand-------------")
print("-------------throw-------------")
counter = 0
refs_dict = {}
for i in dbents:
    for ref in i.refs("Throw"):
        counter += 1
        if (filename := str(ref.file())) in refs_dict:
            refs_dict[filename].update({ref.line(): ref.ent().longname()})
        else:
            refs_dict[filename] = {ref.line(): ref.ent().longname()}

print(counter)
for j, i in enumerate(sorted(refs_dict), 1):
    print(f'{j:2d})', i, len(refs_file := refs_dict[i]))
    for k, v in refs_file.items():
        print(f"\t{k:4d}: {v}")
    print("-------------")

print("-------------throwBy-------------")
counter = 0
refs_dict = {}
for i in dbents:
    for ref in i.refs("ThrowBy"):
        counter += 1
        if (filename := str(ref.file())) in refs_dict:
            refs_dict[filename].update({ref.line(): ref.ent().longname()})
        else:
            refs_dict[filename] = {ref.line(): ref.ent().longname()}

print(counter)
for j, i in enumerate(sorted(refs_dict), 1):
    print(f'{j:2d})', i, len(refs_file := refs_dict[i]))
    for k, v in refs_file.items():
        print(f"\t{k:4d}: {v}")
    print("-------------")
