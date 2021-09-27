"""
CRUD operation in JSON for Understand example

"""


# https://tinydb.readthedocs.io/en/latest/usage.html
from tinydb import TinyDB, Query


# Example C project

"""
myFile.c
    void main(){
       char myString[];
       myString = “Hello World!”;
    }
"""

db = TinyDB('ExampleProjectDB.json')
ent_table = db.table('Ent')
ref_table = db.table('Ref')

# Ent #1
ent_table.insert({'name': 'myFile.c',
                  'longname': 'c:/temp/ExampleProject/myFile.c',
                  'language': 'C',
                  'kind': 'C Code File',
                  })

# Ent 2
ent_table.insert({'name': 'main',
                  'parent': 'c:/temp/ExampleProject/myFile.c',
                  'language': 'C',
                  'kind': 'C Function',
                  'type': 'int',
                  })

# Ent 3
ent_table.insert({'name': 'myString',
                  'parent': 'main',
                  'language': 'C',
                  'kind': 'C Local Object',
                  'type': 'char []',
                  'value': 'HelloWorld'
                  })

# Ref 1
ref_table.insert({'entity': 'main',
                  'scope': 'myFile.c',
                  'file': 'myFile.c',
                  'line': 1,
                  'column': 5,
                  'kind': 'C Define'  # myFile.c defines main
                })

# Ref 2
ref_table.insert({'entity': 'myString',
                  'scope': 'main',
                  'file': 'myFile.c',
                  'line': 2,
                  'column': 7,
                  'kind': 'C Define'  # main defines myString
                })

# Ref 3
ref_table.insert({'entity': 'myString',
                  'scope': 'main',
                  'file': 'myFile.c',
                  'line': 3,
                  'column': 2,
                  'kind': 'C Set'  # main sets myString
                })