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
                    kind = Kind(
                        name=query
                    )
                    res = kind.save()
                    if res:
                        print(f"Created: {kind}")
                    else:
                        raise ConnectionError("Database disconnected, please try again!")


def append_java_ref_kinds():
    # TODO: Complete this method!
    pass


if __name__ == '__main__':
    append_java_ent_kinds()
    append_java_ref_kinds()
