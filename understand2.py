# encoding: utf-8
# module understand calls itself understandAPI
# from D:\program files\SciTools\bin\pc-win64\Python\understand.pyd
# by generator 1.147
"""
This is the python interface to Understand databases.

It provides class-orientated access to Understand databases. Most
of the class objects are only valid when returned from a function.

The following classes and methods are in this module:
Classes:
  understand.Arch
  understand.Db
  understand.Ent
  understand.Kind
  understand.Lexeme
  understand.Lexer
  understand.LexerIter
  understand.Metric
  understand.Ref
  understand.UnderstandError
  understand.Visio
Methods:
  understand.checksum(text [,len])
  understand.license(path)
  understand.open(dbname)
  understand.version()

Examples

The following examples are meant to be complete, yet simplistic
scripts that demonstrate one or more features each. For the sake of
brevity, most try, except statements statements are ommitted.

Sorted List of All Entities
---------------------------

import understand

# Open Database
db = understand.open("test.udb")

for ent in sorted(db.ents(),key= lambda ent: ent.name()):
  print (ent.name(),"  [",ent.kindname(),"]",sep="",end="\n")


List of Files
-------------

import understand

db = understand.open("test.udb")

for file in db.ents("File"):
  # print directory name
  print (file.longname())


Lookup an Entity (Case Insensitive)
-----------------------------------

import understand
import re

db = understand.open("test.udb")

# Create a regular expression that is case insensitive
searchstr = re.compile("test*.cpp",re.I)
for file in db.lookup(searchstr,"File"):
  print (file)


Global Variable Usage
---------------------

import understand

db = understand.open("test.udb")

for ent in db.ents("Global Object ~Static"):
  print (ent,":",sep="")
  for ref in ent.refs():
    print (ref.kindname(),ref.ent(),ref.file(),"(",ref.line(),",",ref.column(),")")
  print ("\n",end="")


List of Functions with Parameters
---------------------------------

import understand

def sortKeyFunc(ent):
  return str.lower(ent.longname())

db = understand.open("test.udb")

ents = db.ents("function,method,procedure")
for func in sorted(ents,key = sortKeyFunc):
  print (func.longname()," (",sep="",end="")
  first = True
  for param in func.ents("Define","Parameter"):
    if not first:
      print (", ",end="")
    print (param.type(),param,end="")
    first = False
  print (")")


List of Functions with Associated Comments
------------------------------------------

import understand

db = understand.open("test.udb")

for func in db.ents("function ~unresolved ~unknown"):
  comments = func.comments("after")
  if comments:
    print (func.longname(),":\n  ",comments,"\n",sep="")


List of Ada Packages
--------------------

import understand

db = understand.open("test.udb")

print ("Standard Packages:")
for package in db.ents("Package"):
  if package.library() == "Standard":
    print ("  ",package.longname())

print ("\nUser Packages:")
for package in db.ents("Package"):
  if package.library() != "Standard":
    print("  ",package.longname())


All Project Metrics
-------------------

import understand

db = understand.open("test.udb")

metrics = db.metric(db.metrics())
for k,v in sorted(metrics.items()):
  print (k,"=",v)


Cyclomatic Complexity of Functions
----------------------------------

import understand

db = understand.open("test.udb")

for func in db.ents("function,method,procedure"):
  metric = func.metric(("Cyclomatic",))
  if metric["Cyclomatic"] is not None:
    print (func," = ",metric["Cyclomatic"],sep="")


"Called By" Graphs of Functions
-------------------------------

import understand

db = understand.open("test.udb")

for func in db.ents("function,method,procedure"):
  file = "callby_" + func.name() + ".png"
  print (func.longname(),"->",file)
  func.draw("Called By",file)


Info Browser View of Functions
------------------------------

import understand

db = understand.open("test.udb")

for func in db.ents("function,method,procedure"):
  for line in func.ib():
    print(line,end="")


Lexical Stream
--------------

import understand

db = understand.open("test.udb")

file = db.lookup("test.cpp")[0]
for lexeme in file.lexer():
  print (lexeme.text(),end="")
  if lexeme.ent():
    print ("@",end="")
"""
# no imports

# Variables with simple values

COMMENT = 'Comment'
CONTINUATION = 'Continuation'

DEDENT = 'Dedent'

ENDOFSTATEMENT = 'EndOfStatement'

EOF = 'EOF'

IDENTIFIER = 'Identifier'
IDSEQ = 'IdSeq'

INDENT = 'Indent'

KEYWORD = 'Keyword'

LABEL = 'Label'

LITERAL = 'Literal'

NEWLINE = 'Newline'

OPERATOR = 'Operator'

PREPROCESSOR = 'Preprocessor'

PUNCTUATION = 'Punctuation'

STRING = 'String'

WHITESPACE = 'Whitespace'


# functions

def checksum(text, len=None):  # real signature unknown; restored from __doc__
    """
    understand.checksum(text [,len]) -> string

    Return a checksum of the text

    The optional parameter len specifies the length of the checksum,
    which may be between 1 and 32 characters, with 32 being the default
    """
    return ""


def license(name):  # real signature unknown; restored from __doc__
    """
    understand.license(name) -> None

    Set a regcode string or a specific path to an understand license
    """
    pass


def open(dbname):  # real signature unknown; restored from __doc__
    """
    understand.open(dbname) -> understand.Db

    Open a database from the passed in filename.

    This returns a new understand.Db given the dbname (string). It
    will throw an understand.UnderstandError if unsuccessful. Possible causes
    for error are:
      DBAlreadyOpen        - only one database may be open at once
      DBCorrupt            - bad database file
      DBOldVersion         - database needs to be rebuilt
      DBUnknownVersion     - database needs to be rebuilt
      DBUnableOpen         - database is unreadable or does not exist
      NoApiLicense         - Understand license required
    """
    pass


def version():  # real signature unknown; restored from __doc__
    """
    understand.version() -> int

    Return the current build number for this module
    """
    return 0


# classes

