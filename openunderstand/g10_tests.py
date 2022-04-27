import understand as und

PRJ_INDEX = -1
PROJECTS_NAME = [
    'calculator_app',
    'JSON',
    'testing_legacy_code',
    'jhotdraw-develop',
    'xerces2j',
    'jvlt-1.3.2',
    'jfreechart',
    'ganttproject',
    '105_freemind',
    'custom_app',
]
PROJECT_NAME = PROJECTS_NAME[PRJ_INDEX]
DB_PATH = f"../../databases/origin/{PROJECT_NAME}.udb"
PROJECT_PATH = f"../../benchmarks/{PROJECT_NAME}"


def test_understand_kinds():
    db = und.open(DB_PATH)
    for ent in db.ents():
        for ref in ent.refs("Modify"):
            print(f'ref.scope (entity performing reference)\t: "{ref.scope().longname()}", kind: "{ref.scope().kind()}"')
            print(f'ref.ent (entity being referenced)\t\t: "{ref.ent().longname()}", kind: "{ref.ent().kind()}"')
            print(f'File where the reference occurred: "{ref.file().longname()}", line: {ref.line()}, col: {ref.column()}')

            print(f"Entity longname: {ent.longname()}")
            print(f"Entity parent: {ent.parent()}")
            print(f"Entity kind: {ent.kind()}")
            print(f"Entity value: {ent.value()}")
            print(f"Entity type: {ent.type()}")
            print(f"Entity contents: {ent.contents()}")
            print('-' * 50)

            print(f"File kind: {ref.file().kind()}")
            print(f"Parent: {ref.file().parent()}, long name: {ref.file().longname()}")
            print(f"Value: {ref.file().value()}, type: {ref.file().type()}")
            print(f"Contents: {ref.file().contents()}, name: {ref.file().name()}")
            print('-' * 50)

if __name__ == '__main__':
    test_understand_kinds()
