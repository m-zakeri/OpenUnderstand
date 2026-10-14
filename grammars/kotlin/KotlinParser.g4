// OpenUnderstand modifications to antlr/grammars-v4 kotlin/kotlin-formal (see README.md):
// Kotlin 2.x syntax added up to 2.4 (context parameters, explicit backing fields, when guards,
// multi-dollar strings, name-based destructuring, ...). Edit the grammar, not generated code.
/**
 * Kotlin Grammar for ANTLR v4
 *
 * Based on:
 * jetbrains.github.io/kotlin-spec/#_grammars_and_parsing
 * and
 * kotlinlang.org/docs/reference/grammar.html
 *
 * Tested on
 * github.com/JetBrains/kotlin/tree/master/compiler/testData/psi
 * (stale link)
 */

// $antlr-format alignTrailingComments true, columnLimit 150, minEmptyLines 1, maxEmptyLinesToKeep 1, reflowComments false, useTab false
// $antlr-format allowShortRulesOnASingleLine false, allowShortBlocksOnASingleLine true, alignSemicolons hanging, alignColons hanging

parser grammar KotlinParser;

options {
    tokenVocab = KotlinLexer;
}

kotlinFile
    : shebangLine? NL* fileAnnotation* packageHeader importList topLevelObject* EOF
    ;

script
    : shebangLine? NL* fileAnnotation* packageHeader importList (statement semi)* EOF
    ;

fileAnnotation
    : '@file' NL* ':' NL* ('[' unescapedAnnotation+ ']' | unescapedAnnotation) NL*
    ;

packageHeader
    : ('package' identifier semi?)?
    ;

importList
    : importHeader*
    ;

importHeader
    : 'import' identifier ('.' '*' | importAlias)? semi?
    ;

importAlias
    : 'as' simpleIdentifier
    ;

topLevelObject
    : (memberPropertyDeclaration | declaration) semis?
    ;

classDeclaration
    : modifiers? ('class' | 'fun'? 'interface') NL* simpleIdentifier (NL* typeParameters)? (
        NL* primaryConstructor
    )? (NL* ':' NL* delegationSpecifiers)? (NL* typeConstraints)? (
        NL* classBody
        | NL* enumClassBody
    )?
    ;

primaryConstructor
    : (modifiers? 'constructor' NL*)? classParameters
    ;

classParameters
    : '(' NL* (classParameter (NL* ',' NL* classParameter)*)? NL* ','? ')'
    ;

classParameter
    : modifiers? ('val' | 'var')? NL* simpleIdentifier ':' NL* type_ (NL* '=' NL* expression)?
    ;

delegationSpecifiers
    : annotatedDelegationSpecifier (NL* ',' NL* annotatedDelegationSpecifier)*
    ;

annotatedDelegationSpecifier
    : annotation* NL* delegationSpecifier
    ;

delegationSpecifier
    : constructorInvocation
    | explicitDelegation
    | userType
    | typeModifiers? functionType
    ;

constructorInvocation
    : userType valueArguments
    ;

explicitDelegation
    : (userType | functionType) NL* 'by' NL* delegateExpression
    ;

delegateExpression // no trailing lambda: it would be read as the class body
    : primaryExpression delegateSuffix* (NL* asOperator NL* type_)*
    ;

delegateSuffix
    : postfixUnaryOperator
    | typeArguments? valueArguments
    | indexingSuffix
    | navigationSuffix
    ;

classBody
    : '{' NL* classMemberDeclarations NL* '}'
    ;

classMemberDeclarations
    : (classMemberDeclaration semis?)*
    ;

classMemberDeclaration
    : memberPropertyDeclaration
    | declaration
    | companionObject
    | companionBlock
    | anonymousInitializer
    | secondaryConstructor
    ;

anonymousInitializer
    : 'init' NL* block
    ;

secondaryConstructor
    : modifiers? 'constructor' NL* functionValueParameters (NL* ':' NL* constructorDelegationCall)? NL* block?
    ;

constructorDelegationCall
    : 'this' NL* valueArguments
    | 'super' NL* valueArguments
    ;

enumClassBody
    : '{' NL* enumEntries? (NL* ';' NL* classMemberDeclarations)? NL* '}'
    ;

enumEntries
    : enumEntry (NL* ',' NL* enumEntry)* NL* ','?
    ;

enumEntry
    : (modifiers NL*)? simpleIdentifier (NL* valueArguments)? (NL* classBody)?
    ;

