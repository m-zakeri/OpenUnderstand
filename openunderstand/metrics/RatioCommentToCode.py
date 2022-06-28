from antlr4 import *
from gen.javaLabeled.JavaLexer import JavaLexer


def main(input_address):
    file_stream = FileStream(r""+input_address)
    lexer = JavaLexer(file_stream)
    token = lexer.nextToken()
    current_line = lexer.line
    last_line = -1
    comments = 0
    code = 0
    while token.type != Token.EOF:
        if current_line != last_line or token.type == lexer.LINE_COMMENT or token.type == lexer.COMMENT:
            if token.type == lexer.COMMENT:
                comments += 1
                last_line = lexer.line
                comments += token.text.count('\n')
            elif token.type == lexer.LINE_COMMENT:
                comments += 1
                last_line = lexer.line
            else:
                code += 1
                last_line = lexer.line
        current_line = lexer.line
        token = lexer.nextToken()
    print(comments/code)


if __name__ == "__main__":
    pass
    #main('.//javapackage//c.java')