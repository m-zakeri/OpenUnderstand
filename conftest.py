import sys
import types

# Create a fake 'gen' package so utilities.py can be imported
# without the real ANTLR-generated parser modules.
if "gen" not in sys.modules:
    gen_pkg = types.ModuleType("gen")
    gen_pkg.__path__ = []
    sys.modules["gen"] = gen_pkg

    java_labeled_pkg = types.ModuleType("gen.javaLabeled")
    java_labeled_pkg.__path__ = []
    sys.modules["gen.javaLabeled"] = java_labeled_pkg

    java_parser_mod = types.ModuleType("gen.javaLabeled.JavaParserLabeled")
    java_parser_mod.JavaParserLabeled = object
    sys.modules["gen.javaLabeled.JavaParserLabeled"] = java_parser_mod