"""Чтение данных о зависимостях из репозитория PyPI."""

import json
import urllib.error
import urllib.request

TIMEOUT = 20
USER_AGENT = "depviz/0.1"
VERSION_SIGNS = "<>=!~"


def fetch_json(url: str) -> tuple[dict | None, str | None]:
    """Загружает JSON по адресу и возвращает (данные, ошибка)."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        return None, f"repository answered {error.code}: {url}"
    except urllib.error.URLError as error:
        return None, f"cannot reach repository: {error.reason}"
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return None, f"repository returned broken JSON: {url}"
    return data, None


def release_url(base: str, package: str, version: str) -> str:
    """Собирает адрес описания конкретной версии пакета."""
    return f"{base.rstrip('/')}/{package}/{version}/json"


def fetch_release(
    base: str, package: str, version: str
) -> tuple[dict | None, str | None]:
    """Возвращает имя, версию и список requires_dist пакета."""
    data, error = fetch_json(release_url(base, package, version))
    if error:
        return None, error
    info = data.get("info")
    if not info:
        return None, "repository response has no package information"
    requires = info.get("requires_dist") or []
    return {
        "name": info.get("name", package),
        "version": info.get("version", version),
        "requires": requires,
    }, None


def split_requirement(text: str) -> tuple[str, str, str]:
    """Делит строку requires_dist на имя, условие и маркер.

    Пример: "idna (<4,>=2.5)" даёт ("idna", "<4,>=2.5", "").
    """
    marker = ""
    rest = text
    if ";" in rest:
        rest, _, marker = rest.partition(";")
        marker = marker.strip()
    rest = rest.strip()
    if "(" in rest:
        name, _, tail = rest.partition("(")
        condition = tail.split(")")[0].strip()
        return name.strip(), condition, marker
    for index, char in enumerate(rest):
        if char in VERSION_SIGNS:
            return rest[:index].strip(), rest[index:].strip(), marker
    return rest, "", marker


def print_dependencies(name: str, version: str, requires: list[str]) -> None:
    """Печатает все прямые зависимости пакета."""
    print()
    print(f"{name} {version}: direct dependencies ({len(requires)})")
    for text in requires:
        package, condition, marker = split_requirement(text)
        line = package
        if condition:
            line = f"{line} {condition}"
        if marker:
            line = f"{line}  ; {marker}"
        print(f"  - {line}")
