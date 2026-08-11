from antlr4 import *
from openunderstand.metrics import context
from openunderstand.gen.javaLabeled.JavaLexer import JavaLexer
from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from openunderstand.metrics.max_inheritance import FindAllInheritances
from openunderstand.metrics.max_inheritance import FindAllClasses
from openunderstand.metrics.max_nesting import MaxNesting
from openunderstand.metrics.min_max_essential_knots import MinEssentialKnots
import os
from fnmatch import fnmatch
import argparse


def get_max_inheritance(inheritances, key):
    current_classs = key
    level = 0
    while True:
        if not current_classs in inheritances.keys():
            break
        elif len(inheritances[current_classs]) == 0:
            break
        else:
            level += 1
            current_classs = inheritances[current_classs][0]

    return level


def _parse(ent_model):
    return context.parse(ent_model.contents() or "")


def max_inheritance_tree(ent_model):
    """MaxInheritanceTree for one entity.

    api.py dispatched this to get_max_inheritance(), which takes an
    inheritance map and a class name, not an entity -- so asking for the
    metric raised TypeError. The map has to be built first.
    """
    tree = _parse(ent_model)
    walker = ParseTreeWalker()
    finder = FindAllClasses()
    walker.walk(t=tree, listener=finder)
    classes = {name: [] for name in finder.class_names}
    inheritances = FindAllInheritances(classes)
    walker.walk(t=tree, listener=inheritances)
    # +1 for java.lang.Object: every class has it as an ancestor, and
    # Understand counts that level even though no JDK is analysed here.
    return get_max_inheritance(inheritances.classes, ent_model.name()) + 1


def max_nesting(ent_model):
    """MaxNesting for one entity.

    MaxNesting is a listener class, and api.py called it as MaxNesting(ent),
    which its zero-argument constructor rejected.

    Walked over context.parse_entity() rather than a plain compilationUnit()
    parse of the entity's contents: a *method's* source is not a compilation
    unit, so that parse produced a tree with no statements in it and every
    method's MaxNesting came out 0. Understand reports 2 for Cookie.escape.
    parse_entity() wraps a member in a synthetic class so it parses, and the
    wrapper adds no nesting of its own because only statements are counted.
    """
    return context.walk_entity(ent_model, MaxNesting()).max_nesting


def getListOfFiles(dirName):
    listOfFile = os.listdir(dirName)
    allFiles = list()
    for entry in listOfFile:
        # Create full path
        fullPath = os.path.join(dirName, entry)
        if os.path.isdir(fullPath):
            allFiles = allFiles + getListOfFiles(fullPath)
        elif fnmatch(fullPath, "*.java"):
            allFiles.append(fullPath)

    return allFiles


def get_knot_inheritance_nested(ent_model=None):

    classes = {}
    class_names = []

    try:
        # at first we should Stream text from input file
        inputfile = InputStream(ent_model.contents(), encoding="utf8")
        # then we must use lexer
        lex = JavaLexer(inputfile)
        # then we should tokenize that
        toked = CommonTokenStream(lex)
        # at last we should parse tokenized
        parsed = JavaParserLabeled(toked)
        ptree = parsed.compilationUnit()

        listener = FindAllClasses()
        treewalker = ParseTreeWalker()
        treewalker.walk(t=ptree, listener=listener)
        for n in listener.class_names:
            class_names.append(n)

    except Exception as e:
        print("An Error occurred in file:" + ent_model.longname() + "\n" + str(e))

    for c in class_names:
        classes.update({c: []})

    inputfile = InputStream(ent_model.contents(), encoding="utf8")
    # then we must use lexer
    lex = JavaLexer(inputfile)
    # then we should tokenize that
    toked = CommonTokenStream(lex)
    # at last we should parse tokenized
    parsed = JavaParserLabeled(toked)
    ptree = parsed.compilationUnit()
    listener2 = FindAllInheritances(classes)
    treewalker2 = ParseTreeWalker()
    treewalker2.walk(t=ptree, listener=listener2)

    classes = listener2.classes

    max_inheritances = {}
    for key in classes.keys():
        max_inheritances.update({key: get_max_inheritance(classes, key)})

    print(f"Class Name = {max_inheritances}")

    inputfile = FileStream(ent_model.contents(), encoding="utf8")
    # then we must use lexer
    lex = JavaLexer(inputfile)
    # then we should tokenize that
    toked = CommonTokenStream(lex)
    # at last we should parse tokenized
    parsed = JavaParserLabeled(toked)
    ptree = parsed.compilationUnit()
    listener3 = MaxNesting()
    treewalker3 = ParseTreeWalker()
    treewalker3.walk(t=ptree, listener=listener3)
    print("Max Nesting of", file_address, " is: ", listener3.max_nesting)

    inputfile = InputStream(ent_model.contents(), encoding="utf8")
    # then we must use lexer
    lex = JavaLexer(inputfile)
    # then we should tokenize that
    toked = CommonTokenStream(lex)
    # at last we should parse tokenized
    parsed = JavaParserLabeled(toked)
    ptree = parsed.compilationUnit()
    listener4 = MinEssentialKnots()
    treewalker4 = ParseTreeWalker()
    treewalker4.walk(t=ptree, listener=listener4)
    return listener4.counter