functionDeclaration
    : modifiers? 'fun' (NL* typeParameters)? (NL* receiverType NL* '.')? NL* simpleIdentifier NL* functionValueParameters (
        NL* ':' NL* type_
    )? (NL* typeConstraints)? (NL* functionBody)?
    ;

functionValueParameters
    : '(' NL* (functionValueParameter (NL* ',' NL* functionValueParameter)*)? NL* ','? ')'
    ;

functionValueParameter
    : modifiers? parameter (NL* '=' NL* expression)?
    ;

parameter
    : simpleIdentifier NL* ':' NL* type_
    ;

setterParameter
    : simpleIdentifier NL* (':' NL* type_)?
    ;

functionBody
    : block
    | '=' NL* expression
    ;

objectDeclaration
    : modifiers? 'object' NL* simpleIdentifier (NL* ':' NL* delegationSpecifiers)? (NL* classBody)?
    ;

companionBlock
    : modifiers? 'companion' NL* classBody
    ;

companionObject
    : modifiers? 'companion' NL* 'object' (NL* simpleIdentifier)? (
        NL* ':' NL* delegationSpecifiers
    )? (NL* classBody)?
    ;

memberPropertyDeclaration
    : propertyDeclarationHead NL* explicitBackingField propertyAccessors?
    ;

explicitBackingField
    : 'field' (NL* ':' NL* type_)? (NL* '=' NL* expression)?
    ;

propertyDeclaration
    : propertyDeclarationHead propertyAccessors?
    ;

propertyDeclarationHead
    : modifiers? ('val' | 'var') (NL* typeParameters)? (NL* receiverType NL* '.')? (
        NL* (multiVariableDeclaration | variableDeclaration)
    ) (NL* typeConstraints)? (NL* ('=' NL* expression | propertyDelegate))?
    ;

propertyAccessors
    : (NL | ';')* getter ((NL | ';')* setter)?
    | (NL | ';')* setter ((NL | ';')* getter)?
    ;

multiVariableDeclaration
    : '(' NL* destructuringEntry (NL* ',' NL* destructuringEntry)* NL* ','? NL* ')'
    | '[' NL* destructuringEntry (NL* ',' NL* destructuringEntry)* NL* ','? NL* ']'
    ;

destructuringEntry
    : (('val' | 'var') NL*)? variableDeclaration (NL* '=' NL* simpleIdentifier)?
    ;

variableDeclaration
    : annotation* NL* simpleIdentifier (NL* ':' NL* type_)?
    ;

propertyDelegate
    : 'by' NL* expression
    ;

getter
    : modifiers? 'get'
    | modifiers? 'get' NL* '(' NL* ')' (NL* ':' NL* type_)? NL* functionBody
    ;

setter
    : modifiers? 'set'
    | modifiers? 'set' NL* '(' (annotation | parameterModifier)* setterParameter ')' (
        NL* ':' NL* type_
    )? NL* functionBody
    ;

typeAlias
    : modifiers? 'typealias' NL* simpleIdentifier (NL* typeParameters)? NL* '=' NL* type_
    ;

typeParameters
    : '<' NL* typeParameter (NL* ',' NL* typeParameter)* NL* (',' NL*)? '>'
    ;

typeParameter
    : typeParameterModifiers? NL* simpleIdentifier (NL* ':' NL* type_)?
    ;

typeParameterModifiers
    : typeParameterModifier+
    ;

typeParameterModifier
    : reificationModifier NL*
    | varianceModifier NL*
    | annotation
    ;

type_
    : typeModifiers? (parenthesizedType | nullableType | typeReference | functionType) (NL* '&' NL* type_)?
    ;

typeModifiers
    : typeModifier+
    ;

typeModifier
    : annotation
    | 'suspend' NL*
    | contextParameters NL*
    ;

parenthesizedType
    : '(' NL* type_ NL* ')'
    ;

nullableType
    : (typeReference | parenthesizedType) NL* quest+
    ;

typeReference
    : userType
    | 'dynamic' // do we need a separate dynamic support here?
    ;

functionType
    : (receiverType NL* '.' NL*)? functionTypeParameters NL* '->' NL* type_
    ;

receiverType
    : typeModifiers? (parenthesizedType | nullableType | typeReference)
    ;

userType
    : simpleUserType (NL* '.' NL* simpleUserType)*
    ;

parenthesizedUserType
    : '(' NL* userType NL* ')'
    | '(' NL* parenthesizedUserType NL* ')'
    ;

simpleUserType
    : simpleIdentifier (NL* typeArguments)?
    ;

functionTypeParameters
    : '(' NL* (parameter | type_)? (NL* ',' NL* (parameter | type_))* NL* ')'
    ;

