"""speedy-antlr C++ parse accelerator.

Nothing here is importable until ``build.py`` has been run -- it compiles
``sa_javalabeled_cpp_parser`` into this directory from ``grammars/*.g4``.
Consumers should go through ``openunderstand.utils.antler_parser``, which falls
back to the pure-Python parser when the extension is absent.
"""
