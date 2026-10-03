/*
 [The "BSD licence"]
 Copyright (c) 2013 Terence Parr, Sam Harwell
 Copyright (c) 2017 Ivan Kochurkin (upgrade to Java 8)
 All rights reserved.

 Redistribution and use in source and binary forms, with or without
 modification, are permitted provided that the following conditions
 are met:
 1. Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.
 2. Redistributions in binary form must reproduce the above copyright
    notice, this list of conditions and the following disclaimer in the
    documentation and/or other materials provided with the distribution.
 3. The name of the author may not be used to endorse or promote products
    derived from this software without specific prior written permission.

 THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
 IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
 OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
 IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
 INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
 NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
 THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

parser grammar JavaParserLabeled;

options { tokenVocab=JavaLexer; }

/* Java 9-25 additions.

   This grammar was Java 8. Everything newer is *added* without touching what a
   Java 8 file parses to: no existing alternative is reshaped, no label is
   renamed, and no rule gains a second reference to something it already
   references once -- that would turn ctx.IDENTIFIER() or ctx.typeList() into
   a list and break every pass calling it. New syntax therefore lives in new
   rules or new labelled alternatives, and every new rule is defined at the
   end of the file (see JAVA 9-25 there) so no rule index moves.

   Not supported: Java 25 compact source files (top-level methods). They make
   a bare method a valid compilation unit, and metrics/context.py reparses a
   method's own source expecting exactly that to fail before wrapping it.

   Contextual keywords (record, sealed, permits, yield, when, module, ...) are
   IDENTIFIER tokens matched by text through a semantic predicate. The
   predicates are written for the Python target; java8speedy/build.py rewrites
   them for C++. Keep them to the one shape it rewrites:
   self._input.LT(n).text compared with ==/!=, joined by and/or, and a
   compound one wrapped in parentheses -- the Python target writes
   `if not <predicate>:`, so `not a or b` would test the wrong thing.
 */

compilationUnit
    : packageDeclaration? importDeclaration* (typeDeclaration | moduleDeclaration)* EOF
    ;

packageDeclaration
    : annotation* PACKAGE qualifiedName ';'
    ;

importDeclaration
    : IMPORT STATIC? qualifiedName ('.' '*')? ';'
    | IMPORT moduleKeyword qualifiedName ';' // Java 25
    ;

typeDeclaration
    : classOrInterfaceModifier*
      (classDeclaration | enumDeclaration | interfaceDeclaration | annotationTypeDeclaration)
    | ';'
    ;

modifier
    : classOrInterfaceModifier
    | NATIVE
    | SYNCHRONIZED
    | TRANSIENT
    | VOLATILE
    ;

classOrInterfaceModifier
    : annotation
    | PUBLIC
    | PROTECTED
    | PRIVATE
    | STATIC
    | ABSTRACT
    | FINAL    // FINAL for class only -- does not apply to interfaces
    | STRICTFP
    ;

variableModifier
    : FINAL
    | annotation
    ;

classDeclaration
    : (sealedModifier classOrInterfaceModifier*)? CLASS IDENTIFIER typeParameters?
      (EXTENDS typeType)?
      (IMPLEMENTS typeList)?
      permitsClause?
      classBody
    // Java 16. A record *is* a classDeclaration, so every pass that handles a
    // class -- scope chains, Define, Begin/End, Couple -- handles a record.
    // Each element occurs once per alternative, so no accessor turns plural.
    | recordKeyword IDENTIFIER typeParameters? recordHeader (IMPLEMENTS typeList)? classBody
    ;

typeParameters
    : '<' typeParameter (',' typeParameter)* '>'
    ;

typeParameter
    : annotation* IDENTIFIER (EXTENDS annotation* typeBound)?
    ;

typeBound
    : typeType ('&' typeType)*
    ;

enumDeclaration
    : ENUM IDENTIFIER (IMPLEMENTS typeList)? '{' enumConstants? ','? enumBodyDeclarations? '}'
    ;