typeConstraints
    : 'where' NL* typeConstraint (NL* ',' NL* typeConstraint)*
    ;

typeConstraint
    : annotation* simpleIdentifier NL* ':' NL* type_
    ;

block
    : '{' NL* statements NL* '}'
    ;

statements
    : (statement ((';' | NL)+ statement)* semis?)?
    ;

statement
    : label* (declaration | annotation* (destructuringAssignment | loopStatement) | expressionStatement)
    ;

declaration
    : classDeclaration
    | objectDeclaration
    | functionDeclaration
    | propertyDeclaration
    | typeAlias
    ;

destructuringAssignment
    : multiVariableDeclaration NL* '=' NL* expression
    ;

expressionStatement
    : expression (('=' | assignmentAndOperator) NL* expression)?
    ;

expression
    : disjunction
    ;

disjunction
    : conjunction (NL* '||' NL* conjunction)*
    ;

conjunction
    : equality (NL* '&&' NL* equality)*
    ;

equality
    : comparison (/* NO NL! */ equalityOperator NL* comparison)*
    ;

comparison
    : infixOperation (/* NO NL! */ comparisonOperator NL* infixOperation)?
    ;

infixOperation
    : elvisExpression (/* NO NL! */ inOperator NL* elvisExpression | isOperator NL* type_)*
    ;

elvisExpression
    : infixFunctionCall (NL* elvis NL* infixFunctionCall)*
    ;

infixFunctionCall
    : rangeExpression (/* NO NL! */ simpleIdentifier NL* rangeExpression)*
    ;

rangeExpression
    : additiveExpression (/* NO NL! */ ('..' | '..<') NL* additiveExpression)*
    ;

additiveExpression
    : multiplicativeExpression (/* NO NL! */ additiveOperator NL* multiplicativeExpression)*
    ;

multiplicativeExpression
    : asExpression (/* NO NL! */ multiplicativeOperator NL* asExpression)*
    ;

asExpression
    : prefixUnaryExpression (NL* asOperator NL* type_)*
    ;

prefixUnaryExpression
    : unaryPrefix* (postfixUnaryExpression | jumpExpression)
    ;

unaryPrefix
    : annotation
    | label
    | prefixUnaryOperator NL*
    ;

postfixUnaryExpression
    : primaryExpression postfixUnarySuffix*
    ;

postfixUnarySuffix
    : postfixUnaryOperator
    | typeArguments
    | callSuffix
    | indexingSuffix
    | navigationSuffix
    ;

indexingSuffix
    : '[' NL* expression (NL* ',' NL* expression)* NL* ']'
    ;

navigationSuffix
    : NL* memberAccessOperator NL* (simpleIdentifier | parenthesizedExpression | 'class')
    ;

callSuffix
    : typeArguments? (valueArguments annotatedLambda? | annotatedLambda)
    ;

annotatedLambda
    : annotation* label? lambdaLiteral
    ;

valueArguments
    : '(' NL* ')'
    | '(' NL* valueArgument (NL* ',' NL* valueArgument)* NL* ','? ')'
    ;

typeArguments
    : '<' NL* typeProjection (NL* ',' NL* typeProjection)* NL* (',' NL*)? '>'
    ;

typeProjection
    : typeProjectionModifiers? type_
    | '*'
    ;

typeProjectionModifiers
    : typeProjectionModifier+
    ;

typeProjectionModifier
    : varianceModifier NL*
    | annotation
    ;

valueArgument
    : annotation? NL* (simpleIdentifier NL* '=' NL*)? '*'? NL* expression
    ;

primaryExpression
    : parenthesizedExpression
    | literalConstant
    | stringLiteral
    | simpleIdentifier
    | callableReference
    | functionLiteral
    | objectLiteral
    | collectionLiteral
    | thisExpression
    | superExpression
    | ifExpression
    | whenExpression
    | tryExpression
    ;

parenthesizedExpression
    : '(' NL* expression NL* ')'
    ;

collectionLiteral
    : '[' NL* expression (NL* ',' NL* expression)* NL* ','? ']'
    | '[' NL* ']'
    ;

literalConstant
    : BooleanLiteral
    | IntegerLiteral
    | HexLiteral
    | BinLiteral
    | CharacterLiteral
    | RealLiteral
    | NullLiteral
    | LongLiteral
    ;

stringLiteral
    : lineStringLiteral
    | multiLineStringLiteral
    ;

lineStringLiteral
    : QUOTE_OPEN (lineStringContent | lineStringExpression)* QUOTE_CLOSE
    ;

