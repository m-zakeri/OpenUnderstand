from pprint import pprint

try:
    import understand as und
except ImportError:
    print("Can not import understand")

db = und.open("D:\Dev\JavaSample\JavaSample1.udb")

ent = db.ents("class")

for i in ent:
    depends = i.depends()
    if depends:
        print(i, i.kind(), i.parent())
        for k, v in depends.items():
            print(k, k.kind())
            pprint(v)
        print("============")
