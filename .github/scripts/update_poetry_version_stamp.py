"""Update the version stamp in pyproject.toml."""

from operator import index
import os
import sys
import re


def update_version():
    """Update the version stamp in pyproject.toml."""
    version = "0.0.0"

    for index, value in enumerate(sys.argv):
        if value in ["--version", "-V"]:
            version = str(sys.argv[index + 1]).replace("v", "")

    with open(f"{os.getcwd()}/pyproject.toml", "r", encoding="utf-8") as file:
        content = file.read()
        content = re.sub(
            r'version = "[0-9]+\.[0-9]+\.[0-9]+"', f'version = "{version}"', content
        )
        with open(f"{os.getcwd()}/pyproject.toml", "w", encoding="utf-8") as file:
            file.write(content)


update_version()