enumConstants
    : enumConstant (',' enumConstant)*
    ;

enumConstant
    : annotation* IDENTIFIER arguments? classBody?
    ;

enumBodyDeclarations
    : ';' classBodyDeclaration*
    ;

interfaceDeclaration
    : (sealedModifier classOrInterfaceModifier*)? INTERFACE IDENTIFIER typeParameters? (EXTENDS typeList)? permitsClause? interfaceBody
    ;

classBody
    : '{' classBodyDeclaration* '}'
    ;

interfaceBody
    : '{' interfaceBodyDeclaration* '}'
    ;

classBodyDeclaration
    : ';' #classBodyDeclaration0
    | STATIC? block #classBodyDeclaration1
    | modifier* memberDeclaration #classBodyDeclaration2
    ;

memberDeclaration
    : methodDeclaration #memberDeclaration0
    | genericMethodDeclaration #memberDeclaration1
    | fieldDeclaration #memberDeclaration2
    | constructorDeclaration #memberDeclaration3
    | genericConstructorDeclaration #memberDeclaration4
    | interfaceDeclaration #memberDeclaration5
    | annotationTypeDeclaration #memberDeclaration6
    | classDeclaration #memberDeclaration7
    | enumDeclaration #memberDeclaration8
    ;

/* We use rule this even for void methods which cannot have [] after parameters.
   This simplifies grammar and we can consider void to be a type, which
   renders the [] matching as a context-sensitive issue or a semantic check
   for invalid return type after parsing.
 */
methodDeclaration
    // The predicate only refuses `record Name(` and `record Name<`, which is a
    // record header (Java 16) and not a method returning a type named record.
    : {(self._input.LT(1).text != "record" or (self._input.LT(3).text != "(" and self._input.LT(3).text != "<"))}?
      typeTypeOrVoid IDENTIFIER formalParameters ('[' ']')*
      (THROWS qualifiedNameList)?
      methodBody
    ;

methodBody
    : block
    | ';'
    ;

typeTypeOrVoid
    : typeType
    | VOID
    ;

genericMethodDeclaration
    : typeParameters methodDeclaration
    ;

genericConstructorDeclaration
    : typeParameters constructorDeclaration
    ;

constructorDeclaration
    : IDENTIFIER formalParameters (THROWS qualifiedNameList)? constructorBody=block
    | IDENTIFIER constructorBody=block // Java 16 compact canonical constructor
    ;

fieldDeclaration
    : typeType variableDeclarators ';'
    ;

interfaceBodyDeclaration
    : modifier* interfaceMemberDeclaration
    | ';'
    ;

interfaceMemberDeclaration
    : constDeclaration #interfaceMemberDeclaration0
    | interfaceMethodDeclaration #interfaceMemberDeclaration1
    | genericInterfaceMethodDeclaration #interfaceMemberDeclaration2
    | interfaceDeclaration #interfaceMemberDeclaration3
    | annotationTypeDeclaration #interfaceMemberDeclaration4
    | classDeclaration #interfaceMemberDeclaration5
    | enumDeclaration #interfaceMemberDeclaration6
    ;

constDeclaration
    : typeType constantDeclarator (',' constantDeclarator)* ';'
    ;

constantDeclarator
    : IDENTIFIER ('[' ']')* '=' variableInitializer
    ;

// see matching of [] comment in methodDeclaratorRest
// methodBody from Java8
interfaceMethodDeclaration
    : {(self._input.LT(1).text != "record" or (self._input.LT(3).text != "(" and self._input.LT(3).text != "<"))}?
      interfaceMethodModifier* (typeTypeOrVoid | typeParameters annotation* typeTypeOrVoid)
      IDENTIFIER formalParameters ('[' ']')* (THROWS qualifiedNameList)? methodBody
    ;

// Java8
interfaceMethodModifier
    : annotation
    | PUBLIC
    | ABSTRACT
    | DEFAULT
    | STATIC
    | STRICTFP
    ;

