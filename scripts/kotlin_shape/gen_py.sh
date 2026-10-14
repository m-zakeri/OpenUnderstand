#!/bin/bash
# Python parser from the repo grammar, for the shape check
cd "$(dirname "$0")" && rm -rf pyparser && mkdir pyparser && cp ../../grammars/kotlin/*.g4 pyparser/ && cd pyparser && java -jar /home/y/Desktop/codes/personal/OpenUnderstand/openunderstand/gen/java8speedy/.build-cache/antlr-4.13.2-complete.jar -Dlanguage=Python3 -no-visitor -no-listener KotlinLexer.g4 KotlinParser.g4 2>&1 | grep -v '^$'