multiLineStringLiteral // why is lineStringLiteral here? there is no escaping in multiline strings
    : TRIPLE_QUOTE_OPEN (multiLineStringContent | multiLineStringExpression | MultiLineStringQuote)* TRIPLE_QUOTE_CLOSE
    ;

lineStringContent
    : LineStrText
    | LineStrEscapedChar
    | LineStrRef
    ;

lineStringExpression
    : LineStrExprStart NL* expression NL* '}'
    ;

multiLineStringContent
    : MultiLineStrText
    | MultiLineStringQuote
    | MultiLineStrRef
    ;

multiLineStringExpression
    : MultiLineStrExprStart NL* expression NL* '}'
    ;

lambdaLiteral // anonymous functions?
    : LCURL NL* statements NL* RCURL
    | LCURL NL* lambdaParameters? NL* ARROW NL* statements NL* '}'
    ;

lambdaParameters
    : lambdaParameter (NL* COMMA NL* lambdaParameter)* COMMA?
    ;

lambdaParameter
    : variableDeclaration
    | multiVariableDeclaration (NL* COLON NL* type_)?
    ;

anonymousFunction
    : contextParameters? NL* 'fun' (NL* type_ NL* '.')? NL* anonymousFunctionParameters (NL* ':' NL* type_)? (
        NL* typeConstraints
    )? (NL* functionBody)?
    ;

anonymousFunctionParameters
    : '(' NL* (anonymousFunctionParameter (NL* ',' NL* anonymousFunctionParameter)*)? NL* ','? ')'
    ;

anonymousFunctionParameter
    : modifiers? simpleIdentifier (NL* ':' NL* type_)? (NL* '=' NL* expression)?
    ;

functionLiteral
    : lambdaLiteral
    | anonymousFunction
    ;

objectLiteral
    : 'object' NL* ':' NL* delegationSpecifiers (NL* classBody)?
    | 'object' NL* classBody
    ;

thisExpression
    : 'this'
    | THIS_AT
    ;

superExpression
    : 'super' ('<' NL* type_ NL* '>')? ('@' simpleIdentifier)?
    | SUPER_AT
    ;

controlStructureBody
    : block
    | controlStatement
    ;

controlStatement
    : label* (annotation* (destructuringAssignment | loopStatement) | expressionStatement)
    ;

ifExpression
    : 'if' NL* '(' NL* expression NL* ')' NL* controlStructureBody (
        ';'? NL* 'else' NL* controlStructureBody
    )?
    | 'if' NL* '(' NL* expression NL* ')' NL* (';' NL*)? 'else' NL* controlStructureBody
    ;

whenExpression
    : 'when' NL* ('(' NL* whenSubject NL* ')')? NL* '{' (NL | ';')* (whenEntry (NL | ';')*)* '}'
    ;

whenSubject
    : annotation* 'val' NL* variableDeclaration NL* '=' NL* expression
    | expression
    ;

whenGuard
    : 'if' NL* expression
    ;

whenEntry
    : whenCondition (NL* ',' NL* whenCondition)* (NL* ',')? (NL* whenGuard)? NL* '->' NL* controlStructureBody
    | 'else' NL* '->' NL* controlStructureBody
    ;

whenCondition
    : expression
    | rangeTest
    | typeTest
    ;

rangeTest
    : inOperator NL* expression
    ;

typeTest
    : isOperator NL* type_
    ;

tryExpression
    : 'try' NL* block ((NL* catchBlock)+ (NL* finallyBlock)? | NL* finallyBlock)
    ;

catchBlock
    : 'catch' NL* '(' annotation* simpleIdentifier ':' userType ')' NL* block
    ;

finallyBlock
    : 'finally' NL* block
    ;

loopStatement
    : forStatement
    | whileStatement
    | doWhileStatement
    ;

forStatement
    : 'for' NL* '(' annotation* (variableDeclaration | multiVariableDeclaration) 'in' expression ')' NL* controlStructureBody?
    ;

whileStatement
    : 'while' NL* '(' expression ')' NL* controlStructureBody
    | 'while' NL* '(' expression ')' NL* ';'
    ;

doWhileStatement
    : 'do' NL* controlStructureBody? NL* 'while' NL* '(' expression ')'
    ;

jumpExpression
    : 'throw' NL* expression
    | ('return' | RETURN_AT) expression?
    | 'continue'
    | CONTINUE_AT
    | 'break'
    | BREAK_AT
    ;

callableReference // ?:: here is not an actual operator, it's just a lexer hack to avoid (?: + :) vs (? + ::) ambiguity
    : (receiverType? NL* '::' NL* (simpleIdentifier | 'class'))
    ;