genericInterfaceMethodDeclaration
    : typeParameters interfaceMethodDeclaration
    ;

variableDeclarators
    : variableDeclarator (',' variableDeclarator)*
    ;

variableDeclarator
    : variableDeclaratorId ('=' variableInitializer)?
    ;

variableDeclaratorId
    : IDENTIFIER ('[' ']')*
    ;

variableInitializer
    : arrayInitializer #variableInitializer0
    | expression #variableInitializer1
    ;

arrayInitializer
    : '{' (variableInitializer (',' variableInitializer)* (',')? )? '}'
    ;

classOrInterfaceType
    : IDENTIFIER typeArguments? ('.' IDENTIFIER typeArguments?)*
    ;

typeArgument
    : typeType #typeArgument0
    | annotation* '?' ((EXTENDS | SUPER) typeType)? #typeArgument0
    ;

qualifiedNameList
    : qualifiedName (',' qualifiedName)*
    ;

formalParameters
    : '(' formalParameterList? ')'
    ;

formalParameterList
    : formalParameter (',' formalParameter)* (',' lastFormalParameter)? #formalParameterList0
    | lastFormalParameter #formalParameterList1
    ;

formalParameter
    : variableModifier* typeType variableDeclaratorId
    ;

lastFormalParameter
    : variableModifier* typeType annotation* '...' variableDeclaratorId
    ;

qualifiedName
    : IDENTIFIER ('.' IDENTIFIER)*
    ;

literal
    : integerLiteral #literal0
    | floatLiteral #literal1
    | CHAR_LITERAL #literal2
    | STRING_LITERAL #literal3
    | BOOL_LITERAL #literal4
    | NULL_LITERAL #literal5
    | TEXT_BLOCK #literal6 // Java 15
    ;

integerLiteral
    : DECIMAL_LITERAL
    | HEX_LITERAL
    | OCT_LITERAL
    | BINARY_LITERAL
    ;

floatLiteral
    : FLOAT_LITERAL
    | HEX_FLOAT_LITERAL
    ;

// ANNOTATIONS
altAnnotationQualifiedName
    : (IDENTIFIER DOT)* '@' IDENTIFIER
    ;

annotation
    : ('@' qualifiedName | altAnnotationQualifiedName) ('(' ( elementValuePairs | elementValue )? ')')?
    ;

elementValuePairs
    : elementValuePair (',' elementValuePair)*
    ;

elementValuePair
    : IDENTIFIER '=' elementValue
    ;

elementValue
    : expression #elementValue0
    | annotation #elementValue1
    | elementValueArrayInitializer #elementValue2
    ;

elementValueArrayInitializer
    : '{' (elementValue (',' elementValue)*)? (',')? '}'
    ;

annotationTypeDeclaration
    : '@' INTERFACE IDENTIFIER annotationTypeBody
    ;

annotationTypeBody
    : '{' (annotationTypeElementDeclaration)* '}'
    ;

annotationTypeElementDeclaration
    : modifier* annotationTypeElementRest
    | ';' // this is not allowed by the grammar, but apparently allowed by the actual compiler
    ;

annotationTypeElementRest
    : typeType annotationMethodOrConstantRest ';' #annotationTypeElementRest0
    | classDeclaration ';'? #annotationTypeElementRest1
    | interfaceDeclaration ';'? #annotationTypeElementRest2
    | enumDeclaration ';'? #annotationTypeElementRest3
    | annotationTypeDeclaration ';'? #annotationTypeElementRest4
    ;

annotationMethodOrConstantRest
    : annotationMethodRest #annotationMethodOrConstantRest0
    | annotationConstantRest #annotationMethodOrConstantRest1
    ;

annotationMethodRest
    : IDENTIFIER '(' ')' defaultValue?
    ;

annotationConstantRest
    : variableDeclarators
    ;

defaultValue
    : DEFAULT elementValue
    ;

// STATEMENTS / BLOCKS

