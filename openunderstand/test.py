from pprint import pprint
from oudb.models import KindModel, EntityModel, ReferenceModel
from oudb.api import open as db_open, create_db
from oudb.fill import main


try:
    import understand as und
except ImportError:
    print("Can not import understand")

project_index = 8
project_list = [
    "calculator_app",       # 0
    "JSON",                 # 1
    "testing_legacy_code",  # 2
    "105_freemind",         # 3
    "ganttproject",         # 4
    "jfreechart",           # 5
    "jhotdraw-develop",     # 6
    "jvlt-1.3.2",           # 7
    "xerces2j"              # 8
]
db = und.open(rf"C:\Compiler\OpenUnderstand\benchmark\{project_list[project_index]}\{project_list[project_index]}.und")
n = 1

#ent = db.lookup("Admin", "method")[0]
for ent in db.ents():
    for ref in ent.refs(refkindstring="create"):
        # print(ref)
        # print("ent", ref.ent(), "value", ref.ent().value(), "type", ref.ent().type(), "ent.kind parent:",
        #       ref.ent().parent().kind(), "/////////", "parent ln:", ref.ent().parent().longname(), "//////////",
        #       "name:", ref.ent().name(), "///////////", "longname:", ref.ent().longname(), "///// contents: ",
        #       ref.ent().contents)
        # print("scope: ", ref.scope())
        print(f'1. refname:{ref.kindname()}, inverse ref name:{ref.kind().inv().longname()}')
        print(f'2. ref.scope(entity performing reference)\t: "{ref.scope().longname()}", kind: "{ref.scope().kind()}"')
        print(f'3. ref.entity(entity being referenced)\t\t: "{ref.ent().longname}" kind: "{ref.ent().kind()}"')
        print(f'4. location the reference occured: "{ref.file().longname()}", line: {ref.line()}')
        print(n)
        print(f'')
        n = n + 1
