import sys
from os import getcwd
from os.path import join
sys.path.append(join(getcwd(), "openunderstand"))
sys.path.append(join(getcwd(), "openunderstand", "oudb"))
sys.path.append(join(getcwd(), "openunderstand", "utils"))
import openunderstand.ounderstand as und

_db = und.open("C:\\Users\\USER\\OpenUnderstand\\mydb.udb")
dbents = _db.ents()
print("---------declare---------")
all_things=[]
print(len(dbents))
for i in dbents:
    for j in i.refs('Declare, Declarein'):
        longname = i.longname()
        file = j.file()
        ent = j.ent()
        line = j.line()
        kind = j.kind()
        column = j.column()
        isforward = j.isforward()
        kindname = j.kindname()
        scope = j.scope()
        all_things.append({
            'longname ': longname,
            #'file ':file,
            #'ent ': ent,
            #'line ': line,
            #'kind ': kind,
            #'column ': column,
            #'isforward ': isforward,
            #'kindname ': kindname,
            #'scope ': scope

        })

for i in all_things:
    print(i)
print(len(all_things))
