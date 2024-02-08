import os
import sys
os.add_dll_directory("C:\\Program Files\\SciTools\\bin\\pc-win64\\")
sys.path.append("C:\\Program Files\\SciTools\\bin\\pc-win64\\python")
import understand as und


def get_references_info(static=False):
    db_path = "C:\\Users\\USER\\OpenUnderstand\\benchmark\\JSON\\JSON.udb"
    n=0
    m=0
    db = und.open(db_path)
    candidates = []
    query = db.ents()
    external_references = 0
    for ent in query:
        kind_name = ent.kindname().lower()
        parent = ent.parent()

        """if parent is None:
            continue

        if not parent.kind().check("class") or parent.kind().check("anonymous"):
            continue"""

        source_package = None
        long_name = ent.longname().split(".")

        if len(long_name) >= 3:
            source_package = '.'.join(long_name[:-2])
            source_class, field_name = long_name[-2:]
        elif len(long_name) == 2:
            source_class, field_name = long_name
        else:
            continue

        is_public = ent.kind().check('public')
        is_private = ent.kind().check('private')

        for ref in ent.refs('Create, Createby'):
            print("ref =",ref)
            print("ref long = ",ref.ent().longname())
            print("in yeki =",'.'.join(long_name[:-1]))
            if '.'.join(long_name[:-1]) not in ref.ent().longname():
                external_references += 1
                candidates.append({
                        'source_package': source_package, 'source_class': source_class, 'field_name': field_name,
                        'is_public': is_public, 'is_private': is_private, 'external_references': external_references
                    })
    print("total external references =",external_references)
    db.close()
    return candidates


# Get references information
l=[]
l1=[]
references_info = get_references_info(static=True)
for m in references_info:
    if int(m['external_references']) > 0:
        l.append(m)
for z in l:
    if z not in l1:
        l1.append(z)
with open('createund.txt', 'w') as file:
    for q in l1:
        file.write(str(q)+"\n")


# Get references information


# Close the Understand database





