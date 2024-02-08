import sys
from os import getcwd
from os.path import join
sys.path.append(join(getcwd(), "openunderstand"))
sys.path.append(join(getcwd(), "openunderstand", "oudb"))
sys.path.append(join(getcwd(), "openunderstand", "utils"))
import openunderstand.ounderstand as und

_db = und.open("C:\\Users\\USER\\OpenUnderstand\\mydb.udb")
dbents = _db.ents()
print("---------Create---------")
all_things=[]
print(len(dbents))
l=['com.calculator.app.method.fibonacci',
    'com.calculator.app.method.basic_operation',
"java.lang.System",
'com.calculator.app.display.print_fail',
'java.lang.Object',
'com.calculator.app.method.integral',
'com.calculator.app.method.printLog',
'com.calculator.app.init.Main',
'String',
'com.calculator.app.display.println',
'com.calculator.app.display.print_success',
'Override',
]
n=0
v=[]
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


'''for m in l:
    if m not in v:
        print(m)'''