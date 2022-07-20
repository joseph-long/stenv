import importlib.metadata
import re
import sys
from pathlib import Path
from typing import Mapping, Dict, Tuple

import yaml
from packaging.version import Version

ENVIRONMENT_FILENAME = Path(__file__).parent.parent / "spacetelescope-env-latest.yml"
DEPENDENCY_PATTERN = re.compile(r"([\w\d-]+)\s*((?:[<>=~]=?|\^)\s*[\d\w.]*)?")
MINIMUM_DEPENDENCY_PATTERN = re.compile(r".*>=?\s*([\d\w.]+).*")

INSTALLED_PACKAGES = {
    distribution.metadata["name"].lower(): distribution.metadata["version"]
    for distribution in importlib.metadata.distributions()
}

DEPENDENCIES = {}

with open(ENVIRONMENT_FILENAME) as environment_file:
    environment = yaml.safe_load(environment_file)


def parse_dependency(
    dependency: str,
    dependencies: Dict[str, Tuple[str, str]],
    version_specification_pattern: re.Pattern = DEPENDENCY_PATTERN,
):
    match = re.match(version_specification_pattern, dependency)
    if match is not None:
        groups = match.groups()
        dependencies[groups[0]] = groups[1]


for dependency in environment["dependencies"]:
    if isinstance(dependency, Mapping):
        dependency = list(dependency.items())[0]
        if dependency[0] == "pip":
            [
                parse_dependency(dependency=pip_dependency, dependencies=DEPENDENCIES)
                for pip_dependency in dependency[1]
            ]


def check_package(
    package_name: str, minimum_version: Version = None, verbose: bool = True
) -> bool:
    if package_name in INSTALLED_PACKAGES:
        installed_version = Version(INSTALLED_PACKAGES[package_name])
        if minimum_version is not None:
            if not isinstance(minimum_version, Version):
                minimum_version = Version(str(minimum_version))
            if installed_version < minimum_version:
                print(
                    f'"{package_name}" is installed ({installed_version}) but out of date ({minimum_version} required)',
                    file=sys.stderr,
                )
                return False
        if verbose:
            print(f'"{package_name}" is installed ({installed_version})')
    else:
        print(f'"{package_name}" is not installed', file=sys.stderr)
        return False
    return True


def test_package_install():
    errors = []
    for package_name, specification in DEPENDENCIES.items():
        if specification is not None:
            min_version = re.match(MINIMUM_DEPENDENCY_PATTERN, specification)
            if min_version is not None:
                min_version = Version(min_version.groups()[0])
        else:
            min_version = None
        if not check_package(package_name, minimum_version=min_version):
            errors.append(package_name)
    assert len(errors) == 0


def test_module_import():
    errors = []
    for package_name in DEPENDENCIES:
        if package_name not in ["ipython"]:
            try:
                importlib.import_module(package_name)
            except (ImportError, ModuleNotFoundError):
                errors.append(package_name)

    assert len(errors) == 0