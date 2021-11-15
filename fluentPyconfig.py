from dynaconf import Dynaconf
import os

path,_ = os.path.split(__file__)
settings = Dynaconf(
    settings_files=[os.path.join(path,'settings.toml')],
    environments = True,
    envvar_prefix = 'FLUENTPY'
)