class ClassTypeDataAdapter:
    def __init__(self):
        self.parent_class = None
        self.child_class = None
        self.package_name = ""
        self.file_path = ""

    def set_parent_class(self, parent):
        self.parent_class = parent

    def set_child_class(self, child):
        self.child_class = child

    def set_package_name(self, package):
        self.package_name = package

    def get_name(self):
        if self.child_class is None:
            raise ValueError("Child class is missing")
        return self.child_class

    def get_long_name(self):
        return self.package_name + "." + self.get_name()

    def has_parent(self):
        return self.parent_class is not None