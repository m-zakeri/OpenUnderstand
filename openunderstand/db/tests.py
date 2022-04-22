from pprint import pprint

try:
    import understand as und
except ImportError:
    print("Can not import understand")

db = und.open("C:/Users/98910/university/Term6/Courses/Compiler/Project/Compiler_OpneUnderstand/OpenUnderstand-8b69f877f175bf4ccd6c58ec3601be655157d8ca/benchmark/jfreechart/jfreechart.udb")

# ent = db.lookup("Admin", "method")[0]
# print(ent, ent.simplename())
# for ref in ent.refs(entkindstring="method", unique=True):
#     print(ref, ref.kind().longname())



for ent in db.ents():
    for ref in ent.refs():

        if ref.kindname() == "Declare": # and ref.file().name() == "printLog.java":
            print(f"ent name: {ent.name()}, ent longname: {ent.longname()}, \n"
                  f"ent parent: {ent.parent()}, ent kind: {ent.kind()}, ent value: {ent.value()},\n"
                  f"ent type: {ent.type()}, ent contents: {ent.contents()}")
            print("+++++++++++++++++++++++++")
            # print(f"file kind: {ref.file().kind()}, parent: {ref.file().parent()}, long name: {ref.file().longname()}"
            #       f"\nvalue: {ref.file().value()}, type: {ref.file().type()}, contents: {ref.file().contents()}, name: {ref.file().name()}")

            print(f"entity: {ent}\n, ref: {ref}\n ref.scope: {ref.scope()}, ref.ent: {ref.ent()}\n"
                  f"ref.line: {ref.line()}, ref.col: {ref.column()}, ref.file: {ref.file().name()}")
            print("--------------------------------------------------------")
            print(f"ref.ent.name:{ref.ent().name()}, ref.ent.longname:{ref.ent().longname()} ,ref.ent.kind:{ref.ent().kind()}\n"
                  f"ref.ent.parent:{ref.ent().parent()}, ref.ent.value:{ref.ent().value()},ref.ent.type:{ref.ent().type()}\n"
                  f"ref.ent.contents:{ref.ent().contents()}")
            print("--------------------------------------------------------")