block
    : '{' blockStatement* '}'
    ;

blockStatement
    : localVariableDeclaration ';' #blockStatement0
    | statement #blockStatement1
    | localTypeDeclaration #blockStatement2
    ;

localVariableDeclaration
    : variableModifier* typeType variableDeclarators
    ;

localTypeDeclaration
    : classOrInterfaceModifier*
      (classDeclaration | interfaceDeclaration | enumDeclaration)
    | ';'
    ;

statement
    : blockLabel=block #statement0
    | ASSERT expression (':' expression)? ';' #statement1
    | IF parExpression statement (ELSE statement)? #statement2
    | FOR '(' forControl ')' statement #statement3
    | WHILE parExpression statement #statement4
    | DO statement WHILE parExpression ';' #statement5
    | TRY block (catchClause+ finallyBlock? | finallyBlock) #statement6
    | TRY resourceSpecification block catchClause* finallyBlock? #statement7
    | SWITCH parExpression '{' switchBlockStatementGroup* switchLabel* '}' #statement8
    | SYNCHRONIZED parExpression block #statement9
    | RETURN expression? ';' #statement10
    | THROW expression ';' #statement11
    | BREAK IDENTIFIER? ';' #statement12
    | CONTINUE IDENTIFIER? ';' #statement13
    | SEMI #statement14
    | {(self._input.LT(1).text == "yield" and self._input.LT(2).text != "=")}? IDENTIFIER expression ';' #statement17 // Java 14
    | SWITCH parExpression '{' switchRule+ '}' #statement18 // Java 14 switch statement with -> rules
    | statementExpression=expression ';' #statement15
    | identifierLabel=IDENTIFIER ':' statement #statement16
    ;

catchClause
    : CATCH '(' variableModifier* catchType IDENTIFIER ')' block
    ;

catchType
    : qualifiedName ('|' qualifiedName)*
    ;

finallyBlock
    : FINALLY block
    ;

resourceSpecification
    : '(' resources ';'? ')'
    ;

resources
    : resource (';' resource)*
    ;

resource
    : variableModifier* classOrInterfaceType variableDeclaratorId '=' expression
    | (THIS '.')? qualifiedName // Java 9: an effectively final variable
    ;

/** Matches cases then statements, both of which are mandatory.
 *  To handle empty cases at the end, we add switchLabel* to statement.
 */
switchBlockStatementGroup
    : switchLabel+ blockStatement+
    ;

switchLabel
    : CASE (constantExpression=expression | enumConstantName=IDENTIFIER) ':'
    | DEFAULT ':'
    | CASE caseConstants ':' // Java 14+
    ;

forControl
    : enhancedForControl #forControl0
    | forInit? ';' expression? ';' forUpdate=expressionList? #forControl1
    ;

forInit
    : localVariableDeclaration #forInit0
    | expressionList #forInit1
    ;

enhancedForControl
    : variableModifier* typeType variableDeclaratorId ':' expression
    ;

// EXPRESSIONS

parExpression
    : '(' expression ')'
    ;

expressionList
    : expression (',' expression)*
    ;

methodCall
    : IDENTIFIER '(' expressionList? ')' #methodCall0
    | THIS '(' expressionList? ')' #methodCall1
    | SUPER '(' expressionList? ')' #methodCall2
    ;