class Arch(object):
    """
    This class represents an understand Architecture. Available methods are:

      understand.Arch.children
      understand.Arch.contains(entity [,recursive])
      understand.Arch.depends(recursive=true,group=false)
      understand.Arch.dependsby(recursive=true,group=false)
      understand.Arch.draw(graph,filename [,options])
      understand.Arch.ents([recursive])
      understand.Arch.longname()
      understand.Arch.name()
      understand.Arch.parent()  understand.Arch.__repr__()  --longname
      understand.Arch.__str__()  --name
    """

    def children(self):  # real signature unknown; restored from __doc__
        """
        arch.children() -> list of understand.Arch

        Return the children of the architecture.
        """
        return []

    def contains(self, entity, recursive=None):  # real signature unknown; restored from __doc__
        """
        arch.contains(entity [,recursive]) -> bool

        Return true if the entity is contained in the architecture

        The parameter entity should be an instance of understand.Ent.

        The optional parameter recursive specifies if the search is recursive.
        If true, all nested architectures will be considered as well. It is
        false by default.
        """
        return False

    def depends(self, recursive, group):  # real signature unknown; restored from __doc__
        """
        arch.depends(recursive,group) ->
          dict key=understand.Arch value=list of understand.Ref

        Return the dependencies of the architecture.

        The optional parameter recursive is true by default. When false, child
        architecture dependencies are not included.

        The optional parameter group is false by default. When true, the keys
        in the dictionary will be grouped into as few keys as possible.

        For example, given the architecture structure:
          All
            Bob
              Lots of entities
            Sue
              Current
                Lots of entities
              Old
                Lots of entities

        calling sue.depends(recursive=false) would return an empty dictionary
        since sue's children (current and old) are not considered. Calling
        bob.depends(group=true) would result in a single key in the
        dictionary (Sue), as opposed to two keys (Sue/Current and Sue/Old)
        since all the entities were grouped together.
        """
        return {}

    def dependsby(self, recursive, group):  # real signature unknown; restored from __doc__
        """
        arch.dependsby(recursive,group) ->
          dict key=understand.Arch value=list of understand.Ref

        Return the architectures depended on by the architecture.

        The optional parameter recursive is true by default. When false, child
        architecture dependencies are not included.

        The optional parameter group is false by default. When true, the keys
        in the dictionary will be grouped into as few keys as possible.

        For more information, see the help for understand.Arch.depends()
        """
        return {}

    def draw(self, graph, filename, options=None):  # real signature unknown; restored from __doc__
        """
        arch.draw(graph, filename [,options]) -> None

        Generate a graphics file for the architecture.
        This command is not supported when running scripts
        through the command line tool und

        The parameter graph(string) should be the name of the graph to
        generate. Available graphs vary by language and architecture, but the name
        will be the same as the name in the Understand GUI. Some examples are:
          "Cluster Call"
          "Graph Architecture"
          "Internal Dependencies"
        The parameter filename(string) should be the name of the file.
        Only jpg, png, and svg file formats are supported on all platforms,
        so the filename parameter must end with either the extension .jpg,
        .png or .svg. The extension .dot may be also specified. This will
         create a .svg image file as well as the .dot file.
        The parameter options (string) is used to specify paramters used to
        generate the graphics. The format of the options string is
        "name=value". Multiple options are seperated with a semicolon.
        spaces are allowed and are significant between mutli-word field names,
        whereas, case is not significant. The valid names and values are the
        same as appear in that graphs right click menu and vary by view. They
        may be abbreviated to any unique prefix of their full names.
        If an error occurs, and UnderstandError will be thrown. Some possible errors
        are:
          NoFont               - no suitable font can be found
          NoImage              - no image is defined or is empty
          NoVisioSupport       - no Visio .vsd files can be generated on
                                 non-windows
          TooBig               - jpg does not support a dimension greater
                                 than 64k
          UnableCreateFile     - file cannot be opened/created
          UnsupportedFile      - only .jpg, .png, or .svg files are supported
        Additional error messages are also possible when generating a Visio
        file.
        """
        pass

    def ents(self, recursive=None) -> list:  # real signature unknown; restored from __doc__
        """
        arch.ents([recursive]) -> list of understand.Ent

        Return the entities within the architecture.

        The optional parameter recursive determines if nested architectures
        are considered. It is false by default.
        """
        return []

    def longname(self):  # real signature unknown; restored from __doc__
        """
        arch.longname() -> string

        Return the long name of the architecture.
        """
        return ""

    def name(self):  # real signature unknown; restored from __doc__
        """
        arch.name() -> string

        Return the short name of the architecture.
        """
        return ""

    def parent(self):  # real signature unknown; restored from __doc__
        """
        arch.parent() -> understand.Arch

        Return the parent of the Arch or None if it is a root.
        """
        pass

    def __init__(self, *args, **kwargs):  # real signature unknown
        pass

    def __repr__(self, *args, **kwargs):  # real signature unknown
        """ Return repr(self). """
        pass

    def __str__(self, *args, **kwargs):  # real signature unknown
        """ Return str(self). """
        pass


class Atn(object):
    """
    This class represents an understand annotation. Annotations can be obtained
    for a database (db.annotations()) or for an entity (ent.annotations())
    Available Methods are:
      understand.Atn.author()
      understand.Atn.ent()
      understand.Atn.date()
      understand.Atn.text()
    """

    def author(self):  # real signature unknown; restored from __doc__
        """
        atn.author() -> string

        Return the author who created the annotation.
        """
        return ""

    def date(self):  # real signature unknown; restored from __doc__
        """
        atn.date() -> string

        Return the date the annotation was last modified as a string of the form
        YYYY-MM-DDTHH:MM:SS such as 2000-01-01T19:20:30.
        """
        return ""

    def ent(self):  # real signature unknown; restored from __doc__
        """
        atn.ent() -> understand.Ent

        Return the entity this annotation belongs to. This may be None if the
        annotation is an orphan.
        """
        pass

    def line(self):  # real signature unknown; restored from __doc__
        """
        atn.line() -> int

        Return the line number (in the file) of the annotation or -1 if the
        annotation is not a line annotation.
        """
        return 0

    def text(self):  # real signature unknown; restored from __doc__
        """
        atn.text() -> string

        Return the text of the annotation.
        """
        return ""

    def __init__(self, *args, **kwargs):  # real signature unknown
        pass


