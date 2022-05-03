def get_name_entity(prefixes) -> str:
    pattern_static = ""
    pattern_generic = ""
    pattern_abstract = ""
    pattern_visibility = " Default"
    if "static" in prefixes:
        pattern_static = " Static"
    if "generic" in prefixes:
        pattern_generic = " Generic"
    if "abstract" in prefixes:
        pattern_abstract = " Abstract"
    elif "final" in prefixes:
        pattern_abstract = " Final"
    if "private" in prefixes:
        pattern_visibility = " Private"
    elif "public" in prefixes:
        pattern_visibility = " Public"
    elif "protected" in prefixes:
        pattern_visibility = " Protected"

    result_str = "Java{0}{1}{2} Class Type{3} Member".format(pattern_static, pattern_abstract, pattern_generic,
                                                             pattern_visibility)
    return result_str


def config_entity_type(type_entity):
    if type_entity == "class":
        return "Class Type"
    if type_entity == "interface":
        return "Interface Type"
    if type_entity == "variable":
        return "Variable"
    if type_entity == "method":
        return "Method"


def extract_is_constructor(prefixes):
    pattern_visibility = " Default"
    if "private" in prefixes:
        pattern_visibility = " Private"
    elif "public" in prefixes:
        pattern_visibility = " Public"
    elif "protected" in prefixes:
        pattern_visibility = " Protected"
    return f"Java Method Constructor Member{pattern_visibility}"


def extract_all_kind(prefixes, type_entity, is_constructor) -> str:
    if is_constructor:
        return extract_is_constructor(prefixes)

    pattern_static = ""
    pattern_generic = ""
    pattern_abstract = ""
    pattern_visibility = " Default"
    if "static" in prefixes:
        pattern_static = " Static"
    if "generic" in prefixes:
        pattern_generic = " Generic"
    if "abstract" in prefixes:
        pattern_abstract = " Abstract"
    elif "final" in prefixes:
        pattern_abstract = " Final"
    if "private" in prefixes:
        pattern_visibility = " Private"
    elif "public" in prefixes:
        pattern_visibility = " Public"
    elif "protected" in prefixes:
        pattern_visibility = " Protected"

    result_str = "Java{0}{1}{2} {3}{4} Member".format(pattern_static, pattern_abstract, pattern_generic,
                                                      config_entity_type(type_entity),
                                                      pattern_visibility)
    if type_entity == "interface":
        result_str = result_str.replace("Member", "").strip()
    return result_str
