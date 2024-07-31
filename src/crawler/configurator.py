from dynaconf import Dynaconf, Validator

settings = Dynaconf(
    envvar_prefix="DYNACONF",
    settings_files=["settings.yaml"],
    lowercase_envvars=True,
    lowercase_read=True,
    validators=[
        Validator(
            "threads", "output_file", "base_url", "delay", "requests_to_delay", must_exist=True
        ),
        Validator("proxies", default=[])
    ],
)