assignmentAndOperator
    : '+='
    | '-='
    | '*='
    | '/='
    | '%='
    ;

equalityOperator
    : '!='
    | '!=='
    | '=='
    | '==='
    ;

comparisonOperator
    : '<'
    | '>'
    | '<='
    | '>='
    ;

inOperator
    : 'in'
    | NOT_IN
    ;

isOperator
    : 'is'
    | NOT_IS
    ;

additiveOperator
    : '+'
    | '-'
    ;

multiplicativeOperator
    : '*'
    | '/'
    | '%'
    ;

asOperator
    : 'as'
    | 'as?'
    ;

prefixUnaryOperator
    : '++'
    | '--'
    | '-'
    | '+'
    | excl
    ;

postfixUnaryOperator
    : '++'
    | '--'
    | EXCL_NO_WS excl
    ;

memberAccessOperator
    : '.'
    | safeNav
    | '::'
    ;

modifiers
    : (annotation | modifier | contextParameters NL*)+
    ;

modifier
    : (
        classModifier
        | memberModifier
        | visibilityModifier
        | functionModifier
        | propertyModifier
        | inheritanceModifier
        | parameterModifier
        | platformModifier
    ) NL*
    ;

classModifier
    : 'enum'
    | 'sealed'
    | 'annotation'
    | 'data'
    | 'inner'
    | 'value'
    ;

memberModifier
    : 'override'
    | 'lateinit'
    | 'companion'
    ;

visibilityModifier
    : 'public'
    | 'private'
    | 'internal'
    | 'protected'
    ;

varianceModifier
    : 'in'
    | 'out'
    ;

functionModifier
    : 'tailrec'
    | 'operator'
    | 'infix'
    | 'inline'
    | 'external'
    | 'suspend'
    ;

propertyModifier
    : 'const'
    ;

inheritanceModifier
    : 'abstract'
    | 'final'
    | 'open'
    ;

parameterModifier
    : 'vararg'
    | 'noinline'
    | 'crossinline'
    ;

reificationModifier
    : 'reified'
    ;

platformModifier
    : 'expect'
    | 'actual'
    ;

contextParameters
    : 'context' NL* '(' NL* (contextParameter (NL* ',' NL* contextParameter)* NL* ','?)? NL* ')'
    ;

contextParameter
    : (simpleIdentifier NL* ':' NL*)? type_
    ;

label
    : IdentifierAt NL*
    ;

annotation
    : (singleAnnotation | multiAnnotation) NL*
    ;

singleAnnotation
    : annotationUseSiteTarget NL* ':' NL* unescapedAnnotation
    | '@' unescapedAnnotation
    ;

multiAnnotation
    : annotationUseSiteTarget NL* ':' NL* '[' unescapedAnnotation+ ']'
    | '@' '[' unescapedAnnotation+ ']'
    ;

annotationUseSiteTarget
    : '@field'
    | '@property'
    | '@get'
    | '@set'
    | '@receiver'
    | '@param'
    | '@setparam'
    | '@delegate'
    | '@all'
    ;

unescapedAnnotation
    : constructorInvocation
    | userType
    ;

simpleIdentifier
    : Identifier //soft keywords:
    | 'abstract'
    | 'annotation'
    | 'by'
    | 'catch'
    | 'companion'
    | 'constructor'
    | 'crossinline'
    | 'data'
    | 'dynamic'
    | 'enum'
    | 'external'
    | 'final'
    | 'finally'
    | 'get'
    | 'import'
    | 'infix'
    | 'init'
    | 'inline'
    | 'inner'
    | 'internal'
    | 'lateinit'
    | 'noinline'
    | 'open'
    | 'operator'
    | 'out'
    | 'override'
    | 'private'
    | 'protected'
    | 'public'
    | 'reified'
    | 'sealed'
    | 'tailrec'
    | 'set'
    | 'vararg'
    | 'where'
    | 'expect'
    | 'actual'
    | 'value'
    | 'context'
    | 'field'
    | 'const'
    | 'suspend'
    ;

identifier
    : simpleIdentifier (NL* '.' simpleIdentifier)*
    ;

shebangLine
    : ShebangLine NL+
    ;

quest
    : QUEST_NO_WS
    | QUEST_WS
    ;

elvis
    : QUEST_NO_WS ':'
    ;

safeNav
    : QUEST_NO_WS '.'
    ;

excl
    : EXCL_NO_WS
    | EXCL_WS
    ;

semi
    : (';' | NL)+
    ;

semis
    : (';' | NL)+
    ;
