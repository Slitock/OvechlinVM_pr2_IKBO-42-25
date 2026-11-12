"""Построение графа зависимостей пакета Python.

Первый этап: читаем параметры командной строки, проверяем каждый
и печатаем их в формате «ключ-значение».
"""

import os
import sys

LETTERS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
DIGITS = "0123456789"
ALNUM = LETTERS + DIGITS
NAME_CHARS = ALNUM + "._-"
SEPARATORS = "._-"
FILTER_FORBIDDEN = " \t\n,"
MODES = ("real", "test")
REQUIRED = ("package", "repository", "version")
MAX_NAME_LENGTH = 128
WIDTH = len("repository") + 1

FLAGS = {
    "-p": "package",
    "--package": "package",
    "-r": "repository",
    "--repository": "repository",
    "-m": "mode",
    "--mode": "mode",
    "-V": "version",
    "--version": "version",
    "-f": "filter",
    "--filter": "filter",
}

DEFAULTS = {
    "package": "",
    "repository": "",
    "mode": "real",
    "version": "",
    "filter": "",
}


def read_options(args: list[str]) -> tuple[dict[str, str], str | None]:
    """Читает параметры из списка аргументов.

    Возвращает словарь параметров и текст ошибки (или None).
    """
    options = dict(DEFAULTS)
    index = 0
    while index < len(args):
        flag = args[index]
        if flag not in FLAGS:
            return options, f"unknown option: {flag}"
        if index + 1 >= len(args):
            return options, f"missing value for {flag}"
        options[FLAGS[flag]] = args[index + 1].strip()
        index += 2
    return options, None


def check_required(options: dict[str, str]) -> str | None:
    """Проверяет, что обязательные параметры заданы."""
    for name in REQUIRED:
        if options[name] == "":
            return f"missing option: --{name}"
    return None


def check_mode(mode: str) -> str | None:
    """Проверяет режим работы с репозиторием."""
    if mode not in MODES:
        return f"invalid mode: {mode!r}"
    return None


def check_package(name: str) -> str | None:
    """Проверяет имя пакета.

    Имя начинается и заканчивается буквой или цифрой, внутри может
    содержать точку, подчёркивание и дефис.
    """
    if name == "":
        return "package name must not be empty"
    if len(name) > MAX_NAME_LENGTH:
        return f"package name is longer than {MAX_NAME_LENGTH} characters"
    if name[0] not in ALNUM or name[-1] not in ALNUM:
        return f"invalid package name: {name!r}"
    for char in name:
        if char not in NAME_CHARS:
            return f"invalid package name: {name!r}"
    return None


def check_version(version: str) -> str | None:
    """Проверяет номер версии: цифры и точки, без краевых точек."""
    if version == "":
        return "version must not be empty"
    if version[0] not in DIGITS or version[-1] not in DIGITS:
        return f"invalid version: {version!r}"
    if ".." in version:
        return f"invalid version: {version!r}"
    for char in version:
        if char not in DIGITS + ".":
            return f"invalid version: {version!r}"
    return None


def check_filter(text: str) -> str | None:
    """Проверяет подстроку фильтра."""
    for char in FILTER_FORBIDDEN:
        if char in text:
            return f"filter must not contain whitespace or commas: {text!r}"
    return None


def check_url(location: str) -> str | None:
    """Проверяет, что адрес репозитория начинается с http или https."""
    if location.startswith("http://"):
        host = location[len("http://"):]
    elif location.startswith("https://"):
        host = location[len("https://"):]
    else:
        return f"repository URL must use http or https: {location!r}"
    if host == "" or host.startswith("/"):
        return f"repository URL has no host: {location!r}"
    return None


def check_repository(location: str, mode: str) -> str | None:
    """Проверяет репозиторий с учётом выбранного режима."""
    if location == "":
        return "repository must not be empty"
    if mode == "real":
        return check_url(location)
    if not os.path.isfile(location):
        return f"test repository file not found: {location!r}"
    return None


def check_all(options: dict[str, str]) -> str | None:
    """Проверяет все параметры по очереди."""
    error = check_required(options)
    if error:
        return error
    error = check_mode(options["mode"])
    if error:
        return error
    error = check_package(options["package"])
    if error:
        return error
    error = check_version(options["version"])
    if error:
        return error
    error = check_filter(options["filter"])
    if error:
        return error
    return check_repository(options["repository"], options["mode"])


def print_options(options: dict[str, str]) -> None:
    """Печатает параметры в формате «ключ-значение»."""
    for name in DEFAULTS:
        value = options[name]
        if value == "":
            value = "(none)"
        label = name + ":"
        print(f"{label:<{WIDTH}} {value}")


def main(argv: list[str] | None = None) -> int:
    """Запускает программу и возвращает код возврата."""
    if argv is None:
        argv = sys.argv[1:]
    options, error = read_options(argv)
    if error is None:
        error = check_all(options)
    if error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print_options(options)
    return 0


if __name__ == "__main__":
    sys.exit(main())
