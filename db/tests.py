from pprint import pprint

try:
    import understand as und
except ImportError:
    print("Can not import understand")

db = und.open("D:\Dev\JavaSample\JavaSample1.udb")

ent = db.lookup("Admin", "method")[0]
print(ent, ent.simplename())
for ref in ent.refs(entkindstring="method", unique=True):
    print(ref, ref.kind().longname())