class Check(object):
    """
    Available Methods are:
      understand.Check.db()
      understand.Check.files()
      understand.Check.is_aborted()
      understand.Check.violation(entity,file,line,column,text)
      understand.Check.option()
    """

    def db(self):  # real signature unknown; restored from __doc__
        """
        check.db() -> understand.Db

        Return the database associated with this check.
        """
        pass

    def files(self):  # real signature unknown; restored from __doc__
        """
        check.files() -> list of understand.Ent

        Return the list of files associated with this check.
        """
        return []

    def id(self):  # real signature unknown; restored from __doc__
        """
        check.id() -> string

        Return the id of this check.
        """
        return ""

    def is_aborted(self):  # real signature unknown; restored from __doc__
        """
        check.is_aborted() -> bool

        Return True if the check has been aborted by the user.
        """
        return False

    def option(self):  # real signature unknown; restored from __doc__
        """
        check.option() -> understand.Option

        Return the Option object associated with this check.
        """
        pass

    def violation(self, entity, file, line, column, text):  # real signature unknown; restored from __doc__
        """
        check.violation(entity,file,line,column,text) -> understand.Violation

        Emit a violation of this check.
        """
        pass

    def __init__(self, *args, **kwargs):  # real signature unknown
        pass


class Db(object):
    """
    This class represents an understand database. With the exception of
    Db.close(), all methods require an open database. A database is
    opened through the module function understand.open(dbname). Available
    methods are:

      understand.Db.add_annotation_file(path)
      understand.Db.annotations()
      understand.Db.archs(ent)
      understand.Db.close()
      understand.Db.comparison_db()
      understand.Db.ent_from_id(id)
      understand.Db.ents([kindstring])
      understand.Db.language()
      understand.Db.lookup(name [,kindstring])
      understand.Db.lookup_arch(longname)
      understand.Db.lookup_uniquename(uniquename)
      understand.Db.metric(metriclist)
      understand.Db.metrics()
      understand.Db.metrics_treemap(file, sizemetric, colormetric [enttype [,arch]])
      understand.Db.name()
      understand.Db.relative_file_name()
      understand.Db.root_archs()  understand.Db.__str__() --name
    """

    def add_annotation_file(self, path, foreground=None,
                            background=None):  # real signature unknown; restored from __doc__
        """
        db.add_annotation_file(path [,foreground [,background]]) -> None

        Add a new or existing annotation database file to this database.
        The added file is set as the currently selected annotation database.
        The foreground and background arguments should take the form #RRGGBB.
        """
        pass

    def annotations(self):  # real signature unknown; restored from __doc__
        """
        db.annotations() -> list of understand.Atn

        Return a list of annotations for the database.
        """
        return []

    def archs(self, ent):  # real signature unknown; restored from __doc__
        """
        db.archs(ent) -> list of understand.Arch

        Return a list of architectures that contain ent (understand.Ent)
        """
        return []

    def close(self):  # real signature unknown; restored from __doc__
        """
        db.close() -> None

        Close the database.

        This allows a new database to be opened. It will never throw an
        error and is safe to call even if the database is already closed.
        After the database is closed, accessing objects associated with
        the database (ents, refs, ...) can cause Python to crash.
        """
        pass

    def comparison_db(self):  # real signature unknown; restored from __doc__
        """
        db.comparison_db() -> understand.Db

        Return the comparison database associated with this database.
        """
        pass

    def ents(self, kindstring=None):  # real signature unknown; restored from __doc__
        """
        db.ents([kindstring]) -> list of understand.Ent

        Return a list entities in the database.

        If the optional parameter kindstring(string) is not passed, then all
        the entities in the database are returned. Otherwise, kindstring
        should be a language-specific entity filter string. The database
        must be open or a UnderstandError will be thrown.
        """
        return []

    def ent_from_id(self, id):  # real signature unknown; restored from __doc__
        """
        db.ent_from_id(id) -> understand.Ent

        Return the ent associated with the id.

        The id is obtained using ent.id. This should only be called for
        identifiers that have been obtained while the database has remained
        open. When a database is reopened, the identifier is not guaranteed
        to remain consistent and refer to the same entity.
        """
        pass

    def language(self):  # real signature unknown; restored from __doc__
        """
        db.language() -> tuple of strings

        Return a tuple with project languages

        This method returns a tuple containing all the language names
        enabled in the project. Possible language names are: "Ada", "C++",
        "C#", "Fortran", "Java", "Jovial", "Pascal", "Plm",
        "Python", "VHDL", or "Web". C is included with "C++"
        This will throw a UnderstandError if the database has been closed.
        """
        return ()

    def lookup(self, name, kindstring=None):  # real signature unknown; restored from __doc__
        """
        db.lookup(name [,kindstring]) -> list of understand.Ent

        Return a list of entities that match the specified name.

        The parameter name should be a regular expression, either compiled or
        as a string. By default, regular expressions are case sensitive. For
        case insensitive search, compile the regular expression like this:
          import re
          db.lookup(re.compile("searchstring",re.I))
        The re.I flag is for case insensitivity. Otherwise, the lookup command
        can be run simply
          db.lookup("searchstring")
        The optional paramter kindstring is a language-specific entity filter
        string. So, for example,
          db.lookup(".Test.","File")
        would return a list of file entities containing "Test" (case sensitive)
        in their names.
        """
        return []

    def lookup_arch(self, longname):  # real signature unknown; restored from __doc__
        """
        db.lookup_arch(longname) -> understand.Arch

        Return the architecture with the given longname, or None if not found.
        """
        pass

    def lookup_uniquename(self, uniquename):  # real signature unknown; restored from __doc__
        """
        db.lookup_uniquename(uniquename) -> ent

        Return the entity identified by uniquename.

        Uniquename is the name returned by ent.uniquename and repr(ent). This
        will return None if no entity is found.
        """
        pass

    def metric(self, metriclist):  # real signature unknown; restored from __doc__
        """
        db.metric(metriclist) -> dict key=string value=metricvalue

        Return the metric value for each item in metriclist

        Metric list must be a tuple or list containing the names of metrics
        as strings. If the metric is not available, it's value will be None.
        """
        return {}

    def metrics(self):  # real signature unknown; restored from __doc__
        """
        db.metrics() -> list of strings

        Return a list of project metric names.
        """
        return []

    def metrics_treemap(self, file, sizemetric, colormetric, enttype=None,
                        arch=None):  # real signature unknown; restored from __doc__
        """
        db.metrics_treemap(file, sizemetric, colormetric [,enttype [,arch]]) -> None

        Export a metrics treemap to the given file (must be jpg or png). The parameters
        sizemetric and colormetric should be the API names of the metrics. The optional
        parameter arch is the group-by arch. If none is given, the graph will be flat.
        The optional parameter enttype is the type of entities to use in the treemap. It
        must be a string either "file" "class" or "function". If none is given,
        file is assumed.
        """
        pass

    def name(self):  # real signature unknown; restored from __doc__
        """
        db.name() -> string

        Return the filename of the database.

        This will throw a UnderstandError if the database has been closed.
        """
        return ""

    def relative_file_name(self, absolute_path):  # real signature unknown; restored from __doc__
        """
        db.relative_file_name(absolute_path) -> string

        Return the relative file name like ent.relname() but for an arbitrary path.
        """
        return ""

    def root_archs(self):  # real signature unknown; restored from __doc__
        """
        db.root_archs() -> list of understand.Arch

        Return the root architectures for the database.
        """
        return []

    def __init__(self, *args, **kwargs):  # real signature unknown
        pass

    def __str__(self, *args, **kwargs):  # real signature unknown
        """ Return str(self). """
        pass


