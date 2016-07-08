from django.apps import AppConfig

class MyAppConfig(AppConfig):

    name = 'fulcrum'
    verbose_name = 'Django-Fulcrum'

    def ready(self):
        from fulcrum.sites import site