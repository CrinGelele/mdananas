from django.conf import settings

class DBAppsRouter(object):

    def db_for_read(self, model, **hints):
        return "ideal"

    def db_for_write(self, model, **hints):
       return "ideal"

    def allow_relation(self, obj1, obj2, **hints):
        return None

    def allow_syncdb(self, db, model):
        return False

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db in settings.DATABASE_APPS_MAPPING.values():
            return settings.DATABASE_APPS_MAPPING.get(app_label) == db
        elif app_label in settings.DATABASE_APPS_MAPPING:
            return False