class Ent(object):
    """
    This class represents an understand entity(files, functions,
    variables, etc). Available methods are:

      understand.Ent.annotate(text [,offset])
      understand.Ent.annotations()
      understand.Ent.comments([style [,raw [,refkindstring]]])
      understand.Ent.contents()
      understand.Ent.depends()
      understand.Ent.dependsby()
      understand.Ent.draw(graph,filename [,options])
      understand.Ent.ents(refkindstring [,entkindstring])
      understand.Ent.__eq__() --by id
      understand.Ent.filerefs([refkindstring [,entkindstring [,unique]]])
      understand.Ent.__ge__() --by id
      understand.Ent.__gt__() --by id
      understand.Ent.__hash__() --id
      understand.Ent.ib([options])
      understand.Ent.id()
      understand.Ent.kind()
      understand.Ent.kindname()
      understand.Ent.language()
      understand.Ent.__le__() --by id
      understand.Ent.lexer([lookup_ents [,tabstop [,show_inactive [,expand_macros]]]])
      understand.Ent.library()
      understand.Ent.longname()
      understand.Ent.__lt__() --by id
      understand.Ent.metric(metriclist)
      understand.Ent.metrics()
      understand.Ent.name()
      understand.Ent.__ne__() --by id
      understand.Ent.parameters(shownames = True)
      understand.Ent.parent()
      understand.Ent.parsetime()
      understand.Ent.ref([refkindstring [,entkindstring]])
      understand.Ent.refs([refkindstring [,entkindstring [,unique]]])
      understand.Ent.relname()
      understand.Ent.__repr__() --uniquename
      understand.Ent.simplename()
      understand.Ent.__str__() --name
      understand.Ent.type()
      understand.Ent.uniquename()
      understand.Ent.value()
    """

    def annotate(self, text, author=None, offset=None):
        """
        ent.annotate(text [,author [,offset]]) -> None

        Add text as a new annotation associated with this entity.
        The annotation is added to the current annotation database
        with the currently set user name.
        """
        pass

    def annotations(self):  # real signature unknown; restored from __doc__
        """
        ent.annotations() -> list of understand.Atn

        Return the annotations associated with the entity, or empty list if
        there are none.
        """
        return []

    def comments(self, style=None, raw=None, refkindstring=None) -> str:  # real signature unknown; restored from __doc__
        """
        ent.comments( [style [,raw [,refkindstring]]] ) -> string

        Return the comments associated with the entity.

        The optional paramter style (string) is used to specify which comments
        are to be used. By default, comments that come after the entity
        declaration are processed. Possible values are:
          default              - same as after
          after                - process comments after the entity declaration
          before               - process comments before the entity declaration
        If a different value is passed in, it will be silently ignored.

        The optional paramater raw (true/false) is used to specify what kind of
        formatting, if any, is applied to the comment text. If raw is false,
        function will remove comment characters and certain repeating
        characters, while retaining the original newlines. If raw is true, the
        function will return a list of comment strings in original format,
        including comment characters.

        The optional parameter refkindstring should be a language specific
        reference filter string. For C++, the default is "definein",
        which is almost always correct. However, to see comments associated
        member declarations, "declarein" should be used. For Ada, there
        are many declaration kinds that may be used, including "declarein
        body", "declarein spec" and "declarein instance". A bad
        refkindstring may result in an UnderstandError.
        """
        return ""

    def contents(self):  # real signature unknown; restored from __doc__
        """
        ent.contents() -> string

        Return the contents of the entity.

        Only certain entities are supported, such as files and defined
        functions. Entities with no contents will return empty string.
        """
        return ""

    def depends(self):  # real signature unknown; restored from __doc__
        """
        ent.depends() -> dict key=understand.Ent value=list of understand.Ref

        Return the dependencies of the class or file

        This function returns all the dependencies as a dictionary between an
        ent and the references occurring in the ent. An empty dictionary will
        be returned if there are no dependencies for the ent. The ent should be
        a class or file.
        """
        return {}

    def dependsby(self):  # real signature unknown; restored from __doc__
        """
        ent.dependsby() -> dict key=understand.Ent value=list of understand.Ref

        Return the ents depended on by the class or file

        This function returns all the dependencies as a dictionary between an
        ent and the references occurring in the ent. An empty dictionary will
        be returned if there are no dependencies on the ent. The ent should be
        a class or file.
        """
        return {}

    def draw(self, graph, filename, options=None):  # real signature unknown; restored from __doc__
        """
        ent.draw(graph, filename [,options]) -> None

        Generate a graphics file for the entity

        The parameter graph(string) should be the name of the graph to
        generate. Available graphs vary by language and entity, but the name
        will be the same as the name in the Understand GUI. Some examples are:
          "Base Classes"
          "Butterfly"
          "Called By"
          "Control Flow"
          "Calls"
          "Declaration"
          "DependsOn"

        The parameter filename(string) should be the name of the file.
        Only jpg, png, and svg file formats are supported on all platforms,
        so the filename parameter must end with either the extension .jpg,
        .png or .svg. The extension .dot may be also specified. This will
         create a .svg image file as well as the .dot file.
        On windows systems that have Visio installed, the
        filename may end with .vsd, which will cause Visio to be invoked, to
        draw the graphics, and to save the drawing to the named file. Visio
        will remain running, but may be quit by calling quit() from the
        understand.Visio module.

        The parameter options (string) is used to specify paramters used to
        generate the graphics. The format of the options string is
        "name=value". Multiple options are seperated with a semicolon.
        spaces are allowed and are significant between mutli-word field names,
        whereas, case is not significant. The valid names and values are the
        same as appear in that graphs right click menu and vary by view. They
        may be abbreviated to any unique prefix of their full names. Some
        examples are:
          "Layout=Crossing; name=Fullname;Level=AllLevels"
          "Display Preceding Comments=On;Display Entity Name=On"

        For Relationship graphs use  secondent=EntityUniqueName to indicate the second entity

        If an error occurs, and UnderstandError will be thrown. Some possible errors
        are:
          NoFont               - no suitable font can be found
          NoImage              - no image is defined or is empty
          NoVisioSupport       - no Visio .vsd files can be generated on
                                 non-windows
          TooBig               - jpg does not support a dimension greater
                                 than 64k
          UnableCreateFile     - file cannot be opened/created
          UnsupportedFile      - only .jpg, .png, or .svg files are supported
        Additional error messages are also possible when generating a Visio
        file.
        """
        pass

    def ents(self, refkindstring, entkindstring=None):  # real signature unknown; restored from __doc__
        """
        ent.ents(refkindstring [,entkindstring]) -> list of understand.Ent

        Return a list of entities that reference, or are referenced by, the entity.

        The parameter refkindstring (string) should be a language-specific
        reference filter string.

        The optional paramater entkindstring (string) should be a language-
        specific entity filter string that specifies what kind of referenced
        entities are to be returned. If it is not included, all referenced
        entities are returned.
        """
        return []

    def filerefs(self, refkindstring=None, entkindstring=None,
                 unique=None):  # real signature unknown; restored from __doc__
        """
        ent.filerefs([refkindstring [,entkindstring [,unique]]]) -> list of understand.Ref

        Return a list of all references that occur in a file entity.

        If this is called on a non-file entity, it will return an empty list.
        The references returned will not necessarily have the file entity for
        their .scope value.

        The optional paramter refkindstring (string) should be a language-
        specific reference filter string. If it is not given, all references
         are returned.

        The optional paramter entkindstring (string) should be a language-
        specific entity filter string that specifies what kind of referenced
        entities should be returned. If it is not given, all references to
        any kind of entity are returned.

        The optional parameter unique (bool) is false by default. If it is
        true, only the first matching reference to each unique entity is
        returned
        """
        return []

    def freetext(self, option):  # real signature unknown; restored from __doc__
        """ ent.freetext(option) -> string """
        return ""

    def ib(self, options=None):  # real signature unknown; restored from __doc__
        """
        ent.ib([options]) -> list of strings

        Return the Info Browser information for an entity.

        The optional parameter options (string) may be used to specify some
        parameters used to create the text. The format of the options string
        is "name=value" or "{field-name}name=value". Multiple options are
        separated with a semicolon. Spaces are allowed and are significant
        between multi-word field names, whereas, case is not significant. An
        option that specifies a field name is specific to that named field of
        the Info Browser. The available field names are exactly as they appear
        in the Info Browser. When a field is nested within another field, the
        correct name is the two names combined. For example, in C++, the field
        Macros within the field Local would be specified as "Local Macros".

        A field and its subfields may be disabled by specifying levels=0, or
        by specifying the field off, without specifying any option. For example,
        either of the will disable and hide the Metrics field:
          {Metrics}levels=0;
          {Metrics}=off;
        The following option is currently available only without a field name.
          Indent    - this specifies the number of indent spaces to output for
                      each level of a line of text. The default is 2.

        Other options are the same as are displayed when right-clicking on the
        field name in the Understand tool. No defaults are given for these
        options, as the defaults are specific for each language and each field
        name
        An example of a properly formatted option string would be:
          "{Metrics}=off;{calls}levels=-1;{callbys}levels=-1;{references}sort=name"

        The Architectures field is not generated by this command and can be
        generated separately using db.archs(ent)
        """
        return []

    def id(self):  # real signature unknown; restored from __doc__
        """
        ent.id() -> int

        Return a unique numeric identifier for the entity.

        The identifier is not guaranteed to remain constant after the
        database has been updated. An id can be converted back into an
        understand.Ent with db.ent_from_id(id). The id is used for
        comparisons and the hash function.
        """
        return 0

    def kind(self):  # real signature unknown; restored from __doc__
        """
        ent.kind() -> understand.Kind

        Return the kind object for the entity.
        """
        pass

    def kindname(self):  # real signature unknown; restored from __doc__
        """
        ent.kindname() -> string

        Return the simple name for the kind of the entity.

        This is similar to ent.kind().name(), but does not create a Kind
        object.
        """
        return ""

    def language(self):  # real signature unknown; restored from __doc__
        """
        ent.language() -> string

        Return the language of the entity

        Possible values include "Ada", "C++","C#", "Fortran",
        "Java", "Jovial", "Pascal", "Plm", "Python",
        "VHDL" or "Web". C is included with "C++".
        """
        return ""

    def lexer(self, lookup_ents=None, tabstop=None, show_inactive=None,
              expand_macros=None):  # real signature unknown; restored from __doc__
        """
        ent.lexer([lookup_ents [,tabstop [,show_inactive [,expand_macros]]]])
          -> understand.Lexer

        Return a lexer object for the specified file entity. The original
        source file must be readable and unchanged since the last database
        parse. If an error occurs, an UnderstandError will be thrown. Possible
        errors are:
          FileModified         - the file must not be modified since the last
                                 parse
          FileUnreadable       - the file must be readable from the original
                                 location
          UnsupportedLanguage  - the file language is not supported

        The optional paramter lookup_ents is true by default. If it is
        specified false, the lexemes for the constructed lexer will not
        have entity or reference information, but the lexer construction will
        be much faster.

        The optional paramter tabstop is 8 by default. If it is specified it
        must be greater than 0, and is the value to use for tab stops

        The optional parameter show_inactive is true by default. If false,
        inactive lexemes will not be returned.

        The optional parameter expand_macros is false by default. If true,
        and if macro expansion text is stored, lexemes that are macros will
        be replaced with the lexeme stream of the expansion text.
        """
        pass

    def library(self):  # real signature unknown; restored from __doc__
        """
        ent.library() -> string

        Return the library the entity belongs to.

        This will return "" if the entity does not belong to a
        library. Predefined Ada entities such as text_io will bin the
        'Standard' library. Predefined VHDL entities will be in either the
        'std' or 'ieee' libraries.
        """
        return ""

    def longname(self):  # real signature unknown; restored from __doc__
        """
        ent.longname() -> string

        Return the long name of the entity.

        If there is no long name defined, the regular name (ent.name()) is
        returned. Examples of entities with long names include files, c++
        members, and most ada entities.
        """
        return ""

    def metric(self, metriclist):  # real signature unknown; restored from __doc__
        """
        ent.metric(metriclist) -> dict key=string value=metricvalue

        Return the metric value for each item in metriclist

        Metric list must be a tuple or list containing the names of metrics
        as strings. If the metric is not available, it's value will be None.
        """
        return {}

    def metrics(self):  # real signature unknown; restored from __doc__
        """
        ent.metrics() -> list of strings

        Return a list of metric names defined for the entity.
        """
        return []

    def name(self):  # real signature unknown; restored from __doc__
        """
        ent.name() -> string

        Return the shortname for an entity.

        For Java, this may return a name with a single dot in it. Use
        ent.simplename() to obtain the simplest, shortest name possible. This
        is what str() shows.
        """
        return ""

    def parameters(self, shownames=True):  # real signature unknown; restored from __doc__
        """
        ent.parameters(shownames=True) -> string

        Return a string containing the parameters for the entity.

        The optional parameter shownames should be True or False. If it is
        False only the types, not the names, of the parameters are returned.
        There are some language-specific cases where there are no entities in
        the database for certain kinds of parameters. For example, in c++,
        there are no database entities for parameters for functions that are
        only declared, not defined, and there are no database entities for
        parameters for functional macro definitions. This method can be used
        to get some information about these cases. If no parameters are
        available, None is returned.
        """
        return ""

    def parent(self):  # real signature unknown; restored from __doc__
        """
        ent.parent() -> understand.Ent

        Return the parent of the entity or None if none
        """
        pass

    def parsetime(self):  # real signature unknown; restored from __doc__
        """
        ent.parsetime() -> int

        Return the last time the file entity was parse in the database.

        If the entity is not a parse file, it will be 0. The time is in
        Unix/Postix Time
        """
        return 0

    def ref(self, *args, **kwargs):  # real signature unknown; NOTE: unreliably restored from __doc__
        """
        ent.ref([refkindstring [,entkindstring]) -> understand.Ref

        This is the same as ent.refs()[:1]
        """
        pass

    def refs(self, refkindstring=None, entkindstring=None,
             unique=None):  # real signature unknown; restored from __doc__
        """
        ent.refs([refkindstring [,entkindstring [,unique]]]) -> list of understand.Ref

        Return a list of references.

        The optional paramter refkindstring (string) should be a language-
        specific reference filter string. If it is not given, all references
         are returned.

        The optional paramter entkindstring (string) should be a language-
        specific entity filter string that specifies what kind of referenced
        entities should be returned. If it is not given, all references to
        any kind of entity are returned.

        The optional parameter unique (bool) is false by default. If it is
        true, only the first matching reference to each unique entity is
        returned
        """
        return []

    def relname(self):  # real signature unknown; restored from __doc__
        """
        ent.relname() -> string

        Return the relative name of the file entity.

        This is the fullname for the file, minus any root directories that
        are common for all project files. Return None for non-file entities.
        """
        return ""

    def simplename(self):  # real signature unknown; restored from __doc__
        """
        ent.simplename() -> string

        Return the simplename for the entity.

        This is the simplest, shortest name possible for the entity. It is
        generally the same as ent.name() except for languages like Java, for
        which this will not return a name with any dots in it.
        """
        return ""

    def type(self):  # real signature unknown; restored from __doc__
        """
        ent.type() -> string

        Return the type string of the entity.

        This is defined for entity kinds like variables and types, as well as
        entity kinds that have a return type like functions.
        """
        return ""

    def uniquename(self):  # real signature unknown; restored from __doc__
        """
        ent.uniquename() -> string

        Return the unique name of the entity.

        This name is not suitable for use by an end user. Rather, it is a
        means of identifying an entity uniquely in multiple databases, perhaps
        as the source code changes slightly over time. The unique name is
        composed of things like parameters and parent names. So, the some
        code changes will in new uniquenames for the same intrinsic entity.
        Use db.lookup_uniquename() to convert a unqiuename back to an object
        of understand.Ent. This is what repr() shows.
        """
        return ""

    def value(self):  # real signature unknown; restored from __doc__
        """
        ent.value() -> string

        Return the value associated with the entity.

        This is for enumerators, initialized variables, and macros. Not all
        languages are supported.
        """
        return ""

    def __eq__(self, *args, **kwargs):  # real signature unknown
        """ Return self==value. """
        pass

    def __ge__(self, *args, **kwargs):  # real signature unknown
        """ Return self>=value. """
        pass

    def __gt__(self, *args, **kwargs):  # real signature unknown
        """ Return self>value. """
        pass

    def __hash__(self, *args, **kwargs):  # real signature unknown
        """ Return hash(self). """
        pass

    def __init__(self, *args, **kwargs):  # real signature unknown
        pass

    def __le__(self, *args, **kwargs):  # real signature unknown
        """ Return self<=value. """
        pass

    def __lt__(self, *args, **kwargs):  # real signature unknown
        """ Return self<value. """
        pass

    def __ne__(self, *args, **kwargs):  # real signature unknown
        """ Return self!=value. """
        pass

    def __repr__(self, *args, **kwargs):  # real signature unknown
        """ Return repr(self). """
        pass

    def __str__(self, *args, **kwargs):  # real signature unknown
        """ Return str(self). """
        pass


