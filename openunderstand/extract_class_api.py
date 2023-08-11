# import understand as und
import csv
from pathlib import Path
import oudb.api as und

from os import path, getcwd
from main import runner


class ExtractClassAPI:
    def __init__(self, udb_path: str = ""):
        self.udb_path = udb_path

    def get_source_class_map(self):
        _db = und.open(dbname=self.udb_path)
        classes = _db.ents("Type Class ~Unknown ~Anonymous")
        print(len(classes))
        for i, c in enumerate(classes):
            source_class = c.simplename()
            try:
                file_path = c.parent().longname()
            except:
                continue
            class_fields = []
            class_methods = []
            for ref in c.refs("define", "variable"):
                class_fields.append(ref.ent())
            for ref in c.refs("define", "method"):
                class_methods.append(ref.ent())
            moved_fields = ([ent.simplename() for ent in class_fields],)
            moved_methods = ([ent.simplename() for ent in class_methods],)
            print(moved_methods)
            print(moved_methods)
            field_usages = []
            # for field in moved_fields:
            #     # print(f"{source_class}.{field}")
            #     for ent in _db.lookup(f"{source_class}.{field}"):
            #         print("here")
            #         for ref in ent.refs("Useby, Setby, Modifyby"):
            #             if Path(ref.file().longname()) == Path(file_path):
            #                 continue
            #             field_usage = {
            #                 "field_name": field,
            #                 "file_path": ref.file().longname(),
            #             }
            #             if field_usage not in field_usages:
            #                 print("in if ")
            #                 field_usages.append(field_usage)
            #                 filename = "extract_class_class.csv"
            #                 fieldnames = ["FieldUsage"]
            #                 with open(filename, "w", newline="") as csvfile:
            #                     writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            #                     writer.writeheader()
            #                     writer.writerow(
            #                         {"FieldUsage": field_usage["field_name"]}
            #                     )
        _db.close()
