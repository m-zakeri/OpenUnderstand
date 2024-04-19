import sys
from os import getcwd
from os.path import join
from collections import Counter
from rich.console import Console
from rich.table import Table

sys.path.append(join(getcwd(), "openunderstand"))
sys.path.append(join(getcwd(), "openunderstand", "oudb"))
sys.path.append(join(getcwd(), "openunderstand", "utils"))
import openunderstand.ounderstand as und

_db = und.open("/home/mehran/Downloads/OpenUnderstand/hw.udb")
dbents = _db.ents()


def understandout(ou, ouanswer):
    import os
    import sys
    sys.path.append(
        "/home/mehran/Downloads/Scientific.Toolworks.Understand.5.1.1023.Linux/Understand-5.1.1023-Linux-64bit/scitools/bin/linux64/Python"
    )
    import understand
    db = understand.open(
        "/home/mehran/Downloads/OpenUnderstand/benchmark/hw6test/hw6test.udb"
    )
    dbents = db.ents()
    unders = []
    counter = 0
    for i in dbents:
        for ref in sorted(i.refs("Set Partial"), key=lambda x: x.line()):  # Sort by line numbers
            print("Under =====> ", ref.ent().name(), ref.line())
            unders.append(ref.line())
            counter += 1

    # Count occurrences of each element in the lists
    count1 = Counter(ou)
    count2 = Counter(unders)

    # Find elements that are in one Counter but not in the other, considering counts
    unique_to_openunderstand = {key: count1[key] for key in count1 if key not in count2 or count1[key] > count2[key]}
    unique_to_understand = {key: count2[key] for key in count2 if key not in count1 or count2[key] > count1[key]}

    # Create and print a table
    table = Table(title="Number of Set Partials", show_header=True, header_style="bold magenta")
    table.add_column("OpenUnderstand", style="dim", justify="center")
    table.add_column("Understand", style="dim", justify="center")
    for key, count in unique_to_openunderstand.items():
        table.add_row(str(key), "")
    for key, count in unique_to_understand.items():
        table.add_row("", str(key))

    # Add counter and ouanswer to the table
    table.add_row(f"OU: {ouanswer}", f"U: {counter}")

    console = Console()
    console.print(table)

    # Print the unique elements
    print("Elements unique to OpenUnderstand:", [key for key, count in unique_to_openunderstand.items()])
    print("Elements unique to Understand:", [key for key, count in unique_to_understand.items()])


print("\n--------------Set--------------")

counter = 0
openunderstandOutput = []
for i in dbents:
    for ref in sorted(i.refs("Set Partial"), key=lambda y: y.line()):  # Sort by line numbers
        print("OpenUnder =====> ", ref.ent().name(), ref.line())
        openunderstandOutput.append(ref.line())
        counter += 1
ouanswer = counter

understandout(openunderstandOutput, ouanswer)


# ref.kindname [OK]
# ref.kind [OK]
# ref.line [OK]
# ref.column [OK]
# ref.file [OK]

# ref.ent() [OK]
# ref.ent().name [OK]
# ref.ent().longname [OK]
# ref.ent().refs [API Error]
# ref.ent().ents [API Error]
# ref.ent().parent [Close] LATER
# ref.ent().type [Not OK]
# ref.ent().kind [Not OK But i know how to fix]
# ref.ent().kindName [Just like above]
# ref.ent().value [NOT BAD]
# ref.ent().filerefs [Ok]

# ref.scope() [Not OK]
# ref.scope().value [Close]
# ref.scope().longname [OK]
# ref.scope().kind [like ent().kind]
# ref.scope().type [OK]
# ref.scope().value [OK]
# ref.scope().contents [OK (Space problem from somewhere else)]
# ref.scope().name [Not OK]
# ref.scope().kindname [just like kind]
# ref.scope().parent [Error]





