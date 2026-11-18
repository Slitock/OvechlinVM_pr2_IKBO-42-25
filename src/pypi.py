"""Чтение данных о зависимостях из репозитория PyPI."""

import json
import urllib.error
import urllib.request
from http.client import InvalidURL

TIMEOUT = 20
USER_AGENT = "depviz/0.1"
VERSION_SIGNS = "<>=!~"


def fetch_json(url: str) -> tuple[dict | None, str | None]:
    """Загружает JSON по адресу и возвращает (данные, ошибка)."""
    request = make_request(url)
    if request is None:
        return None, f"invalid repository URL: {url}"
    body, error = read_response(request, url)
    if error:
        return None, error
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        return None, f"repository returned non-UTF-8 data: {url}"
    try:
        return json.loads(text), None
    except json.JSONDecodeError:
        return None, f"repository returned broken JSON: {url}"


def make_request(url: str) -> urllib.request.Request | None:
    """Создаёт запрос и возвращает None для неверного адреса."""
    try:
        return urllib.request.Request(
            url, headers={"User-Agent": USER_AGENT}
        )
    except ValueError:
        return None


def read_response(
    request: urllib.request.Request, url: str
) -> tuple[bytes | None, str | None]:
    """Читает тело ответа и превращает сетевые ошибки в текст."""
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.read(), None
    except urllib.error.HTTPError as error:
        return None, f"repository answered {error.code}: {url}"
    except urllib.error.URLError as error:
        return None, f"cannot reach repository: {error.reason}"
    except (InvalidURL, ValueError):
        return None, f"invalid repository URL: {url}"


def release_url(base: str, package: str, version: str) -> str:
    """Собирает адрес описания конкретной версии пакета."""
    return f"{base.rstrip('/')}/{package}/{version}/json"


def index_url(base: str, package: str) -> str:
    """Собирает адрес последнего релиза пакета."""
    return f"{base.rstrip('/')}/{package}/json"


def release_from_info(
    info: dict, package: str, version: str
) -> dict:
    """Собирает описание релиза из поля info."""
    return {
        "name": info.get("name", package),
        "version": info.get("version", version),
        "requires": info.get("requires_dist") or [],
    }


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
    return release_from_info(info, package, version), None


def fetch_latest(base: str, package: str) -> tuple[dict | None, str | None]:
    """Возвращает описание последнего релиза пакета."""
    data, error = fetch_json(index_url(base, package))
    if error:
        return None, error
    info = data.get("info")
    if not info:
        return None, "repository response has no package information"
    return release_from_info(info, package, ""), None


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
