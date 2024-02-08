import sys
import os

sys.path.insert(
    0,
    "/home/y/Downloads/Scientific.Toolworks.Understand.5.1.1023.Linux/Understand-5.1.1023-Linux-64bit/scitools/bin/linux64/Python",
)
os.environ[
    "LD_LIBRARY_PATH"
] = "/home/y/Downloads/Scientific.Toolworks.Understand.5.1.1023.Linux/Understand-5.1.1023-Linux-64bit/scitools/bin/linux64/Python"
import understand as und

db = und.open("/path/to/understand/database.udb")
dbents = db.ents()

print("-------------Understand-------------")
print("-------------import-------------")
counter = 0
refs_dict = {}
for i in dbents:
    for ref in i.refs("Import"):
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

print("-------------importBy-------------")
counter = 0
refs_dict = {}
for i in dbents:
    for ref in i.refs("ImportBy"):
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

