import shortuuid
from django.db import models

class CustomShortUUIDField(models.CharField):
    def __init__(self, *args, prefix='', suffix='', **kwargs):
        self.prefix = prefix
        self.suffix = suffix
        kwargs['max_length'] = kwargs.get('max_length', 22 + len(prefix) + len(suffix))
        kwargs['editable'] = False
        kwargs['unique'] = True
        super().__init__(*args, **kwargs)

    def pre_save(self, model_instance, add):
        if add and not getattr(model_instance, self.attname):
            value = f"{self.prefix}{shortuuid.uuid()}{self.suffix}"
            setattr(model_instance, self.attname, value)
            return value
        return super().pre_save(model_instance, add)