class Kind(object):
    """
    This class represents a kind of an entity or reference. For example,an entity kind might be a "C Header File" and a reference kind
    kind could be "Call." Kindstrings and refkindstrings filters are
    built from these. A filter string may use the tilde "~" to indicate
    the absence of a token, and comma "," to "or" filters together.
    Otherwise, filters are constructed with an "and" relationship. For
    more information on filter strings or a full list of available kinds
    and reference kinds see the Understand Perl API documentation.

    Available methods are:

      understand.Kind.check(kindstring)
      understand.Kind.inv()
      understand.Kind.longname()
      understand.Kind.name()  understand.Kind.__repr__() --longname
      understand.Kind.__str__() --name
    Static Methods:
      understand.Kind.list_entity([entkind])
      understand.Kind.list_reference([refkind])
    """

    def check(self, kindstring):  # real signature unknown; restored from __doc__
        """
        kind.check(kindstring) -> bool

        Return true if the kind matches the filter string kindstring.
        """
        return False

    def inv(self):  # real signature unknown; restored from __doc__
        """
        kind.inv() -> understand.Kind

        The logical inverse of a reference kind. This will throw an
        UnderstandError if called with an entity kind.
        """
        pass

    def list_entity(self, entkind=None):  # real signature unknown; restored from __doc__
        """
        Kind.list_entity([entkind]) (static method)-> list of understand.Kind

        Return the list of entity kinds that match the filter entkind.

        If no entkind is given, all entity kinds are returned. For example,
        to get the list of all c function entity kinds:
          kinds = understand.Kind.list_entity("c function")
        """
        pass

    def list_reference(self, refkind=None):  # real signature unknown; restored from __doc__
        """
        Kind.list_reference([refkind]) (static method)->list of understand.Kind

        Return the list of reference kinds that match the filter refkind.

        If no refkind is given, all reference kinds are returned. For example,
        to get the list of all ada declare reference kinds:
          kinds = understand.Kind.list_entity("ada declare")
        """
        pass

    def longname(self):  # real signature unknown; restored from __doc__
        """
        kind.longname() -> string

        Return the long form of the kind name.

        This is usually more detailed than desired for human reading. It is
        the same as repr(kind)
        """
        return ""

    def name(self):  # real signature unknown; restored from __doc__
        """
        kind.name() -> string

        Return the name of the kind.

        This is the same as str(kind).
        """
        return ""

    def __eq__(self, *args, **kwargs):  # real signature unknown
        """ Return self==value. """
        pass

    def __ge__(self, *args, **kwargs):  # real signature unknown
        """ Return self>=value. """
        pass

    def __gt__(self, *args, **kwargs):  # real signature unknown
        """ Return self>value. """
        pass

    def __hash__(self, *args, **kwargs):  # real signature unknown
        """ Return hash(self). """
        pass

    def __init__(self, *args, **kwargs):  # real signature unknown
        pass

    def __le__(self, *args, **kwargs):  # real signature unknown
        """ Return self<=value. """
        pass

    def __lt__(self, *args, **kwargs):  # real signature unknown
        """ Return self<value. """
        pass

    def __ne__(self, *args, **kwargs):  # real signature unknown
        """ Return self!=value. """
        pass

    def __repr__(self, *args, **kwargs):  # real signature unknown
        """ Return repr(self). """
        pass

    def __str__(self, *args, **kwargs):  # real signature unknown
        """ Return str(self). """
        pass


