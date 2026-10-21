## This hook updates the copyright year in the site configuration to the current year.
from datetime import datetime, timezone


def on_config(config, **kwargs):
    year = str(datetime.now(timezone.utc).year)
    config.copyright = config.copyright.format(year=year)
