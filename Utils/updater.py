"""
Проверка на обновления.
"""
import re
from logging import getLogger
from locales.localizer import Localizer
import requests
import os
import zipfile
import shutil
import json
from pathlib import Path
from urllib.parse import quote

from project_info import REPOSITORY

logger = getLogger("FunPayNEXT.update_checker")
localizer = Localizer()
_ = localizer.translate

RELEASE_API = f"https://api.github.com/repos/{REPOSITORY}"
HEADERS = {
    "accept": "application/vnd.github+json"
}


class Release:
    """
    Класс, описывающий релиз.
    """

    def __init__(self, name: str, description: str, sources_link: str):
        """
        :param name: название релиза.
        :param description: описание релиза (список изменений).
        :param sources_link: ссылка на архив с исходниками.
        """
        self.name = name
        self.description = description
        self.sources_link = sources_link


def _release_version(tag: str) -> tuple[int, ...] | None:
    if not re.fullmatch(r"v?\d+(?:\.\d+){2,3}", tag):
        return None
    parts = tuple(int(part) for part in tag.removeprefix("v").split("."))
    return parts + (0,) * (4 - len(parts))


def get_new_releases(current_tag: str) -> int | list[Release]:
    """
    Возвращает новые стабильные релизы FunPayNEXT в порядке установки.

    Коды: 2 — установлена актуальная версия, 3 — ошибка GitHub, 4 — релизов пока нет.
    """
    current_version = _release_version(current_tag)
    if current_version is None:
        return 3

    candidates = []
    has_release = False
    page = 1
    try:
        while True:
            response = requests.get(f"{RELEASE_API}/releases", params={"page": page, "per_page": 100},
                                    headers=HEADERS, timeout=15)
            response.raise_for_status()
            for item in response.json():
                if item.get("draft") or item.get("prerelease"):
                    continue
                tag = item.get("tag_name") or ""
                version = _release_version(tag)
                if version is None:
                    continue
                has_release = True
                if version > current_version:
                    description = item.get("body") or ""
                    source = f"{RELEASE_API}/zipball/{quote(tag, safe='')}"
                    candidates.append((version, Release(tag, description, source)))
            if "next" not in response.links:
                break
            page += 1
    except (requests.RequestException, ValueError):
        logger.debug("TRACEBACK", exc_info=True)
        return 3

    if not has_release:
        return 4
    if not candidates:
        return 2

    releases = []
    for _, release in sorted(candidates, key=lambda candidate: candidate[0]):
        releases.append(release)
        if "#unskippable" in release.description:
            break
    return releases


#  Загрузка нового релиза
def download_zip(url: str) -> int:
    """
    Загружает zip архив с обновлением в файл storage/cache/update.zip.

    :param url: ссылка на zip архив.

    :return: 0, если архив с обновлением загружен, иначе - 1.
    """
    try:
        with requests.get(url, stream=True, timeout=(10, 30)) as r:
            r.raise_for_status()
            with open("storage/cache/update.zip", 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return 0
    except:
        logger.debug("TRACEBACK", exc_info=True)
        return 1


def extract_update_archive() -> str | int:
    """
    Разархивирует скачанный update.zip.

    :return: название папки с обновлением (storage/cache/update/<папка с обновлением>) или 1, если произошла ошибка.
    """
    try:
        if os.path.exists("storage/cache/update/"):
            shutil.rmtree("storage/cache/update/", ignore_errors=True)
        os.makedirs("storage/cache/update")

        with zipfile.ZipFile("storage/cache/update.zip", "r") as zip:
            folder_name = zip.filelist[0].filename
            zip.extractall("storage/cache/update/")
        return folder_name
    except:
        logger.debug("TRACEBACK", exc_info=True)
        return 1


def zipdir(path, zip_obj):
    """
    Рекурсивно архивирует папку.

    :param path: путь до папки.
    :param zip_obj: объект zip архива.
    """
    for root, dirs, files in os.walk(path):
        if os.path.basename(root) == "__pycache__":
            continue
        for file in files:
            zip_obj.write(os.path.join(root, file),
                          os.path.relpath(os.path.join(root, file),
                                          os.path.join(path, '..')))


def create_backup() -> int:
    """
    Создает резервную копию с папками storage и configs.

    :return: 0, если бэкап создан успешно, иначе - 1.
    """
    try:
        with zipfile.ZipFile("backup.zip", "w") as zip:
            zipdir("storage", zip)
            zipdir("configs", zip)
            zipdir("plugins", zip)
        return 0
    except:
        logger.debug("TRACEBACK", exc_info=True)
        return 1


def extract_backup_archive() -> bool:
    """
    Разархивирует скачанный backup.zip. в storage/cache/backup/

    :return: True, если разархивировано. False в случае ошибок.
    """
    try:
        if os.path.exists("storage/cache/backup/"):
            shutil.rmtree("storage/cache/backup/", ignore_errors=True)
        os.makedirs("storage/cache/backup")

        with zipfile.ZipFile("storage/cache/backup.zip", "r") as zip:
            zip.extractall("storage/cache/backup/")
        return True
    except:
        logger.debug("TRACEBACK", exc_info=True)
        return False


def install_release(folder_name: str) -> int:
    """
    Устанавливает обновление.

    :param folder_name: название папки со скачанным обновлением в storage/cache/update
    :return: 0, если обновление установлено.
        1 - произошла непредвиденная ошибка.
        2 - папка с обновлением отсутствует.
    """
    try:
        release_folder = os.path.join("storage/cache/update", folder_name)
        if not os.path.exists(release_folder):
            return 2

        obsolete_paths = []
        manifest = Path(release_folder, "delete.json")
        protected = {"configs", "logs", "plugins", "storage", ".git"}
        if manifest.is_file():
            for name in json.loads(manifest.read_text(encoding="utf-8")):
                path = Path(name)
                if (not path.parts or path.anchor or ".." in path.parts
                        or path.parts[0].lower() in protected
                        or not path.resolve().is_relative_to(Path.cwd())):
                    raise ValueError(f"Invalid update removal path: {name}")
                if path.is_dir():
                    raise ValueError(f"Update may remove obsolete files only: {name}")
                obsolete_paths.append(path)

        for i in os.listdir(release_folder):
            if i == "delete.json" or i.lower() in protected:
                continue

            source = os.path.join(release_folder, i)
            if source.endswith(".exe"):
                if not os.path.exists("update"):
                    os.mkdir("update")
                shutil.copy2(source, os.path.join("update", i))
                continue

            if os.path.isfile(source):
                shutil.copy2(source, i)
            else:
                shutil.copytree(source, os.path.join(".", i), dirs_exist_ok=True)

        for path in obsolete_paths:
            path.unlink(missing_ok=True)
        return 0
    except:
        logger.debug("TRACEBACK", exc_info=True)
        return 1


def install_backup() -> bool:
    """
    Устанавливает бэкап.
    """
    try:
        backup_folder = "storage/cache/backup"
        if not os.path.exists(backup_folder):
            return False

        for i in os.listdir(backup_folder):
            source = os.path.join(backup_folder, i)

            if os.path.isfile(source):
                shutil.copy2(source, i)
            else:
                shutil.copytree(source, os.path.join(".", i), dirs_exist_ok=True)
        return True
    except:
        logger.debug("TRACEBACK", exc_info=True)
        return False