class Lexeme(object):
    """
    A lexeme is basically a token recieved from an Lexer. Available
    methods are:

      understand.Lexeme.column_begin()
      understand.Lexeme.column_end()
      understand.Lexeme.ent()
      understand.Lexeme.inactive()
      understand.Lexeme.line_begin()
      understand.Lexeme.line_end()
      understand.Lexeme.next()
      understand.Lexeme.previous()
      understand.Lexeme.ref()
      understand.Lexeme.text()
      understand.Lexeme.token()
    """

    def column_begin(self):  # real signature unknown; restored from __doc__
        """
        lexeme.column_begin() -> int

        Return the beginning column number of the lexeme.
        """
        return 0

    def column_end(self):  # real signature unknown; restored from __doc__
        """
        lexeme.column_end() -> int

        Return the ending column number of the lexeme.
        """
        return 0

    def ent(self):  # real signature unknown; restored from __doc__
        """
        lexeme.ent() -> Understand.Ent

        Return the entity associated with the lexeme or None if none.
        """
        pass

    def inactive(self):  # real signature unknown; restored from __doc__
        """
        lexeme.inactive() -> bool

        Return True if the lexeme is part of inactive code.
        """
        return False

    def line_begin(self):  # real signature unknown; restored from __doc__
        """
        lexeme.line_begin() -> int

        Return the beginning line number of the lexeme.
        """
        return 0

    def line_end(self):  # real signature unknown; restored from __doc__
        """
        lexeme.line_end() -> int

        Return the ending line number of the lexeme.
        """
        return 0

    def next(self, ignore_whitespace=None, ignore_comments=None):  # real signature unknown; restored from __doc__
        """
        lexeme.next([ignore_whitespace [,ignore_comments]]) -> understand.Lexeme

        Return the next lexeme, or None if no lexemes remain.
        """
        pass

    def previous(self, ignore_whitespace=None, ignore_comments=None):  # real signature unknown; restored from __doc__
        """
        lexeme.previous([ignore_whitespace [,ignore_comments]]) -> understand.Lexeme

        Return the previous lexeme, or None if beginning of file.
        """
        pass

    def ref(self):  # real signature unknown; restored from __doc__
        """
        lexeme.ref() -> understand.Ref

        Return the reference associated with the lexeme, or None if none.
        """
        pass

    def text(self):  # real signature unknown; restored from __doc__
        """
        lexeme.text() -> string

        Return the text for the lexeme, which may be empty ("").
        """
        return ""

    def token(self):  # real signature unknown; restored from __doc__
        """
        lexeme.token() -> string

        Return the token kind of the lexeme.

        Values include:
          Comment
          Continuation
          EndOfStatemen
          Identifier
          Keyword
          Label
          Literal
          Newline
          Operator
          Preprocessor
          Punctuation
          String
          Whitespace
          Indent
          Dedent
        """
        return ""

    def __init__(self, *args, **kwargs):  # real signature unknown
        pass