expression
    : primary #expression0
    | expression bop='.'
      ( IDENTIFIER
      | methodCall
      | THIS
      | NEW nonWildcardTypeArguments? innerCreator
      | SUPER superSuffix
      | explicitGenericInvocation
      ) #expression1
    | expression '[' expression ']' #expression2
    | methodCall #expression3
    | NEW creator #expression4
    | '(' annotation* typeType ')' expression #expression5
    | expression postfix=('++' | '--') #expression6
    | prefix=('+'|'-'|'++'|'--') expression #expression7
    | prefix=('~'|'!') expression #expression8
    | expression bop=('*'|'/'|'%') expression #expression9
    | expression bop=('+'|'-') expression #expression10
    | expression ('<' '<' | '>' '>' '>' | '>' '>') expression #expression11
    | expression bop=('<=' | '>=' | '>' | '<') expression #expression12
    | expression bop=INSTANCEOF typeType #expression13
    | expression bop=INSTANCEOF pattern #expression27 // Java 16
    | expression bop=('==' | '!=') expression #expression14
    | expression bop='&' expression #expression15
    | expression bop='^' expression #expression16
    | expression bop='|' expression #expression17
    | expression bop='&&' expression #expression18
    | expression bop='||' expression #expression19
    | <assoc=right> expression bop='?' expression ':' expression #expression20
    | <assoc=right> expression
      bop=('=' | '+=' | '-=' | '*=' | '/=' | '&=' | '|=' | '^=' | '>>=' | '>>>=' | '<<=' | '%=')
      expression #expression21
    | lambdaExpression #expression22 // Java8

    // Java 8 methodReference
    | expression '::' typeArguments? IDENTIFIER #expression23
    | typeType '::' (typeArguments? IDENTIFIER | NEW) #expression24
    | classType '::' typeArguments? NEW #expression25
    | switchExpression #expression26 // Java 14
    ;

// Java8
lambdaExpression
    : lambdaParameters '->' lambdaBody
    ;

// Java8
lambdaParameters
    : IDENTIFIER #lambdaParameters0
    | '(' formalParameterList? ')' #lambdaParameters1
    | '(' IDENTIFIER (',' IDENTIFIER)* ')' #lambdaParameters2
    ;

// Java8
lambdaBody
    : expression #lambdaBody0
    | block #lambdaBody1
    ;

primary
    : '(' expression ')' #primary0
    | THIS #primary1
    | SUPER #primary2
    | literal #primary3
    | IDENTIFIER #primary4
    | typeTypeOrVoid '.' CLASS #primary5
    | nonWildcardTypeArguments (explicitGenericInvocationSuffix | THIS arguments) #primary6
    ;

classType
    : (classOrInterfaceType '.')? annotation* IDENTIFIER typeArguments?
    ;

creator
    : nonWildcardTypeArguments createdName classCreatorRest #creator0
    | createdName (arrayCreatorRest | classCreatorRest) #creator1
    ;

createdName
    : IDENTIFIER typeArgumentsOrDiamond? ('.' IDENTIFIER typeArgumentsOrDiamond?)* #createdName0
    | primitiveType #createdName1
    ;

innerCreator
    : IDENTIFIER nonWildcardTypeArgumentsOrDiamond? classCreatorRest
    ;

arrayCreatorRest
    : '[' (']' ('[' ']')* arrayInitializer | expression ']' ('[' expression ']')* ('[' ']')*)
    ;

classCreatorRest
    : arguments classBody?
    ;

explicitGenericInvocation
    : nonWildcardTypeArguments explicitGenericInvocationSuffix
    ;

typeArgumentsOrDiamond
    : '<' '>'
    | typeArguments
    ;

nonWildcardTypeArgumentsOrDiamond
    : '<' '>'
    | nonWildcardTypeArguments
    ;

nonWildcardTypeArguments
    : '<' typeList '>'
    ;

typeList
    : typeType (',' typeType)*
    ;

typeType
    : annotation* (classOrInterfaceType | primitiveType) (annotation* '[' ']')*
    ;

primitiveType
    : BOOLEAN
    | CHAR
    | BYTE
    | SHORT
    | INT
    | LONG
    | FLOAT
    | DOUBLE
    ;

typeArguments
    : '<' typeArgument (',' typeArgument)* '>'
    ;

superSuffix
    : arguments #superSuffix0
    | '.' IDENTIFIER arguments? #superSuffix1
    ;

explicitGenericInvocationSuffix
    : SUPER superSuffix #explicitGenericInvocationSuffix0
    | IDENTIFIER arguments #explicitGenericInvocationSuffix1
    ;

