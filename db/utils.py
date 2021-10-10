
def get_object_or_create(cls, **kwargs):
    try:
        instance = cls.get(**kwargs)
        return instance, False
    except cls.DoesNotExist:
        instance = cls(**kwargs)
        res = instance.save()
        if res:
            return instance, True
        else:
            raise ConnectionError("Database disconnected, please try again!")

