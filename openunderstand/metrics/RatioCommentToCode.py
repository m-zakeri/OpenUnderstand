from antlr4 import *
from gen.javaLabeled.JavaLexer import JavaLexer


def main(input_address):
    #Stream file
    file_stream = FileStream(r""+input_address)
    #lex and tokenize
    lexer = JavaLexer(file_stream)
    token = lexer.nextToken()
    current_line = lexer.line
    last_line = -1
    comments = 0
    code = 0
    #calculating number of lines of comments
    while token.type != Token.EOF:
        #check single line or multiline comments
        if current_line != last_line or token.type == lexer.LINE_COMMENT or token.type == lexer.COMMENT:
            #multiline
            if token.type == lexer.COMMENT:
                comments += 1
                last_line = lexer.line
                comments += token.text.count('\n')
            #single line
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