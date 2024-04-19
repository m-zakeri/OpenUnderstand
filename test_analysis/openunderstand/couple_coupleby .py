import sys
from os import getcwd
from os.path import join
sys.path.append(join(getcwd(), "openunderstand"))
sys.path.append(join(getcwd(), "openunderstand", "oudb"))
sys.path.append(join(getcwd(), "openunderstand", "utils"))
import openunderstand.ounderstand as und

def get_references_info(static=False):
    db_path = "C:\\Users\\USER\\OpenUnderstand\\mydb.udb"

    db = und.open(db_path)
    candidates = []
    query = db.ents()
    external_references = 0
    for ent in query:
        kind_name = ent.kindname().lower()

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
            if '.'.join(long_name[:-1]) not in ref.ent().longname():
                external_references += 1
                candidates.append({
                        'source_package': source_package, 'source_class': source_class, 'field_name': field_name,
                        'is_public': is_public, 'is_private': is_private, 'external_references': external_references
                    })
    print("total external references =",external_references)
    db.close()
    return candidates

l=[]
l1=[]
# Get references information
references_info = get_references_info(static=True)
for m in references_info:
    if int(m['external_references']) > 0:
        l.append(m)
for z in l:
    if z not in l1:
        l1.append(z)
with open('createound.txt', 'w') as file:
    file.write("values with external references = 1 in understand \n")
    for q in references_info:
        file.write(str(q)+"\n")
