from pprint import pprint

try:
    import understand
except ImportError:
    print("Can not import understand")

db = understand.open(r"D:\works\university\term6\compiler\Project\OpenUnderstand\benchmark\xerces2j\xerces2j\xerces2j1.udb")

counter = 0

for ent in db.ents():
    for ref in ent.refs():

        if ref.kindname() == "Define":
            counter += 1

            print("+++++++++++++++++++++++++")

            print(f"entity: {ent}\n, ref: {ref}\n ref.scope: {ref.scope()}, ref.ent: {ref.ent()}\n"
                  f"ref.line: {ref.line()}, ref.col: {ref.column()}, ref.file: {ref.file().name()}")
            print("--------------------------------------------------------")
            print(f"ref.ent.name:{ref.ent().name()}, ref.ent.longname:{ref.ent().longname()} ,ref.ent.kind:{ref.ent().kind()}\n"
                  f"ref.ent.parent:{ref.ent().parent()}, ref.ent.value:{ref.ent().value()},ref.ent.type:{ref.ent().type()}\n")
            print("--------------------------------------------------------")

print(counter)