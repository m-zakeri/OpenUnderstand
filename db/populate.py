from models import Kind


def append_java_ent_kinds():
    with open("./java_ent_kinds.txt", "r") as f:
        for line in f.readlines():
            if line.startswith("Java"):
                query = line.strip()
                try:
                    kind = Kind.get(Kind.name == query)
                    if kind:
                        print(f"Kind exists: {kind}")
                        continue
                except Kind.DoesNotExist:
                    Kind(
                        name=query
                    ).save()


def append_java_ref_kinds():
    pass


if __name__ == '__main__':
    append_java_ent_kinds()
    append_java_ref_kinds()