class Lexer(object):
    """
    A lexer is a lexical stream generated for a file entity, if the
    original file exists and is unchanged from the last database reparse.
    The first lexeme (token) in the stream can be accessed using
    Lexer.first. A lexer can be iterated over, where each item returned is
    a lexeme. Available methods are:

      understand.Lexer.first()
      understand.Lexer.__iter__()
      undersatnd.Lexer.lexeme(line,column)
      understand.Lexer.lexemes([start_line [,end_line]])
      understand.Lexer.lines()
    """

    def first(self):  # real signature unknown; restored from __doc__
        """
        lexer.first() -> lexeme

        Return the first lexeme for the lexer.
        """
        pass

    def lexeme(self, line, column):  # real signature unknown; restored from __doc__
        """
        lexer.lexeme(line,column) -> understand.Lexeme

        Return the lexeme at the specified line and column.
        """
        pass

    def lexemes(self, start_line=None, end_line=None):  # real signature unknown; restored from __doc__
        """
        lexer.lexemes([start_line [,end_line]]) -> list of understand.Lexeme

        Return all lexemes. If the optional parameters start_line or end_line
        are specified, only the lexemes within these lines are returned.
        """
        return []

    def lines(self):  # real signature unknown; restored from __doc__
        """
        lexer.lines() -> int

        Return the number of lines in the lexer.
        """
        return 0

    def __init__(self, *args, **kwargs):  # real signature unknown
        pass

    def __iter__(self, *args, **kwargs):  # real signature unknown
        """ Implement iter(self). """
        pass


