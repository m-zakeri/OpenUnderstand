from peewee import *

db = SqliteDatabase('../database.db', pragmas={
    'journal_mode': 'wal',
    'cache_size': -1 * 64000,  # 64MB
    'ignore_check_constraints': 0,
    'synchronous': 0})


class Kind(Model):
    """
    This table will fill automatically.
    """
    id = AutoField()
    inverse = ForeignKeyField('self', null=True)
    name = CharField(max_length=256, unique=True)

    is_ent_kind = BooleanField(default=True)

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return str(self.name)

    @property
    def is_ref_kind(self):
        return not self.is_ent_kind

    def check(self, kind_string: str):
        """
        Return true if the kind matches the filter string kind_string.
        """
        # TODO: Complete this method.
        return False

    def inv(self):
        """
        The logical inverse of a reference kind. This will throw an
        OpenUnderstandError if called with an entity kind.
        """
        if self.is_ent_kind:
            raise OperationalError("Entity kind has no inverse.")
        return self.inverse

    @staticmethod
    def list_entity(ent_kind: str):
        """
        Return the list of entity kinds that match the filter ent_kind.

        If no ent_kind is given, all entity kinds are returned. For example,
        to get the list of all c function entity kinds:
          kinds = understand.Kind.list_entity("c function")
        """
        return None

    @staticmethod
    def list_reference(ref_kind: str):
        """
        Return the list of reference kinds that match the filter refkind.

        If no refkind is given, all reference kinds are returned. For example,
        to get the list of all ada declare reference kinds:
          kinds = understand.Kind.list_entity("ada declare")
        """
        return None

    class Meta:
        database = db


class Entity(Model):
    id = AutoField()
    kind = ForeignKeyField(Kind, backref='entities')
    parent = ForeignKeyField('self', backref='children', null=True)
    name = CharField(max_length=512)
    longname = CharField(max_length=512)
    value = CharField(max_length=512, null=True)
    type = CharField(max_length=512, null=True)

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return str(self.longname)

    class Meta:
        database = db

    # TODO: Implement other methods


class Reference(Model):
    id = AutoField()
    kind = ForeignKeyField(Kind, backref='references')
    file = CharField(max_length=1024)
    line = IntegerField()
    column = IntegerField()
    ent = ForeignKeyField(Entity, backref='refs')
    scope = ForeignKeyField(Entity, backref='inv_refs')

    class Meta:
        database = db

    # TODO: Implement other methods


class Database(Model):
    name = CharField(max_length=128)
    language = CharField(max_length=128, default="Java")
    root = CharField(max_length=1024)

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return str(self.name)

    class Meta:
        database = db


if __name__ == '__main__':
    db.connect()
    db.create_tables(
        models=[Database, Kind, Entity, Reference, ],
    )
