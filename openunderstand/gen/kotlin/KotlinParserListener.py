# Generated from KotlinParser.g4 by ANTLR 4.13.2
from antlr4 import *
if "." in __name__:
    from .KotlinParser import KotlinParser
else:
    from KotlinParser import KotlinParser

# This class defines a complete listener for a parse tree produced by KotlinParser.
class KotlinParserListener(ParseTreeListener):

    # Enter a parse tree produced by KotlinParser#kotlinFile.
    def enterKotlinFile(self, ctx:KotlinParser.KotlinFileContext):
        pass

    # Exit a parse tree produced by KotlinParser#kotlinFile.
    def exitKotlinFile(self, ctx:KotlinParser.KotlinFileContext):
        pass


    # Enter a parse tree produced by KotlinParser#script.
    def enterScript(self, ctx:KotlinParser.ScriptContext):
        pass

    # Exit a parse tree produced by KotlinParser#script.
    def exitScript(self, ctx:KotlinParser.ScriptContext):
        pass


    # Enter a parse tree produced by KotlinParser#fileAnnotation.
    def enterFileAnnotation(self, ctx:KotlinParser.FileAnnotationContext):
        pass

    # Exit a parse tree produced by KotlinParser#fileAnnotation.
    def exitFileAnnotation(self, ctx:KotlinParser.FileAnnotationContext):
        pass


    # Enter a parse tree produced by KotlinParser#packageHeader.
    def enterPackageHeader(self, ctx:KotlinParser.PackageHeaderContext):
        pass

    # Exit a parse tree produced by KotlinParser#packageHeader.
    def exitPackageHeader(self, ctx:KotlinParser.PackageHeaderContext):
        pass


    # Enter a parse tree produced by KotlinParser#importList.
    def enterImportList(self, ctx:KotlinParser.ImportListContext):
        pass

    # Exit a parse tree produced by KotlinParser#importList.
    def exitImportList(self, ctx:KotlinParser.ImportListContext):
        pass


    # Enter a parse tree produced by KotlinParser#importHeader.
    def enterImportHeader(self, ctx:KotlinParser.ImportHeaderContext):
        pass

    # Exit a parse tree produced by KotlinParser#importHeader.
    def exitImportHeader(self, ctx:KotlinParser.ImportHeaderContext):
        pass


    # Enter a parse tree produced by KotlinParser#importAlias.
    def enterImportAlias(self, ctx:KotlinParser.ImportAliasContext):
        pass

    # Exit a parse tree produced by KotlinParser#importAlias.
    def exitImportAlias(self, ctx:KotlinParser.ImportAliasContext):
        pass


    # Enter a parse tree produced by KotlinParser#topLevelObject.
    def enterTopLevelObject(self, ctx:KotlinParser.TopLevelObjectContext):
        pass

    # Exit a parse tree produced by KotlinParser#topLevelObject.
    def exitTopLevelObject(self, ctx:KotlinParser.TopLevelObjectContext):
        pass


    # Enter a parse tree produced by KotlinParser#classDeclaration.
    def enterClassDeclaration(self, ctx:KotlinParser.ClassDeclarationContext):
        pass

    # Exit a parse tree produced by KotlinParser#classDeclaration.
    def exitClassDeclaration(self, ctx:KotlinParser.ClassDeclarationContext):
        pass


    # Enter a parse tree produced by KotlinParser#primaryConstructor.
    def enterPrimaryConstructor(self, ctx:KotlinParser.PrimaryConstructorContext):
        pass

    # Exit a parse tree produced by KotlinParser#primaryConstructor.
    def exitPrimaryConstructor(self, ctx:KotlinParser.PrimaryConstructorContext):
        pass


    # Enter a parse tree produced by KotlinParser#classParameters.
    def enterClassParameters(self, ctx:KotlinParser.ClassParametersContext):
        pass

    # Exit a parse tree produced by KotlinParser#classParameters.
    def exitClassParameters(self, ctx:KotlinParser.ClassParametersContext):
        pass


    # Enter a parse tree produced by KotlinParser#classParameter.
    def enterClassParameter(self, ctx:KotlinParser.ClassParameterContext):
        pass

    # Exit a parse tree produced by KotlinParser#classParameter.
    def exitClassParameter(self, ctx:KotlinParser.ClassParameterContext):
        pass


    # Enter a parse tree produced by KotlinParser#delegationSpecifiers.
    def enterDelegationSpecifiers(self, ctx:KotlinParser.DelegationSpecifiersContext):
        pass

    # Exit a parse tree produced by KotlinParser#delegationSpecifiers.
    def exitDelegationSpecifiers(self, ctx:KotlinParser.DelegationSpecifiersContext):
        pass


    # Enter a parse tree produced by KotlinParser#annotatedDelegationSpecifier.
    def enterAnnotatedDelegationSpecifier(self, ctx:KotlinParser.AnnotatedDelegationSpecifierContext):
        pass

    # Exit a parse tree produced by KotlinParser#annotatedDelegationSpecifier.
    def exitAnnotatedDelegationSpecifier(self, ctx:KotlinParser.AnnotatedDelegationSpecifierContext):
        pass


    # Enter a parse tree produced by KotlinParser#delegationSpecifier.
    def enterDelegationSpecifier(self, ctx:KotlinParser.DelegationSpecifierContext):
        pass

    # Exit a parse tree produced by KotlinParser#delegationSpecifier.
    def exitDelegationSpecifier(self, ctx:KotlinParser.DelegationSpecifierContext):
        pass


    # Enter a parse tree produced by KotlinParser#constructorInvocation.
    def enterConstructorInvocation(self, ctx:KotlinParser.ConstructorInvocationContext):
        pass

    # Exit a parse tree produced by KotlinParser#constructorInvocation.
    def exitConstructorInvocation(self, ctx:KotlinParser.ConstructorInvocationContext):
        pass


    # Enter a parse tree produced by KotlinParser#explicitDelegation.
    def enterExplicitDelegation(self, ctx:KotlinParser.ExplicitDelegationContext):
        pass

    # Exit a parse tree produced by KotlinParser#explicitDelegation.
    def exitExplicitDelegation(self, ctx:KotlinParser.ExplicitDelegationContext):
        pass


    # Enter a parse tree produced by KotlinParser#delegateExpression.
    def enterDelegateExpression(self, ctx:KotlinParser.DelegateExpressionContext):
        pass

    # Exit a parse tree produced by KotlinParser#delegateExpression.
    def exitDelegateExpression(self, ctx:KotlinParser.DelegateExpressionContext):
        pass


    # Enter a parse tree produced by KotlinParser#delegateSuffix.
    def enterDelegateSuffix(self, ctx:KotlinParser.DelegateSuffixContext):
        pass

    # Exit a parse tree produced by KotlinParser#delegateSuffix.
    def exitDelegateSuffix(self, ctx:KotlinParser.DelegateSuffixContext):
        pass


    # Enter a parse tree produced by KotlinParser#classBody.
    def enterClassBody(self, ctx:KotlinParser.ClassBodyContext):
        pass

    # Exit a parse tree produced by KotlinParser#classBody.
    def exitClassBody(self, ctx:KotlinParser.ClassBodyContext):
        pass


    # Enter a parse tree produced by KotlinParser#classMemberDeclarations.
    def enterClassMemberDeclarations(self, ctx:KotlinParser.ClassMemberDeclarationsContext):
        pass

    # Exit a parse tree produced by KotlinParser#classMemberDeclarations.
    def exitClassMemberDeclarations(self, ctx:KotlinParser.ClassMemberDeclarationsContext):
        pass


    # Enter a parse tree produced by KotlinParser#classMemberDeclaration.
    def enterClassMemberDeclaration(self, ctx:KotlinParser.ClassMemberDeclarationContext):
        pass

    # Exit a parse tree produced by KotlinParser#classMemberDeclaration.
    def exitClassMemberDeclaration(self, ctx:KotlinParser.ClassMemberDeclarationContext):
        pass


    # Enter a parse tree produced by KotlinParser#anonymousInitializer.
    def enterAnonymousInitializer(self, ctx:KotlinParser.AnonymousInitializerContext):
        pass

    # Exit a parse tree produced by KotlinParser#anonymousInitializer.
    def exitAnonymousInitializer(self, ctx:KotlinParser.AnonymousInitializerContext):
        pass


    # Enter a parse tree produced by KotlinParser#secondaryConstructor.
    def enterSecondaryConstructor(self, ctx:KotlinParser.SecondaryConstructorContext):
        pass

    # Exit a parse tree produced by KotlinParser#secondaryConstructor.
    def exitSecondaryConstructor(self, ctx:KotlinParser.SecondaryConstructorContext):
        pass


    # Enter a parse tree produced by KotlinParser#constructorDelegationCall.
    def enterConstructorDelegationCall(self, ctx:KotlinParser.ConstructorDelegationCallContext):
        pass

    # Exit a parse tree produced by KotlinParser#constructorDelegationCall.
    def exitConstructorDelegationCall(self, ctx:KotlinParser.ConstructorDelegationCallContext):
        pass


    # Enter a parse tree produced by KotlinParser#enumClassBody.
    def enterEnumClassBody(self, ctx:KotlinParser.EnumClassBodyContext):
        pass

    # Exit a parse tree produced by KotlinParser#enumClassBody.
    def exitEnumClassBody(self, ctx:KotlinParser.EnumClassBodyContext):
        pass


    # Enter a parse tree produced by KotlinParser#enumEntries.
    def enterEnumEntries(self, ctx:KotlinParser.EnumEntriesContext):
        pass

    # Exit a parse tree produced by KotlinParser#enumEntries.
    def exitEnumEntries(self, ctx:KotlinParser.EnumEntriesContext):
        pass


    # Enter a parse tree produced by KotlinParser#enumEntry.
    def enterEnumEntry(self, ctx:KotlinParser.EnumEntryContext):
        pass

    # Exit a parse tree produced by KotlinParser#enumEntry.
    def exitEnumEntry(self, ctx:KotlinParser.EnumEntryContext):
        pass


    # Enter a parse tree produced by KotlinParser#functionDeclaration.
    def enterFunctionDeclaration(self, ctx:KotlinParser.FunctionDeclarationContext):
        pass

    # Exit a parse tree produced by KotlinParser#functionDeclaration.
    def exitFunctionDeclaration(self, ctx:KotlinParser.FunctionDeclarationContext):
        pass


    # Enter a parse tree produced by KotlinParser#contractSpec.
    def enterContractSpec(self, ctx:KotlinParser.ContractSpecContext):
        pass

    # Exit a parse tree produced by KotlinParser#contractSpec.
    def exitContractSpec(self, ctx:KotlinParser.ContractSpecContext):
        pass


    # Enter a parse tree produced by KotlinParser#functionValueParameters.
    def enterFunctionValueParameters(self, ctx:KotlinParser.FunctionValueParametersContext):
        pass

    # Exit a parse tree produced by KotlinParser#functionValueParameters.
    def exitFunctionValueParameters(self, ctx:KotlinParser.FunctionValueParametersContext):
        pass


    # Enter a parse tree produced by KotlinParser#functionValueParameter.
    def enterFunctionValueParameter(self, ctx:KotlinParser.FunctionValueParameterContext):
        pass

    # Exit a parse tree produced by KotlinParser#functionValueParameter.
    def exitFunctionValueParameter(self, ctx:KotlinParser.FunctionValueParameterContext):
        pass


    # Enter a parse tree produced by KotlinParser#parameter.
    def enterParameter(self, ctx:KotlinParser.ParameterContext):
        pass

    # Exit a parse tree produced by KotlinParser#parameter.
    def exitParameter(self, ctx:KotlinParser.ParameterContext):
        pass


    # Enter a parse tree produced by KotlinParser#setterParameter.
    def enterSetterParameter(self, ctx:KotlinParser.SetterParameterContext):
        pass

    # Exit a parse tree produced by KotlinParser#setterParameter.
    def exitSetterParameter(self, ctx:KotlinParser.SetterParameterContext):
        pass


    # Enter a parse tree produced by KotlinParser#functionBody.
    def enterFunctionBody(self, ctx:KotlinParser.FunctionBodyContext):
        pass

    # Exit a parse tree produced by KotlinParser#functionBody.
    def exitFunctionBody(self, ctx:KotlinParser.FunctionBodyContext):
        pass


    # Enter a parse tree produced by KotlinParser#objectDeclaration.
    def enterObjectDeclaration(self, ctx:KotlinParser.ObjectDeclarationContext):
        pass

    # Exit a parse tree produced by KotlinParser#objectDeclaration.
    def exitObjectDeclaration(self, ctx:KotlinParser.ObjectDeclarationContext):
        pass


    # Enter a parse tree produced by KotlinParser#companionBlock.
    def enterCompanionBlock(self, ctx:KotlinParser.CompanionBlockContext):
        pass

    # Exit a parse tree produced by KotlinParser#companionBlock.
    def exitCompanionBlock(self, ctx:KotlinParser.CompanionBlockContext):
        pass


    # Enter a parse tree produced by KotlinParser#companionObject.
    def enterCompanionObject(self, ctx:KotlinParser.CompanionObjectContext):
        pass

    # Exit a parse tree produced by KotlinParser#companionObject.
    def exitCompanionObject(self, ctx:KotlinParser.CompanionObjectContext):
        pass


    # Enter a parse tree produced by KotlinParser#memberPropertyDeclaration.
    def enterMemberPropertyDeclaration(self, ctx:KotlinParser.MemberPropertyDeclarationContext):
        pass

    # Exit a parse tree produced by KotlinParser#memberPropertyDeclaration.
    def exitMemberPropertyDeclaration(self, ctx:KotlinParser.MemberPropertyDeclarationContext):
        pass


    # Enter a parse tree produced by KotlinParser#explicitBackingField.
    def enterExplicitBackingField(self, ctx:KotlinParser.ExplicitBackingFieldContext):
        pass

    # Exit a parse tree produced by KotlinParser#explicitBackingField.
    def exitExplicitBackingField(self, ctx:KotlinParser.ExplicitBackingFieldContext):
        pass


    # Enter a parse tree produced by KotlinParser#propertyDeclaration.
    def enterPropertyDeclaration(self, ctx:KotlinParser.PropertyDeclarationContext):
        pass

    # Exit a parse tree produced by KotlinParser#propertyDeclaration.
    def exitPropertyDeclaration(self, ctx:KotlinParser.PropertyDeclarationContext):
        pass


    # Enter a parse tree produced by KotlinParser#propertyDeclarationHead.
    def enterPropertyDeclarationHead(self, ctx:KotlinParser.PropertyDeclarationHeadContext):
        pass

    # Exit a parse tree produced by KotlinParser#propertyDeclarationHead.
    def exitPropertyDeclarationHead(self, ctx:KotlinParser.PropertyDeclarationHeadContext):
        pass


    # Enter a parse tree produced by KotlinParser#propertyAccessors.
    def enterPropertyAccessors(self, ctx:KotlinParser.PropertyAccessorsContext):
        pass

    # Exit a parse tree produced by KotlinParser#propertyAccessors.
    def exitPropertyAccessors(self, ctx:KotlinParser.PropertyAccessorsContext):
        pass


    # Enter a parse tree produced by KotlinParser#multiVariableDeclaration.
    def enterMultiVariableDeclaration(self, ctx:KotlinParser.MultiVariableDeclarationContext):
        pass

    # Exit a parse tree produced by KotlinParser#multiVariableDeclaration.
    def exitMultiVariableDeclaration(self, ctx:KotlinParser.MultiVariableDeclarationContext):
        pass


    # Enter a parse tree produced by KotlinParser#destructuringEntry.
    def enterDestructuringEntry(self, ctx:KotlinParser.DestructuringEntryContext):
        pass

    # Exit a parse tree produced by KotlinParser#destructuringEntry.
    def exitDestructuringEntry(self, ctx:KotlinParser.DestructuringEntryContext):
        pass


    # Enter a parse tree produced by KotlinParser#variableDeclaration.
    def enterVariableDeclaration(self, ctx:KotlinParser.VariableDeclarationContext):
        pass

    # Exit a parse tree produced by KotlinParser#variableDeclaration.
    def exitVariableDeclaration(self, ctx:KotlinParser.VariableDeclarationContext):
        pass


    # Enter a parse tree produced by KotlinParser#propertyDelegate.
    def enterPropertyDelegate(self, ctx:KotlinParser.PropertyDelegateContext):
        pass

    # Exit a parse tree produced by KotlinParser#propertyDelegate.
    def exitPropertyDelegate(self, ctx:KotlinParser.PropertyDelegateContext):
        pass


    # Enter a parse tree produced by KotlinParser#getter.
    def enterGetter(self, ctx:KotlinParser.GetterContext):
        pass

    # Exit a parse tree produced by KotlinParser#getter.
    def exitGetter(self, ctx:KotlinParser.GetterContext):
        pass


    # Enter a parse tree produced by KotlinParser#setter.
    def enterSetter(self, ctx:KotlinParser.SetterContext):
        pass

    # Exit a parse tree produced by KotlinParser#setter.
    def exitSetter(self, ctx:KotlinParser.SetterContext):
        pass


    # Enter a parse tree produced by KotlinParser#typeAlias.
    def enterTypeAlias(self, ctx:KotlinParser.TypeAliasContext):
        pass

    # Exit a parse tree produced by KotlinParser#typeAlias.
    def exitTypeAlias(self, ctx:KotlinParser.TypeAliasContext):
        pass


    # Enter a parse tree produced by KotlinParser#typeParameters.
    def enterTypeParameters(self, ctx:KotlinParser.TypeParametersContext):
        pass

    # Exit a parse tree produced by KotlinParser#typeParameters.
    def exitTypeParameters(self, ctx:KotlinParser.TypeParametersContext):
        pass


    # Enter a parse tree produced by KotlinParser#typeParameter.
    def enterTypeParameter(self, ctx:KotlinParser.TypeParameterContext):
        pass

    # Exit a parse tree produced by KotlinParser#typeParameter.
    def exitTypeParameter(self, ctx:KotlinParser.TypeParameterContext):
        pass


    # Enter a parse tree produced by KotlinParser#typeParameterModifiers.
    def enterTypeParameterModifiers(self, ctx:KotlinParser.TypeParameterModifiersContext):
        pass

    # Exit a parse tree produced by KotlinParser#typeParameterModifiers.
    def exitTypeParameterModifiers(self, ctx:KotlinParser.TypeParameterModifiersContext):
        pass


    # Enter a parse tree produced by KotlinParser#typeParameterModifier.
    def enterTypeParameterModifier(self, ctx:KotlinParser.TypeParameterModifierContext):
        pass

    # Exit a parse tree produced by KotlinParser#typeParameterModifier.
    def exitTypeParameterModifier(self, ctx:KotlinParser.TypeParameterModifierContext):
        pass


    # Enter a parse tree produced by KotlinParser#type_.
    def enterType_(self, ctx:KotlinParser.Type_Context):
        pass

    # Exit a parse tree produced by KotlinParser#type_.
    def exitType_(self, ctx:KotlinParser.Type_Context):
        pass


    # Enter a parse tree produced by KotlinParser#typeModifiers.
    def enterTypeModifiers(self, ctx:KotlinParser.TypeModifiersContext):
        pass

    # Exit a parse tree produced by KotlinParser#typeModifiers.
    def exitTypeModifiers(self, ctx:KotlinParser.TypeModifiersContext):
        pass


    # Enter a parse tree produced by KotlinParser#typeModifier.
    def enterTypeModifier(self, ctx:KotlinParser.TypeModifierContext):
        pass

    # Exit a parse tree produced by KotlinParser#typeModifier.
    def exitTypeModifier(self, ctx:KotlinParser.TypeModifierContext):
        pass


    # Enter a parse tree produced by KotlinParser#parenthesizedType.
    def enterParenthesizedType(self, ctx:KotlinParser.ParenthesizedTypeContext):
        pass

    # Exit a parse tree produced by KotlinParser#parenthesizedType.
    def exitParenthesizedType(self, ctx:KotlinParser.ParenthesizedTypeContext):
        pass


    # Enter a parse tree produced by KotlinParser#nullableType.
    def enterNullableType(self, ctx:KotlinParser.NullableTypeContext):
        pass

    # Exit a parse tree produced by KotlinParser#nullableType.
    def exitNullableType(self, ctx:KotlinParser.NullableTypeContext):
        pass


    # Enter a parse tree produced by KotlinParser#typeReference.
    def enterTypeReference(self, ctx:KotlinParser.TypeReferenceContext):
        pass

    # Exit a parse tree produced by KotlinParser#typeReference.
    def exitTypeReference(self, ctx:KotlinParser.TypeReferenceContext):
        pass


    # Enter a parse tree produced by KotlinParser#functionType.
    def enterFunctionType(self, ctx:KotlinParser.FunctionTypeContext):
        pass

    # Exit a parse tree produced by KotlinParser#functionType.
    def exitFunctionType(self, ctx:KotlinParser.FunctionTypeContext):
        pass


    # Enter a parse tree produced by KotlinParser#receiverType.
    def enterReceiverType(self, ctx:KotlinParser.ReceiverTypeContext):
        pass

    # Exit a parse tree produced by KotlinParser#receiverType.
    def exitReceiverType(self, ctx:KotlinParser.ReceiverTypeContext):
        pass


    # Enter a parse tree produced by KotlinParser#userType.
    def enterUserType(self, ctx:KotlinParser.UserTypeContext):
        pass

    # Exit a parse tree produced by KotlinParser#userType.
    def exitUserType(self, ctx:KotlinParser.UserTypeContext):
        pass


    # Enter a parse tree produced by KotlinParser#parenthesizedUserType.
    def enterParenthesizedUserType(self, ctx:KotlinParser.ParenthesizedUserTypeContext):
        pass

    # Exit a parse tree produced by KotlinParser#parenthesizedUserType.
    def exitParenthesizedUserType(self, ctx:KotlinParser.ParenthesizedUserTypeContext):
        pass


    # Enter a parse tree produced by KotlinParser#simpleUserType.
    def enterSimpleUserType(self, ctx:KotlinParser.SimpleUserTypeContext):
        pass

    # Exit a parse tree produced by KotlinParser#simpleUserType.
    def exitSimpleUserType(self, ctx:KotlinParser.SimpleUserTypeContext):
        pass


    # Enter a parse tree produced by KotlinParser#functionTypeParameters.
    def enterFunctionTypeParameters(self, ctx:KotlinParser.FunctionTypeParametersContext):
        pass

    # Exit a parse tree produced by KotlinParser#functionTypeParameters.
    def exitFunctionTypeParameters(self, ctx:KotlinParser.FunctionTypeParametersContext):
        pass


    # Enter a parse tree produced by KotlinParser#typeConstraints.
    def enterTypeConstraints(self, ctx:KotlinParser.TypeConstraintsContext):
        pass

    # Exit a parse tree produced by KotlinParser#typeConstraints.
    def exitTypeConstraints(self, ctx:KotlinParser.TypeConstraintsContext):
        pass


    # Enter a parse tree produced by KotlinParser#typeConstraint.
    def enterTypeConstraint(self, ctx:KotlinParser.TypeConstraintContext):
        pass

    # Exit a parse tree produced by KotlinParser#typeConstraint.
    def exitTypeConstraint(self, ctx:KotlinParser.TypeConstraintContext):
        pass


    # Enter a parse tree produced by KotlinParser#block.
    def enterBlock(self, ctx:KotlinParser.BlockContext):
        pass

    # Exit a parse tree produced by KotlinParser#block.
    def exitBlock(self, ctx:KotlinParser.BlockContext):
        pass


    # Enter a parse tree produced by KotlinParser#statements.
    def enterStatements(self, ctx:KotlinParser.StatementsContext):
        pass

    # Exit a parse tree produced by KotlinParser#statements.
    def exitStatements(self, ctx:KotlinParser.StatementsContext):
        pass


    # Enter a parse tree produced by KotlinParser#statement.
    def enterStatement(self, ctx:KotlinParser.StatementContext):
        pass

    # Exit a parse tree produced by KotlinParser#statement.
    def exitStatement(self, ctx:KotlinParser.StatementContext):
        pass


    # Enter a parse tree produced by KotlinParser#declaration.
    def enterDeclaration(self, ctx:KotlinParser.DeclarationContext):
        pass

    # Exit a parse tree produced by KotlinParser#declaration.
    def exitDeclaration(self, ctx:KotlinParser.DeclarationContext):
        pass


    # Enter a parse tree produced by KotlinParser#destructuringAssignment.
    def enterDestructuringAssignment(self, ctx:KotlinParser.DestructuringAssignmentContext):
        pass

    # Exit a parse tree produced by KotlinParser#destructuringAssignment.
    def exitDestructuringAssignment(self, ctx:KotlinParser.DestructuringAssignmentContext):
        pass


    # Enter a parse tree produced by KotlinParser#expressionStatement.
    def enterExpressionStatement(self, ctx:KotlinParser.ExpressionStatementContext):
        pass

    # Exit a parse tree produced by KotlinParser#expressionStatement.
    def exitExpressionStatement(self, ctx:KotlinParser.ExpressionStatementContext):
        pass


    # Enter a parse tree produced by KotlinParser#expression.
    def enterExpression(self, ctx:KotlinParser.ExpressionContext):
        pass

    # Exit a parse tree produced by KotlinParser#expression.
    def exitExpression(self, ctx:KotlinParser.ExpressionContext):
        pass


    # Enter a parse tree produced by KotlinParser#disjunction.
    def enterDisjunction(self, ctx:KotlinParser.DisjunctionContext):
        pass

    # Exit a parse tree produced by KotlinParser#disjunction.
    def exitDisjunction(self, ctx:KotlinParser.DisjunctionContext):
        pass


    # Enter a parse tree produced by KotlinParser#conjunction.
    def enterConjunction(self, ctx:KotlinParser.ConjunctionContext):
        pass

    # Exit a parse tree produced by KotlinParser#conjunction.
    def exitConjunction(self, ctx:KotlinParser.ConjunctionContext):
        pass


    # Enter a parse tree produced by KotlinParser#equality.
    def enterEquality(self, ctx:KotlinParser.EqualityContext):
        pass

    # Exit a parse tree produced by KotlinParser#equality.
    def exitEquality(self, ctx:KotlinParser.EqualityContext):
        pass


    # Enter a parse tree produced by KotlinParser#comparison.
    def enterComparison(self, ctx:KotlinParser.ComparisonContext):
        pass

    # Exit a parse tree produced by KotlinParser#comparison.
    def exitComparison(self, ctx:KotlinParser.ComparisonContext):
        pass


    # Enter a parse tree produced by KotlinParser#infixOperation.
    def enterInfixOperation(self, ctx:KotlinParser.InfixOperationContext):
        pass

    # Exit a parse tree produced by KotlinParser#infixOperation.
    def exitInfixOperation(self, ctx:KotlinParser.InfixOperationContext):
        pass


    # Enter a parse tree produced by KotlinParser#elvisExpression.
    def enterElvisExpression(self, ctx:KotlinParser.ElvisExpressionContext):
        pass

    # Exit a parse tree produced by KotlinParser#elvisExpression.
    def exitElvisExpression(self, ctx:KotlinParser.ElvisExpressionContext):
        pass


    # Enter a parse tree produced by KotlinParser#infixFunctionCall.
    def enterInfixFunctionCall(self, ctx:KotlinParser.InfixFunctionCallContext):
        pass

    # Exit a parse tree produced by KotlinParser#infixFunctionCall.
    def exitInfixFunctionCall(self, ctx:KotlinParser.InfixFunctionCallContext):
        pass


    # Enter a parse tree produced by KotlinParser#rangeExpression.
    def enterRangeExpression(self, ctx:KotlinParser.RangeExpressionContext):
        pass

    # Exit a parse tree produced by KotlinParser#rangeExpression.
    def exitRangeExpression(self, ctx:KotlinParser.RangeExpressionContext):
        pass


    # Enter a parse tree produced by KotlinParser#additiveExpression.
    def enterAdditiveExpression(self, ctx:KotlinParser.AdditiveExpressionContext):
        pass

    # Exit a parse tree produced by KotlinParser#additiveExpression.
    def exitAdditiveExpression(self, ctx:KotlinParser.AdditiveExpressionContext):
        pass


    # Enter a parse tree produced by KotlinParser#multiplicativeExpression.
    def enterMultiplicativeExpression(self, ctx:KotlinParser.MultiplicativeExpressionContext):
        pass

    # Exit a parse tree produced by KotlinParser#multiplicativeExpression.
    def exitMultiplicativeExpression(self, ctx:KotlinParser.MultiplicativeExpressionContext):
        pass


    # Enter a parse tree produced by KotlinParser#asExpression.
    def enterAsExpression(self, ctx:KotlinParser.AsExpressionContext):
        pass

    # Exit a parse tree produced by KotlinParser#asExpression.
    def exitAsExpression(self, ctx:KotlinParser.AsExpressionContext):
        pass


    # Enter a parse tree produced by KotlinParser#prefixUnaryExpression.
    def enterPrefixUnaryExpression(self, ctx:KotlinParser.PrefixUnaryExpressionContext):
        pass

    # Exit a parse tree produced by KotlinParser#prefixUnaryExpression.
    def exitPrefixUnaryExpression(self, ctx:KotlinParser.PrefixUnaryExpressionContext):
        pass


    # Enter a parse tree produced by KotlinParser#unaryPrefix.
    def enterUnaryPrefix(self, ctx:KotlinParser.UnaryPrefixContext):
        pass

    # Exit a parse tree produced by KotlinParser#unaryPrefix.
    def exitUnaryPrefix(self, ctx:KotlinParser.UnaryPrefixContext):
        pass


    # Enter a parse tree produced by KotlinParser#postfixUnaryExpression.
    def enterPostfixUnaryExpression(self, ctx:KotlinParser.PostfixUnaryExpressionContext):
        pass

    # Exit a parse tree produced by KotlinParser#postfixUnaryExpression.
    def exitPostfixUnaryExpression(self, ctx:KotlinParser.PostfixUnaryExpressionContext):
        pass


    # Enter a parse tree produced by KotlinParser#postfixUnarySuffix.
    def enterPostfixUnarySuffix(self, ctx:KotlinParser.PostfixUnarySuffixContext):
        pass

    # Exit a parse tree produced by KotlinParser#postfixUnarySuffix.
    def exitPostfixUnarySuffix(self, ctx:KotlinParser.PostfixUnarySuffixContext):
        pass


    # Enter a parse tree produced by KotlinParser#indexingSuffix.
    def enterIndexingSuffix(self, ctx:KotlinParser.IndexingSuffixContext):
        pass

    # Exit a parse tree produced by KotlinParser#indexingSuffix.
    def exitIndexingSuffix(self, ctx:KotlinParser.IndexingSuffixContext):
        pass


    # Enter a parse tree produced by KotlinParser#navigationSuffix.
    def enterNavigationSuffix(self, ctx:KotlinParser.NavigationSuffixContext):
        pass

    # Exit a parse tree produced by KotlinParser#navigationSuffix.
    def exitNavigationSuffix(self, ctx:KotlinParser.NavigationSuffixContext):
        pass


    # Enter a parse tree produced by KotlinParser#callSuffix.
    def enterCallSuffix(self, ctx:KotlinParser.CallSuffixContext):
        pass

    # Exit a parse tree produced by KotlinParser#callSuffix.
    def exitCallSuffix(self, ctx:KotlinParser.CallSuffixContext):
        pass


    # Enter a parse tree produced by KotlinParser#labeledLambda.
    def enterLabeledLambda(self, ctx:KotlinParser.LabeledLambdaContext):
        pass

    # Exit a parse tree produced by KotlinParser#labeledLambda.
    def exitLabeledLambda(self, ctx:KotlinParser.LabeledLambdaContext):
        pass


    # Enter a parse tree produced by KotlinParser#annotatedLambda.
    def enterAnnotatedLambda(self, ctx:KotlinParser.AnnotatedLambdaContext):
        pass

    # Exit a parse tree produced by KotlinParser#annotatedLambda.
    def exitAnnotatedLambda(self, ctx:KotlinParser.AnnotatedLambdaContext):
        pass


    # Enter a parse tree produced by KotlinParser#valueArguments.
    def enterValueArguments(self, ctx:KotlinParser.ValueArgumentsContext):
        pass

    # Exit a parse tree produced by KotlinParser#valueArguments.
    def exitValueArguments(self, ctx:KotlinParser.ValueArgumentsContext):
        pass


    # Enter a parse tree produced by KotlinParser#typeArguments.
    def enterTypeArguments(self, ctx:KotlinParser.TypeArgumentsContext):
        pass

    # Exit a parse tree produced by KotlinParser#typeArguments.
    def exitTypeArguments(self, ctx:KotlinParser.TypeArgumentsContext):
        pass


    # Enter a parse tree produced by KotlinParser#typeProjection.
    def enterTypeProjection(self, ctx:KotlinParser.TypeProjectionContext):
        pass

    # Exit a parse tree produced by KotlinParser#typeProjection.
    def exitTypeProjection(self, ctx:KotlinParser.TypeProjectionContext):
        pass


    # Enter a parse tree produced by KotlinParser#typeProjectionModifiers.
    def enterTypeProjectionModifiers(self, ctx:KotlinParser.TypeProjectionModifiersContext):
        pass

    # Exit a parse tree produced by KotlinParser#typeProjectionModifiers.
    def exitTypeProjectionModifiers(self, ctx:KotlinParser.TypeProjectionModifiersContext):
        pass


    # Enter a parse tree produced by KotlinParser#typeProjectionModifier.
    def enterTypeProjectionModifier(self, ctx:KotlinParser.TypeProjectionModifierContext):
        pass

    # Exit a parse tree produced by KotlinParser#typeProjectionModifier.
    def exitTypeProjectionModifier(self, ctx:KotlinParser.TypeProjectionModifierContext):
        pass


    # Enter a parse tree produced by KotlinParser#valueArgument.
    def enterValueArgument(self, ctx:KotlinParser.ValueArgumentContext):
        pass

    # Exit a parse tree produced by KotlinParser#valueArgument.
    def exitValueArgument(self, ctx:KotlinParser.ValueArgumentContext):
        pass


    # Enter a parse tree produced by KotlinParser#primaryExpression.
    def enterPrimaryExpression(self, ctx:KotlinParser.PrimaryExpressionContext):
        pass

    # Exit a parse tree produced by KotlinParser#primaryExpression.
    def exitPrimaryExpression(self, ctx:KotlinParser.PrimaryExpressionContext):
        pass


    # Enter a parse tree produced by KotlinParser#parenthesizedExpression.
    def enterParenthesizedExpression(self, ctx:KotlinParser.ParenthesizedExpressionContext):
        pass

    # Exit a parse tree produced by KotlinParser#parenthesizedExpression.
    def exitParenthesizedExpression(self, ctx:KotlinParser.ParenthesizedExpressionContext):
        pass


    # Enter a parse tree produced by KotlinParser#collectionLiteral.
    def enterCollectionLiteral(self, ctx:KotlinParser.CollectionLiteralContext):
        pass

    # Exit a parse tree produced by KotlinParser#collectionLiteral.
    def exitCollectionLiteral(self, ctx:KotlinParser.CollectionLiteralContext):
        pass


    # Enter a parse tree produced by KotlinParser#literalConstant.
    def enterLiteralConstant(self, ctx:KotlinParser.LiteralConstantContext):
        pass

    # Exit a parse tree produced by KotlinParser#literalConstant.
    def exitLiteralConstant(self, ctx:KotlinParser.LiteralConstantContext):
        pass


    # Enter a parse tree produced by KotlinParser#stringLiteral.
    def enterStringLiteral(self, ctx:KotlinParser.StringLiteralContext):
        pass

    # Exit a parse tree produced by KotlinParser#stringLiteral.
    def exitStringLiteral(self, ctx:KotlinParser.StringLiteralContext):
        pass


    # Enter a parse tree produced by KotlinParser#lineStringLiteral.
    def enterLineStringLiteral(self, ctx:KotlinParser.LineStringLiteralContext):
        pass

    # Exit a parse tree produced by KotlinParser#lineStringLiteral.
    def exitLineStringLiteral(self, ctx:KotlinParser.LineStringLiteralContext):
        pass


    # Enter a parse tree produced by KotlinParser#multiLineStringLiteral.
    def enterMultiLineStringLiteral(self, ctx:KotlinParser.MultiLineStringLiteralContext):
        pass

    # Exit a parse tree produced by KotlinParser#multiLineStringLiteral.
    def exitMultiLineStringLiteral(self, ctx:KotlinParser.MultiLineStringLiteralContext):
        pass


    # Enter a parse tree produced by KotlinParser#lineStringContent.
    def enterLineStringContent(self, ctx:KotlinParser.LineStringContentContext):
        pass

    # Exit a parse tree produced by KotlinParser#lineStringContent.
    def exitLineStringContent(self, ctx:KotlinParser.LineStringContentContext):
        pass


    # Enter a parse tree produced by KotlinParser#lineStringExpression.
    def enterLineStringExpression(self, ctx:KotlinParser.LineStringExpressionContext):
        pass

    # Exit a parse tree produced by KotlinParser#lineStringExpression.
    def exitLineStringExpression(self, ctx:KotlinParser.LineStringExpressionContext):
        pass


    # Enter a parse tree produced by KotlinParser#multiLineStringContent.
    def enterMultiLineStringContent(self, ctx:KotlinParser.MultiLineStringContentContext):
        pass

    # Exit a parse tree produced by KotlinParser#multiLineStringContent.
    def exitMultiLineStringContent(self, ctx:KotlinParser.MultiLineStringContentContext):
        pass


    # Enter a parse tree produced by KotlinParser#multiLineStringExpression.
    def enterMultiLineStringExpression(self, ctx:KotlinParser.MultiLineStringExpressionContext):
        pass

    # Exit a parse tree produced by KotlinParser#multiLineStringExpression.
    def exitMultiLineStringExpression(self, ctx:KotlinParser.MultiLineStringExpressionContext):
        pass


    # Enter a parse tree produced by KotlinParser#lambdaLiteral.
    def enterLambdaLiteral(self, ctx:KotlinParser.LambdaLiteralContext):
        pass

    # Exit a parse tree produced by KotlinParser#lambdaLiteral.
    def exitLambdaLiteral(self, ctx:KotlinParser.LambdaLiteralContext):
        pass


    # Enter a parse tree produced by KotlinParser#lambdaParameters.
    def enterLambdaParameters(self, ctx:KotlinParser.LambdaParametersContext):
        pass

    # Exit a parse tree produced by KotlinParser#lambdaParameters.
    def exitLambdaParameters(self, ctx:KotlinParser.LambdaParametersContext):
        pass


    # Enter a parse tree produced by KotlinParser#lambdaParameter.
    def enterLambdaParameter(self, ctx:KotlinParser.LambdaParameterContext):
        pass

    # Exit a parse tree produced by KotlinParser#lambdaParameter.
    def exitLambdaParameter(self, ctx:KotlinParser.LambdaParameterContext):
        pass


    # Enter a parse tree produced by KotlinParser#anonymousFunction.
    def enterAnonymousFunction(self, ctx:KotlinParser.AnonymousFunctionContext):
        pass

    # Exit a parse tree produced by KotlinParser#anonymousFunction.
    def exitAnonymousFunction(self, ctx:KotlinParser.AnonymousFunctionContext):
        pass


    # Enter a parse tree produced by KotlinParser#anonymousFunctionParameters.
    def enterAnonymousFunctionParameters(self, ctx:KotlinParser.AnonymousFunctionParametersContext):
        pass

    # Exit a parse tree produced by KotlinParser#anonymousFunctionParameters.
    def exitAnonymousFunctionParameters(self, ctx:KotlinParser.AnonymousFunctionParametersContext):
        pass


    # Enter a parse tree produced by KotlinParser#anonymousFunctionParameter.
    def enterAnonymousFunctionParameter(self, ctx:KotlinParser.AnonymousFunctionParameterContext):
        pass

    # Exit a parse tree produced by KotlinParser#anonymousFunctionParameter.
    def exitAnonymousFunctionParameter(self, ctx:KotlinParser.AnonymousFunctionParameterContext):
        pass


    # Enter a parse tree produced by KotlinParser#functionLiteral.
    def enterFunctionLiteral(self, ctx:KotlinParser.FunctionLiteralContext):
        pass

    # Exit a parse tree produced by KotlinParser#functionLiteral.
    def exitFunctionLiteral(self, ctx:KotlinParser.FunctionLiteralContext):
        pass


    # Enter a parse tree produced by KotlinParser#objectLiteral.
    def enterObjectLiteral(self, ctx:KotlinParser.ObjectLiteralContext):
        pass

    # Exit a parse tree produced by KotlinParser#objectLiteral.
    def exitObjectLiteral(self, ctx:KotlinParser.ObjectLiteralContext):
        pass


    # Enter a parse tree produced by KotlinParser#thisExpression.
    def enterThisExpression(self, ctx:KotlinParser.ThisExpressionContext):
        pass

    # Exit a parse tree produced by KotlinParser#thisExpression.
    def exitThisExpression(self, ctx:KotlinParser.ThisExpressionContext):
        pass


    # Enter a parse tree produced by KotlinParser#superExpression.
    def enterSuperExpression(self, ctx:KotlinParser.SuperExpressionContext):
        pass

    # Exit a parse tree produced by KotlinParser#superExpression.
    def exitSuperExpression(self, ctx:KotlinParser.SuperExpressionContext):
        pass


    # Enter a parse tree produced by KotlinParser#controlStructureBody.
    def enterControlStructureBody(self, ctx:KotlinParser.ControlStructureBodyContext):
        pass

    # Exit a parse tree produced by KotlinParser#controlStructureBody.
    def exitControlStructureBody(self, ctx:KotlinParser.ControlStructureBodyContext):
        pass


    # Enter a parse tree produced by KotlinParser#controlStatement.
    def enterControlStatement(self, ctx:KotlinParser.ControlStatementContext):
        pass

    # Exit a parse tree produced by KotlinParser#controlStatement.
    def exitControlStatement(self, ctx:KotlinParser.ControlStatementContext):
        pass


    # Enter a parse tree produced by KotlinParser#ifExpression.
    def enterIfExpression(self, ctx:KotlinParser.IfExpressionContext):
        pass

    # Exit a parse tree produced by KotlinParser#ifExpression.
    def exitIfExpression(self, ctx:KotlinParser.IfExpressionContext):
        pass


    # Enter a parse tree produced by KotlinParser#whenExpression.
    def enterWhenExpression(self, ctx:KotlinParser.WhenExpressionContext):
        pass

    # Exit a parse tree produced by KotlinParser#whenExpression.
    def exitWhenExpression(self, ctx:KotlinParser.WhenExpressionContext):
        pass


    # Enter a parse tree produced by KotlinParser#whenSubject.
    def enterWhenSubject(self, ctx:KotlinParser.WhenSubjectContext):
        pass

    # Exit a parse tree produced by KotlinParser#whenSubject.
    def exitWhenSubject(self, ctx:KotlinParser.WhenSubjectContext):
        pass


    # Enter a parse tree produced by KotlinParser#whenGuard.
    def enterWhenGuard(self, ctx:KotlinParser.WhenGuardContext):
        pass

    # Exit a parse tree produced by KotlinParser#whenGuard.
    def exitWhenGuard(self, ctx:KotlinParser.WhenGuardContext):
        pass


    # Enter a parse tree produced by KotlinParser#whenEntry.
    def enterWhenEntry(self, ctx:KotlinParser.WhenEntryContext):
        pass

    # Exit a parse tree produced by KotlinParser#whenEntry.
    def exitWhenEntry(self, ctx:KotlinParser.WhenEntryContext):
        pass


    # Enter a parse tree produced by KotlinParser#whenCondition.
    def enterWhenCondition(self, ctx:KotlinParser.WhenConditionContext):
        pass

    # Exit a parse tree produced by KotlinParser#whenCondition.
    def exitWhenCondition(self, ctx:KotlinParser.WhenConditionContext):
        pass


    # Enter a parse tree produced by KotlinParser#rangeTest.
    def enterRangeTest(self, ctx:KotlinParser.RangeTestContext):
        pass

    # Exit a parse tree produced by KotlinParser#rangeTest.
    def exitRangeTest(self, ctx:KotlinParser.RangeTestContext):
        pass


    # Enter a parse tree produced by KotlinParser#typeTest.
    def enterTypeTest(self, ctx:KotlinParser.TypeTestContext):
        pass

    # Exit a parse tree produced by KotlinParser#typeTest.
    def exitTypeTest(self, ctx:KotlinParser.TypeTestContext):
        pass


    # Enter a parse tree produced by KotlinParser#tryExpression.
    def enterTryExpression(self, ctx:KotlinParser.TryExpressionContext):
        pass

    # Exit a parse tree produced by KotlinParser#tryExpression.
    def exitTryExpression(self, ctx:KotlinParser.TryExpressionContext):
        pass


    # Enter a parse tree produced by KotlinParser#catchBlock.
    def enterCatchBlock(self, ctx:KotlinParser.CatchBlockContext):
        pass

    # Exit a parse tree produced by KotlinParser#catchBlock.
    def exitCatchBlock(self, ctx:KotlinParser.CatchBlockContext):
        pass


    # Enter a parse tree produced by KotlinParser#finallyBlock.
    def enterFinallyBlock(self, ctx:KotlinParser.FinallyBlockContext):
        pass

    # Exit a parse tree produced by KotlinParser#finallyBlock.
    def exitFinallyBlock(self, ctx:KotlinParser.FinallyBlockContext):
        pass


    # Enter a parse tree produced by KotlinParser#loopStatement.
    def enterLoopStatement(self, ctx:KotlinParser.LoopStatementContext):
        pass

    # Exit a parse tree produced by KotlinParser#loopStatement.
    def exitLoopStatement(self, ctx:KotlinParser.LoopStatementContext):
        pass


    # Enter a parse tree produced by KotlinParser#forStatement.
    def enterForStatement(self, ctx:KotlinParser.ForStatementContext):
        pass

    # Exit a parse tree produced by KotlinParser#forStatement.
    def exitForStatement(self, ctx:KotlinParser.ForStatementContext):
        pass


    # Enter a parse tree produced by KotlinParser#whileStatement.
    def enterWhileStatement(self, ctx:KotlinParser.WhileStatementContext):
        pass

    # Exit a parse tree produced by KotlinParser#whileStatement.
    def exitWhileStatement(self, ctx:KotlinParser.WhileStatementContext):
        pass


    # Enter a parse tree produced by KotlinParser#doWhileStatement.
    def enterDoWhileStatement(self, ctx:KotlinParser.DoWhileStatementContext):
        pass

    # Exit a parse tree produced by KotlinParser#doWhileStatement.
    def exitDoWhileStatement(self, ctx:KotlinParser.DoWhileStatementContext):
        pass


    # Enter a parse tree produced by KotlinParser#jumpExpression.
    def enterJumpExpression(self, ctx:KotlinParser.JumpExpressionContext):
        pass

    # Exit a parse tree produced by KotlinParser#jumpExpression.
    def exitJumpExpression(self, ctx:KotlinParser.JumpExpressionContext):
        pass


    # Enter a parse tree produced by KotlinParser#callableReference.
    def enterCallableReference(self, ctx:KotlinParser.CallableReferenceContext):
        pass

    # Exit a parse tree produced by KotlinParser#callableReference.
    def exitCallableReference(self, ctx:KotlinParser.CallableReferenceContext):
        pass


    # Enter a parse tree produced by KotlinParser#assignmentAndOperator.
    def enterAssignmentAndOperator(self, ctx:KotlinParser.AssignmentAndOperatorContext):
        pass

    # Exit a parse tree produced by KotlinParser#assignmentAndOperator.
    def exitAssignmentAndOperator(self, ctx:KotlinParser.AssignmentAndOperatorContext):
        pass


    # Enter a parse tree produced by KotlinParser#equalityOperator.
    def enterEqualityOperator(self, ctx:KotlinParser.EqualityOperatorContext):
        pass

    # Exit a parse tree produced by KotlinParser#equalityOperator.
    def exitEqualityOperator(self, ctx:KotlinParser.EqualityOperatorContext):
        pass


    # Enter a parse tree produced by KotlinParser#comparisonOperator.
    def enterComparisonOperator(self, ctx:KotlinParser.ComparisonOperatorContext):
        pass

    # Exit a parse tree produced by KotlinParser#comparisonOperator.
    def exitComparisonOperator(self, ctx:KotlinParser.ComparisonOperatorContext):
        pass


    # Enter a parse tree produced by KotlinParser#inOperator.
    def enterInOperator(self, ctx:KotlinParser.InOperatorContext):
        pass

    # Exit a parse tree produced by KotlinParser#inOperator.
    def exitInOperator(self, ctx:KotlinParser.InOperatorContext):
        pass


    # Enter a parse tree produced by KotlinParser#isOperator.
    def enterIsOperator(self, ctx:KotlinParser.IsOperatorContext):
        pass

    # Exit a parse tree produced by KotlinParser#isOperator.
    def exitIsOperator(self, ctx:KotlinParser.IsOperatorContext):
        pass


    # Enter a parse tree produced by KotlinParser#additiveOperator.
    def enterAdditiveOperator(self, ctx:KotlinParser.AdditiveOperatorContext):
        pass

    # Exit a parse tree produced by KotlinParser#additiveOperator.
    def exitAdditiveOperator(self, ctx:KotlinParser.AdditiveOperatorContext):
        pass


    # Enter a parse tree produced by KotlinParser#multiplicativeOperator.
    def enterMultiplicativeOperator(self, ctx:KotlinParser.MultiplicativeOperatorContext):
        pass

    # Exit a parse tree produced by KotlinParser#multiplicativeOperator.
    def exitMultiplicativeOperator(self, ctx:KotlinParser.MultiplicativeOperatorContext):
        pass


    # Enter a parse tree produced by KotlinParser#asOperator.
    def enterAsOperator(self, ctx:KotlinParser.AsOperatorContext):
        pass

    # Exit a parse tree produced by KotlinParser#asOperator.
    def exitAsOperator(self, ctx:KotlinParser.AsOperatorContext):
        pass


    # Enter a parse tree produced by KotlinParser#prefixUnaryOperator.
    def enterPrefixUnaryOperator(self, ctx:KotlinParser.PrefixUnaryOperatorContext):
        pass

    # Exit a parse tree produced by KotlinParser#prefixUnaryOperator.
    def exitPrefixUnaryOperator(self, ctx:KotlinParser.PrefixUnaryOperatorContext):
        pass


    # Enter a parse tree produced by KotlinParser#postfixUnaryOperator.
    def enterPostfixUnaryOperator(self, ctx:KotlinParser.PostfixUnaryOperatorContext):
        pass

    # Exit a parse tree produced by KotlinParser#postfixUnaryOperator.
    def exitPostfixUnaryOperator(self, ctx:KotlinParser.PostfixUnaryOperatorContext):
        pass


    # Enter a parse tree produced by KotlinParser#memberAccessOperator.
    def enterMemberAccessOperator(self, ctx:KotlinParser.MemberAccessOperatorContext):
        pass

    # Exit a parse tree produced by KotlinParser#memberAccessOperator.
    def exitMemberAccessOperator(self, ctx:KotlinParser.MemberAccessOperatorContext):
        pass


    # Enter a parse tree produced by KotlinParser#modifiers.
    def enterModifiers(self, ctx:KotlinParser.ModifiersContext):
        pass

    # Exit a parse tree produced by KotlinParser#modifiers.
    def exitModifiers(self, ctx:KotlinParser.ModifiersContext):
        pass


    # Enter a parse tree produced by KotlinParser#modifier.
    def enterModifier(self, ctx:KotlinParser.ModifierContext):
        pass

    # Exit a parse tree produced by KotlinParser#modifier.
    def exitModifier(self, ctx:KotlinParser.ModifierContext):
        pass


    # Enter a parse tree produced by KotlinParser#classModifier.
    def enterClassModifier(self, ctx:KotlinParser.ClassModifierContext):
        pass

    # Exit a parse tree produced by KotlinParser#classModifier.
    def exitClassModifier(self, ctx:KotlinParser.ClassModifierContext):
        pass


    # Enter a parse tree produced by KotlinParser#memberModifier.
    def enterMemberModifier(self, ctx:KotlinParser.MemberModifierContext):
        pass

    # Exit a parse tree produced by KotlinParser#memberModifier.
    def exitMemberModifier(self, ctx:KotlinParser.MemberModifierContext):
        pass


    # Enter a parse tree produced by KotlinParser#visibilityModifier.
    def enterVisibilityModifier(self, ctx:KotlinParser.VisibilityModifierContext):
        pass

    # Exit a parse tree produced by KotlinParser#visibilityModifier.
    def exitVisibilityModifier(self, ctx:KotlinParser.VisibilityModifierContext):
        pass


    # Enter a parse tree produced by KotlinParser#varianceModifier.
    def enterVarianceModifier(self, ctx:KotlinParser.VarianceModifierContext):
        pass

    # Exit a parse tree produced by KotlinParser#varianceModifier.
    def exitVarianceModifier(self, ctx:KotlinParser.VarianceModifierContext):
        pass


    # Enter a parse tree produced by KotlinParser#functionModifier.
    def enterFunctionModifier(self, ctx:KotlinParser.FunctionModifierContext):
        pass

    # Exit a parse tree produced by KotlinParser#functionModifier.
    def exitFunctionModifier(self, ctx:KotlinParser.FunctionModifierContext):
        pass


    # Enter a parse tree produced by KotlinParser#propertyModifier.
    def enterPropertyModifier(self, ctx:KotlinParser.PropertyModifierContext):
        pass

    # Exit a parse tree produced by KotlinParser#propertyModifier.
    def exitPropertyModifier(self, ctx:KotlinParser.PropertyModifierContext):
        pass


    # Enter a parse tree produced by KotlinParser#inheritanceModifier.
    def enterInheritanceModifier(self, ctx:KotlinParser.InheritanceModifierContext):
        pass

    # Exit a parse tree produced by KotlinParser#inheritanceModifier.
    def exitInheritanceModifier(self, ctx:KotlinParser.InheritanceModifierContext):
        pass


    # Enter a parse tree produced by KotlinParser#parameterModifier.
    def enterParameterModifier(self, ctx:KotlinParser.ParameterModifierContext):
        pass

    # Exit a parse tree produced by KotlinParser#parameterModifier.
    def exitParameterModifier(self, ctx:KotlinParser.ParameterModifierContext):
        pass


    # Enter a parse tree produced by KotlinParser#reificationModifier.
    def enterReificationModifier(self, ctx:KotlinParser.ReificationModifierContext):
        pass

    # Exit a parse tree produced by KotlinParser#reificationModifier.
    def exitReificationModifier(self, ctx:KotlinParser.ReificationModifierContext):
        pass


    # Enter a parse tree produced by KotlinParser#platformModifier.
    def enterPlatformModifier(self, ctx:KotlinParser.PlatformModifierContext):
        pass

    # Exit a parse tree produced by KotlinParser#platformModifier.
    def exitPlatformModifier(self, ctx:KotlinParser.PlatformModifierContext):
        pass


    # Enter a parse tree produced by KotlinParser#contextParameters.
    def enterContextParameters(self, ctx:KotlinParser.ContextParametersContext):
        pass

    # Exit a parse tree produced by KotlinParser#contextParameters.
    def exitContextParameters(self, ctx:KotlinParser.ContextParametersContext):
        pass


    # Enter a parse tree produced by KotlinParser#contextParameter.
    def enterContextParameter(self, ctx:KotlinParser.ContextParameterContext):
        pass

    # Exit a parse tree produced by KotlinParser#contextParameter.
    def exitContextParameter(self, ctx:KotlinParser.ContextParameterContext):
        pass


    # Enter a parse tree produced by KotlinParser#label.
    def enterLabel(self, ctx:KotlinParser.LabelContext):
        pass

    # Exit a parse tree produced by KotlinParser#label.
    def exitLabel(self, ctx:KotlinParser.LabelContext):
        pass


    # Enter a parse tree produced by KotlinParser#annotation.
    def enterAnnotation(self, ctx:KotlinParser.AnnotationContext):
        pass

    # Exit a parse tree produced by KotlinParser#annotation.
    def exitAnnotation(self, ctx:KotlinParser.AnnotationContext):
        pass


    # Enter a parse tree produced by KotlinParser#statementAnnotation.
    def enterStatementAnnotation(self, ctx:KotlinParser.StatementAnnotationContext):
        pass

    # Exit a parse tree produced by KotlinParser#statementAnnotation.
    def exitStatementAnnotation(self, ctx:KotlinParser.StatementAnnotationContext):
        pass


    # Enter a parse tree produced by KotlinParser#singleAnnotation.
    def enterSingleAnnotation(self, ctx:KotlinParser.SingleAnnotationContext):
        pass

    # Exit a parse tree produced by KotlinParser#singleAnnotation.
    def exitSingleAnnotation(self, ctx:KotlinParser.SingleAnnotationContext):
        pass


    # Enter a parse tree produced by KotlinParser#multiAnnotation.
    def enterMultiAnnotation(self, ctx:KotlinParser.MultiAnnotationContext):
        pass

    # Exit a parse tree produced by KotlinParser#multiAnnotation.
    def exitMultiAnnotation(self, ctx:KotlinParser.MultiAnnotationContext):
        pass


    # Enter a parse tree produced by KotlinParser#annotationUseSiteTarget.
    def enterAnnotationUseSiteTarget(self, ctx:KotlinParser.AnnotationUseSiteTargetContext):
        pass

    # Exit a parse tree produced by KotlinParser#annotationUseSiteTarget.
    def exitAnnotationUseSiteTarget(self, ctx:KotlinParser.AnnotationUseSiteTargetContext):
        pass


    # Enter a parse tree produced by KotlinParser#unescapedAnnotation.
    def enterUnescapedAnnotation(self, ctx:KotlinParser.UnescapedAnnotationContext):
        pass

    # Exit a parse tree produced by KotlinParser#unescapedAnnotation.
    def exitUnescapedAnnotation(self, ctx:KotlinParser.UnescapedAnnotationContext):
        pass


    # Enter a parse tree produced by KotlinParser#simpleIdentifier.
    def enterSimpleIdentifier(self, ctx:KotlinParser.SimpleIdentifierContext):
        pass

    # Exit a parse tree produced by KotlinParser#simpleIdentifier.
    def exitSimpleIdentifier(self, ctx:KotlinParser.SimpleIdentifierContext):
        pass


    # Enter a parse tree produced by KotlinParser#identifier.
    def enterIdentifier(self, ctx:KotlinParser.IdentifierContext):
        pass

    # Exit a parse tree produced by KotlinParser#identifier.
    def exitIdentifier(self, ctx:KotlinParser.IdentifierContext):
        pass


    # Enter a parse tree produced by KotlinParser#shebangLine.
    def enterShebangLine(self, ctx:KotlinParser.ShebangLineContext):
        pass

    # Exit a parse tree produced by KotlinParser#shebangLine.
    def exitShebangLine(self, ctx:KotlinParser.ShebangLineContext):
        pass


    # Enter a parse tree produced by KotlinParser#quest.
    def enterQuest(self, ctx:KotlinParser.QuestContext):
        pass

    # Exit a parse tree produced by KotlinParser#quest.
    def exitQuest(self, ctx:KotlinParser.QuestContext):
        pass


    # Enter a parse tree produced by KotlinParser#elvis.
    def enterElvis(self, ctx:KotlinParser.ElvisContext):
        pass

    # Exit a parse tree produced by KotlinParser#elvis.
    def exitElvis(self, ctx:KotlinParser.ElvisContext):
        pass


    # Enter a parse tree produced by KotlinParser#safeNav.
    def enterSafeNav(self, ctx:KotlinParser.SafeNavContext):
        pass

    # Exit a parse tree produced by KotlinParser#safeNav.
    def exitSafeNav(self, ctx:KotlinParser.SafeNavContext):
        pass


    # Enter a parse tree produced by KotlinParser#excl.
    def enterExcl(self, ctx:KotlinParser.ExclContext):
        pass

    # Exit a parse tree produced by KotlinParser#excl.
    def exitExcl(self, ctx:KotlinParser.ExclContext):
        pass


    # Enter a parse tree produced by KotlinParser#semi.
    def enterSemi(self, ctx:KotlinParser.SemiContext):
        pass

    # Exit a parse tree produced by KotlinParser#semi.
    def exitSemi(self, ctx:KotlinParser.SemiContext):
        pass


    # Enter a parse tree produced by KotlinParser#semis.
    def enterSemis(self, ctx:KotlinParser.SemisContext):
        pass

    # Exit a parse tree produced by KotlinParser#semis.
    def exitSemis(self, ctx:KotlinParser.SemisContext):
        pass



del KotlinParser