arguments
    : '(' expressionList? ')'
    ;

/* JAVA 9-25

   Every rule below is newer than Java 8, and they are all defined here, after
   the last Java 8 rule, on purpose: a rule's index is its position in this
   file, and set_setby.py and setinit_setinitby.py compare getRuleIndex()
   against integers. Defining a rule anywhere above this line renumbers every
   rule after it.
 */

moduleKeyword
    : {self._input.LT(1).text == "module"}? IDENTIFIER
    ;

/* Java 17. Kept out of classOrInterfaceModifier on purpose: there it would
   compete with the return type of every method in the member-modifier loop,
   and ANTLR defers predicates until a conflict, so it would read each method
   body to the end before deciding. Here it sits directly before class or
   interface, which settles it on the next token. Modifiers written before it
   stay in the enclosing rule; modifiers after it land in this rule.
 */
sealedModifier
    : {self._input.LT(1).text == "sealed"}? IDENTIFIER
    | {(self._input.LT(1).text == "non" and self._input.LT(2).text == "-" and self._input.LT(3).text == "sealed")}? IDENTIFIER '-' IDENTIFIER
    ;

permitsClause
    : {self._input.LT(1).text == "permits"}? IDENTIFIER typeList
    ;

recordKeyword
    : {self._input.LT(1).text == "record"}? IDENTIFIER
    ;

recordHeader
    : '(' (recordComponent (',' recordComponent)*)? ')'
    ;

recordComponent
    : annotation* typeType (annotation* '...')? IDENTIFIER
    ;

moduleDeclaration
    : annotation* ({self._input.LT(1).text == "open"}? IDENTIFIER)? moduleKeyword qualifiedName
      '{' moduleDirective* '}'
    ;

moduleDirective
    : {self._input.LT(1).text == "requires"}? IDENTIFIER requiresModifier* qualifiedName ';'
    | {(self._input.LT(1).text == "exports" or self._input.LT(1).text == "opens")}? IDENTIFIER qualifiedName
      ({self._input.LT(1).text == "to"}? IDENTIFIER qualifiedName (',' qualifiedName)*)? ';'
    | {self._input.LT(1).text == "uses"}? IDENTIFIER qualifiedName ';'
    | {self._input.LT(1).text == "provides"}? IDENTIFIER qualifiedName
      {self._input.LT(1).text == "with"}? IDENTIFIER qualifiedName (',' qualifiedName)* ';'
    ;

requiresModifier
    : {(self._input.LT(1).text == "transitive" and self._input.LT(2).text != ";")}? IDENTIFIER
    | STATIC
    ;

// What a Java 14+ case can hold that `CASE expression` cannot: several
// constants, `null, default`, or patterns with an optional guard.
caseConstants
    : expression (',' expression)+
    | NULL_LITERAL ',' DEFAULT
    | pattern (',' pattern)* guard?
    ;

guard
    : {self._input.LT(1).text == "when"}? IDENTIFIER expression
    ;

// Java 14 switch as an expression (expression26): -> rules, or the Java 8
// colon body with yield inside it. statement18 is the -> form as a statement;
// the colon form as a statement stays statement8.
switchExpression
    : SWITCH parExpression '{' switchRule+ '}'
    | SWITCH parExpression '{' switchBlockStatementGroup* switchLabel* '}'
    ;

switchRule
    : switchRuleLabel '->' statement
    ;

switchRuleLabel
    : CASE (expression | caseConstants)
    | DEFAULT
    ;

// Java 16 type pattern, Java 21 record pattern, Java 22 unnamed `_`.
// A type pattern declares a local, and Understand models it as one (Define,
// Set Init, Typed), so it is spelled as a localVariableDeclaration: every pass
// that already handles a local handles a pattern variable unchanged.
pattern
    : localVariableDeclaration
    | typeType '(' (pattern (',' pattern)*)? ')'
    | {self._input.LT(1).text == "_"}? IDENTIFIER
    ;
