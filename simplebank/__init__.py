"""SimpleBank - a small command-line banking system."""
import logging

# Stay silent unless the app (cli.py) switches logging on.
logging.getLogger("simplebank").addHandler(logging.NullHandler())

__version__ = "0.1.0"