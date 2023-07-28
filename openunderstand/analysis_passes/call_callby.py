"""
## Description
This module find all OpenUnderstand call and callby references in a Java project


## References


"""



from gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
import analysis_passes.class_properties as class_properties
from analysis_passes.general_scope_listener import GeneralScopeListener

implement = []

class CallAndCallBy(GeneralScopeListener):
    """
    #Todo: Implementing the ANTLR listener pass for Java Call and Java Callby reference kind
    """


    def __init__(self, file_full_path, available_package_classes, available_class_methods,
                 available_class_fields, class_parents):
        super(CallAndCallBy, self).__init__(file_full_path, available_package_classes, available_class_methods,
                                            available_class_fields, class_parents)
        # The dict has a key corresponding to the
        # entity_id of the reference owner entity
        # each key maps to an array of referenced entities
        # according to their entity id
        self.call_dict = {}
        self.non_dynamic_call_dict = {}
        self.in_local_variable_declaration = False
        self.is_var_non_primitive_type = False
        self.non_primitive_var_type = None
        self.local_method_variables = {}




    def enterClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        bodies = ctx.classBody().classBodyDeclaration()
        if bodies is not None:
            for body in bodies:
                member = getattr(body , 'memberDeclaration' , None)
                if member is not None:
                    member = member()
                    method = getattr(member , 'methodDeclaration' , None)
                    if method is not None:
                        method = method()
                        block = method.methodBody().block()
                        self.dfs(block , method ,ctx)


    def dfs(self , ctx , cls , context):
        bStatements = ctx.blockStatement()
        for bStatement in bStatements:
            kk = str(type(bStatement)).split('.')[-1][:-2]
            kk2 = "BlockStatement1Context"
            if kk == kk2:

                statement = bStatement.statement()

                s = getattr(statement , 'statement' , None)
                if s is not None:
                    s = s()
                    bb = getattr(s , 'block' , None)
                    if bb is not None:
                        bb = bb()
                        self.dfs(bb , cls , context)
                else:
                    exp = getattr(statement, 'expression', None)
                    if exp is not None:
                        exp = exp()
                        exp2 = getattr(exp , 'expression' , None)
                        if exp2 is not None:
                            exp2 = exp2()
                            primary = getattr(exp2, 'primary', None)
                            if primary is not None:
                                primary = primary()
                                super = getattr(primary, 'SUPER', None)
                                if super is not None:
                                    return

                        if type(exp) == list:
                            for exp3 in exp:
                                methodCall = getattr(exp3, 'methodCall', None)
                                if methodCall is not None:
                                    methodCall = methodCall()
                                    if methodCall is not None:
                                        called = methodCall.IDENTIFIER()
                                        scope_parents = class_properties.ClassPropertiesListener.findParents(context)

                                        if len(scope_parents) == 1:
                                            scope_longname = scope_parents[0]
                                        else:
                                            scope_longname = ".".join(scope_parents)


                                        line = context.children[0].symbol.line
                                        col = context.children[0].symbol.column
                                        self.implement.append(
                                            {"scope_kind": "Class", "scope_name": cls.IDENTIFIER().__str__(),
                                             "scope_longname": str(scope_longname),
                                             "scope_parent": scope_parents[-2] if len(scope_parents) > 2 else None,
                                             "scope_contents": cls.getText(),
                                             "scope_modifiers":
                                                 class_properties.ClassPropertiesListener.findClassOrInterfaceModifiers(
                                                     context),
                                             "line": line,
                                             "col": col,
                                             "type_ent_longname": str(called)})

                        else:
                            methodCall = getattr(exp, 'methodCall', None)
                            if methodCall is not None:
                                methodCall = methodCall()
                                if methodCall is not None:
                                    called = methodCall.IDENTIFIER()
                                    scope_parents = class_properties.ClassPropertiesListener.findParents(context)

                                    if len(scope_parents) == 1:
                                        scope_longname = scope_parents[0]
                                    else:
                                        scope_longname = ".".join(scope_parents)


                                    line = methodCall.start.line
                                    col = methodCall.start.column
                                    self.implement.append(
                                        {"scope_kind": "Class", "scope_name": cls.IDENTIFIER().__str__(),
                                         "scope_longname": str(scope_longname),
                                         "scope_parent": scope_parents[-2] if len(scope_parents) > 2 else None,
                                         "scope_contents": cls.getText(),
                                         "scope_modifiers":
                                             class_properties.ClassPropertiesListener.findClassOrInterfaceModifiers(
                                                 context),
                                         "line": line,
                                         "col": col,
                                         "type_ent_longname": str(called)})

    def enterLocalVariableDeclaration(self, ctx: JavaParserLabeled.LocalVariableDeclarationContext):
        self.in_local_variable_declaration = True

    def exitLocalVariableDeclaration(self, ctx: JavaParserLabeled.LocalVariableDeclarationContext):
        self.in_local_variable_declaration = False
        self.is_var_non_primitive_type = False
        self.non_primitive_var_type = None

    def enterClassOrInterfaceType(self, ctx: JavaParserLabeled.ClassOrInterfaceTypeContext):
        if type(ctx.parentCtx) is JavaParserLabeled.TypeTypeContext:
            self.is_var_non_primitive_type = True
            self.non_primitive_var_type = ctx.getText()

    def enterVariableDeclaratorId(self, ctx: JavaParserLabeled.VariableDeclaratorIdContext):
        if self.in_local_variable_declaration and self.is_var_non_primitive_type:
            variable_identifier = str(ctx.IDENTIFIER())
            current_scope_spec = self.scope_stack[len(self.scope_stack) - 1]
            # current_scope_spec['tp'] is guaranteed to be 'method'
            # because we are in local variable declaration
            if type(current_scope_spec) is list:
                current_scope_spec = current_scope_spec[1]
            if current_scope_spec['name'] not in self.local_method_variables.keys():
                self.local_method_variables[current_scope_spec['name']] = []
            self.local_method_variables[current_scope_spec['name']]\
                .append({'tp': self.get_fullname(self.non_primitive_var_type), 'name': variable_identifier})

    # normal invoking of a method (Call/CallBy) or with 'this'
    def enterMethodCall0(self, ctx: JavaParserLabeled.MethodCall0Context):
        # assuming that we have already filled our token_stream
        # using token_stream.fill() -> update : no need
        # token type 111 -> IDENTIFIER
        token = ctx.getTokens(111)[0].getPayload()
        arg_list = ctx.expressionList()
        arg_count = 0
        if arg_list is not None:
            arg_list = arg_list.getText()
            arg_count = arg_list.count(',')
        else:
            arg_list = ''
        # extracting the callee
        callee = ''
        if type(ctx.parentCtx) is JavaParserLabeled.Expression1Context:
            callee = ctx.parentCtx.getText()
            tmp = callee.rfind('.')
            if tmp >= 0:
                callee = callee[:tmp]
            tmp = callee.rfind('(')
            if tmp >= 0:
                tmp2 = callee.find(')')
                if tmp2 >= 0:
                    callee = callee[tmp + 1:tmp2]
                else:
                    callee = callee[tmp + 1:]
            else:
                tmp2 = callee.find(')')
                if tmp2 >= 0:
                    callee = callee[:tmp2]
        if callee != 'this' and callee != 'super'\
                and not callee.startswith('this.') and not callee.startswith('super.')\
                and callee != '':
            # extracting the callee
            callee_spec = self.which_local_variable(callee)
            if callee_spec is None:
                callee_spec = self.which_class_field(self.current_class_name, callee)
                if callee_spec is None:
                    # if caller is neither field nor variable
                    # it's a class name
                    callee_spec = {'tp': self.get_fullname(callee), 'name': None}
                    # find method fullname
                    # and fill self.call_dict
                    # based of method names
                    # It's definitely a static method from the class
                    # We now just see if it's from a parent, self or a surrounding class
                    method_fullname = \
                        self.which_method(callee_spec['tp'], str(ctx.IDENTIFIER()), arg_list, arg_count)
                    method_full_spec = self.get_method_full_spec(method_fullname[0]['name'], arg_list, arg_count)
                    # After the above instruction,
                    # method_full_spec == method_fullname[0] should be True
                    key = (method_full_spec['name'], method_full_spec['params'])
                    is_inherited_method = True if method_fullname[1] == 'parent' else False
                    # the following 'scope' key in the appended element
                    # can be of type class or method
                    # therefore, it might contain a 'params' field
                    if is_inherited_method:
                        self.fill_non_dynamic_call_dict(key, token.line, token.column, callee_spec['tp'])
                    else:
                        self.fill_call_dict(key, token.line, token.column)
                else:
                    # if caller is field
                    self.handle_field_or_variable_callee(ctx, callee_spec[0], arg_list, arg_count, token)
            else:
                # if caller is variable
                self.handle_field_or_variable_callee(ctx, callee_spec, arg_list, arg_count, token)
        elif callee == 'this':
            # There is no middle variable or field
            method_fullname = self.which_method(self.current_class_name, str(ctx.IDENTIFIER()), arg_list, arg_count)
            self.handle_this_or_super_or_empty_callee(method_fullname, token, False)
        elif callee == 'super':
            # There is no middle variable or field
            # in this case by is_inherited_method we mean the super class
            # itself has inherited the called method from another parent class itself
            # but it won't be necessary cause we don't care about it anymore
            method_fullname = self.which_method(self.class_parents[self.current_class_name],
                                                str(ctx.IDENTIFIER()), arg_list, arg_count)
            self.handle_this_or_super_or_empty_callee(method_fullname, token, True)
        elif callee.startswith('this.'):
            self.handle_this_dot_or_super_dot_callee(ctx, callee, arg_list, arg_count, token)
        elif callee.startswith('super.'):
            self.handle_this_dot_or_super_dot_callee(ctx, callee, arg_list, arg_count, token)
        else:
            method_fullname = self.which_method(self.current_class_name, str(ctx.IDENTIFIER()), arg_list, arg_count)
            self.handle_this_or_super_or_empty_callee(method_fullname, token, False)

    # for the purpose of refactoring
    def handle_this_or_super_or_empty_callee(self, method_fullname, token, is_super):
        key = (method_fullname[0]['name'], method_fullname[0]['params'])
        is_inherited_method = True if method_fullname[1] == 'parent' else False
        if is_inherited_method:
            self.fill_non_dynamic_call_dict(key, token.line, token.column,
                                            self.current_class_name if not is_super
                                            else self.class_parents[self.current_class_name])
        else:
            self.fill_call_dict(key, token.line, token.column)

    def handle_this_dot_or_super_dot_callee(self, ctx, callee, arg_list, arg_count, token):
        callee = callee[callee.index('.') + 1:]
        callee_spec = self.which_local_variable(callee)
        if callee_spec is None:
            callee_spec = self.which_class_field(self.current_class_name, callee)
            # this condition shouldn't really be satisfied
            if callee_spec is None:
                callee_spec = {'tp': self.get_fullname(callee), 'name': None}
        method_fullname = self.which_method(callee_spec['tp'], str(ctx.IDENTIFIER()), arg_list, arg_count)
        key = (method_fullname[0]['name'], method_fullname[0]['params'])
        is_inherited_method = True if method_fullname[1] == 'parent' else False
        if is_inherited_method:
            self.fill_non_dynamic_call_dict(key, token.line, token.column, self.current_class_name)
        else:
            self.fill_call_dict(key, token.line, token.column)

    def handle_field_or_variable_callee(self, ctx, callee_spec, arg_list, arg_count, token):
        method_fullname = self.which_method(callee_spec['tp'] if type(callee_spec) is not str else callee_spec,
                                            str(ctx.IDENTIFIER()), arg_list, arg_count)
        key = (method_fullname[0]['name'], method_fullname[0]['params'])
        is_inherited_method = True if method_fullname[1] == 'parent' else False
        if is_inherited_method:
            self.fill_non_dynamic_call_dict(key, token.line, token.column, callee_spec['tp'])
        else:
            self.fill_call_dict(key, token.line, token.column)

    def fill_non_dynamic_call_dict(self, key, line, column, called_through_child):
        if key not in self.non_dynamic_call_dict:
            self.non_dynamic_call_dict[key] = []
        self.non_dynamic_call_dict[key].append({'file': self.abspath,
                                                'scope': self.scope_stack[len(self.scope_stack) - 1],
                                                'called_through_child': called_through_child,
                                                'line': line,
                                                'column': column})

    def fill_call_dict(self, key, line, column):
        if key not in self.call_dict.keys():
            self.call_dict[key] = []
        self.call_dict[key].append({'file': self.abspath,
                                    # caller scope
                                    'scope': self.scope_stack[len(self.scope_stack) - 1],
                                    'called_through_child': None,
                                    'line': line,
                                    'column': column})

    # checks if the given field belongs to the current class
    # or a surrounding class
    # or a parent class
    def which_class_field(self, class_long_name, field_name):
        for classname in self.class_fields_repo:
            for field in self.class_fields_repo[classname]:
                if field_name == field['name']:
                    if classname == class_long_name:
                        return [field, 'self']
                    elif class_long_name.startswith(classname):
                        return [field, 'surrounding']
                    elif class_long_name in self.class_parents.keys()\
                            and self.class_parents[class_long_name] == classname:
                        return [field, 'parent']
                    else:
                        return [field, 'other']
        return None

    def which_local_variable(self, var_name):
        for method in self.local_method_variables:
            for var in self.local_method_variables[method]:
                if var_name == var['name']:
                    return var
        return var_name

    def which_method(self, class_long_name, method_name, method_params, param_count):
        for classname in self.all_classes_repo:
            if classname in self.class_methods_repo.keys():
                for method in self.class_methods_repo[classname]:
                    if (method_name == method['name'] or method['name'].endswith(method_name))\
                            and method['params'].count(',') == param_count:
                        if classname == class_long_name:
                            return [method, 'self']
                        elif class_long_name.startswith(classname + '.'):
                            return [method, 'surrounding']
                        elif class_long_name in self.class_parents.keys()\
                                and self.class_parents[class_long_name] == classname:
                            return [method, 'parent']
                        else:
                            return [method, 'other']
        return [{'name': method_name, 'params': method_params}, 'other']

    def get_method_full_spec(self, name, params, param_count):
        for classname in self.class_methods_repo.keys():
            if classname in self.class_methods_repo.keys():
                for method in self.class_methods_repo[classname]:
                    if method['name'] == name and method['params'].count(',') == param_count:
                        return method
                    elif method['name'].endswith('.' + name) and method['params'].count(',') == param_count:
                        return method
        for classname in self.available_imported_classes:
            index = name.rfind('.')
            tmp_name = name
            right_slice = name
            if index >= 0:
                tmp_name = name[:index]
                right_slice = name[index + 1:]
            if classname.endswith(tmp_name):
                return {'name': tmp_name + '.' + right_slice, 'params': params}
        return {'name': name, 'params': params}

    def get_result_dicts(self):
        return [self.call_dict, self.non_dynamic_call_dict]