class LexerIter(object):
    # no doc
    def __init__(self, *args, **kwargs):  # real signature unknown
        pass

    def __iter__(self, *args, **kwargs):  # real signature unknown
        """ Implement iter(self). """
        pass

    def __next__(self, *args, **kwargs):  # real signature unknown
        """ Implement next(self). """
        pass


class Metric(object):
    """
    This class is really just a shell for the two methods, description
    and list. The description method will give a description for a metric
    and list will list all the available metrics.
    """

    def description(self, metricname):  # real signature unknown; restored from __doc__
        """
        Metric.description(metricname) (static method) -> string

        Return a description of the metric.

        The parameter metricname is the string name of the metric. This will
        return an empty string if there is no metric for metricname
        """
        pass

    def list(self, kindstring=None):  # real signature unknown; restored from __doc__
        """
        Metric.list([kindstring]) (static method) -> list of strings

        Return a list of metric names.

        The optional parameter kindstring should be a filter string. If given
        only the names of metrics defined for entities that match are returned.
        Otherwise, all possible metric names are returned.
        """
        pass

    def __init__(self, *args, **kwargs):  # real signature unknown
        pass

    @staticmethod  # known case of __new__
    def __new__(*args, **kwargs):  # real signature unknown
        """ Create and return a new object.  See help(type) for accurate signature. """
        pass


class Option(object):
    """
    Available Methods are:
      understand.Option.checkbox(name,text,default)
      understand.Option.choice(name,choices,default)
      understand.Option.integer(name,text,default)
      understand.Option.text(name,text,default)
      understand.Option.lookup(name)
    """

    def checkbox(self, name, text, default):  # real signature unknown; restored from __doc__
        """
        option.checkbox(name,text,default) -> None

        Create a checkbox option.
        """
        pass

    def choice(self, name, text, choices, default):  # real signature unknown; restored from __doc__
        """
        option.choice(name,text,choices,default) -> None

        Create a choice option.
        """
        pass

    def integer(self, name, text, default):  # real signature unknown; restored from __doc__
        """
        option.integer(name,text,default) -> None

        Create an integer option.
        """
        pass

    def lookup(self, name):  # real signature unknown; restored from __doc__
        """
        option.lookup(name) -> Any

        Lookup an option value by name.
        """
        pass

    def text(self, name, text, default):  # real signature unknown; restored from __doc__
        """
        option.text(name,text,default) -> None

        Create a text option.
        """
        pass

    def __init__(self, *args, **kwargs):  # real signature unknown
        pass


class Ref(object):
    """
    A reference object stores an reference between on entity an another.
    Available methods are:

      understand.Ref.column()
      understand.Ref.ent()
      understand.Ref.file()
      undersatnd.Ref.kind()
      understand.Ref.kindname()
      understand.Ref.line()
      understand.Ref.scope()
      understand.Ref.__str__() --kindname ent file(line)
    """

    def column(self):  # real signature unknown; restored from __doc__
        """
        ref.column() -> int

        Return the column in source where the reference occurred.
        """
        return 0

    def ent(self):  # real signature unknown; restored from __doc__
        """
        ref.ent() -> understand.Ent

        Return the entity being referenced.
        """
        pass

    def file(self):  # real signature unknown; restored from __doc__
        """
        ref.file() -> understand.Ent

        Return the file where the reference occurred.
        """
        pass

    def isforward(self):  # real signature unknown; restored from __doc__
        """
        ref.isforward() -> bool

        Return True if the reference is forward.
        """
        return False

    def kind(self):  # real signature unknown; restored from __doc__
        """
        ref.kind() -> understand.Kind

        Return the reference kind.
        """
        pass

    def kindname(self):  # real signature unknown; restored from __doc__
        """
        ref.kindname() -> string

        Return the short name of the reference kind

        This is similar to ref.kind().name(), but does not create anunderstand.Kind object.
        """
        return ""

    def line(self):  # real signature unknown; restored from __doc__
        """
        ref.line() -> int

        Return the line in source where the reference occurred.
        """
        return 0

    def macroexpansion(self):  # real signature unknown; restored from __doc__
        """
        ref.macroexpansion() -> string

        Return the macro expansion text for the refence file, line and column.
        This function may return None if no text is available.
        """
        return ""

    def scope(self):  # real signature unknown; restored from __doc__
        """
        ref.scope() -> understand.Ent

        Return the entity performing the reference.
        """
        pass

    def __init__(self, *args, **kwargs):  # real signature unknown
        pass

    def __repr__(self, *args, **kwargs):  # real signature unknown
        """ Return repr(self). """
        pass

    def __str__(self, *args, **kwargs):  # real signature unknown
        """ Return str(self). """
        pass


class UnderstandError(Exception):
    # no doc
    def __init__(self, *args, **kwargs):  # real signature unknown
        pass

    __weakref__ = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default
    """list of weak references to the object (if defined)"""


class Violation(object):
    """
    Available Methods are:
      understand.Violation.add_fixit_hint(line,column,length[,text])
    """

    def add_fixit_hint(self, line, column, end_line, end_column,
                       text=None):  # real signature unknown; restored from __doc__
        """
        violation.add_fixit_hint(line,column,end_line,end_column[,text]) -> None

        Add a fix-it hint associated with this violation.

        The line, column, end_line, and end_column describe a range of text to be
        replaced in the file. The range can be empty to indicate pure insertion.
        The text is the replacement text. It can be empty for pure removal.
        """
        pass

    def __init__(self, *args, **kwargs):  # real signature unknown
        pass


# variables with complex values

__loader__ = None  # (!) real value is '<_frozen_importlib_external.ExtensionFileLoader object at 0x000001CE33FC3130>'

__spec__ = None  # (!) real value is "ModuleSpec(name='understand', loader=<_frozen_importlib_external.ExtensionFileLoader object at 0x000001CE33FC3130>, origin='D:\\\\program files\\\\SciTools\\\\bin\\\\pc-win64\\\\Python\\\\understand.pyd')"
