import itertools
import json
import logging
import re
from enum import Enum
from pathlib import Path
from typing import Dict, Tuple, Optional, Iterable

import mmh3
from sqlalchemy import Connection

from echoes_data import models
from echoes_data.exceptions import LocalizationException

logger = logging.getLogger("echoes_data.lang")


def hash_string(string: str):
    return mmh3.hash(string, seed=2538058380, signed=False)


hash_string("一种特战武器，可以发射炸弹。这种发射器的独特构造使其仅需要少量能量即可发射威力强大的炸弹，但也会对发射器结构造成一定损伤。")


class Language(Enum):
    en = "en"
    de = "de"
    fr = "fr"
    ja = "ja"
    kr = "kr"
    por = "por"
    ru = "ru"
    spa = "spa"
    zh = "zh"
    zhcn = "zhcn"


class LocalizedString:
    def __init__(self, index: int, source: Optional[str]):
        self.id = index
        self.source = source  # type: Optional[str]
        self._translations = {}  # type: Dict[Language, str]

    def __getattr__(self, item):
        if item not in Language.__members__:
            raise AttributeError(f"Unknown language '{item}'")
        return self.get(Language[item])

    def __dir__(self):
        return itertools.chain(super().__dir__(), map(lambda l: l.name, self._translations.keys()))

    def __repr__(self):
        return f"String({self.id}: {self.source}"

    def get(self, lang: Language):
        if lang not in self._translations:
            return None
        return self._translations[lang]

    def set(self, lang: Language, string: str):
        self._translations[lang] = string

    def clone_with_source(self, source: str):
        new_string = LocalizedString(self.id, source)
        for lang, string in self._translations:
            new_string._translations[lang] = string
        return new_string


class LocalizationMap:
    complex_re = re.compile(r"{(?P<type>([^:}])*):(?P<source>([^}])*)}'")

    def __init__(self):
        # Map source strings directly to localization index of their hash values collide
        # ToDo: Implement hash collisions
        self.hash_collisions = {}
        # Maps localization indizes to strings
        self.localization = {}  # type: Dict[int, LocalizedString]
        # Maps the hash values to the message indizes
        self.msg_index = {}  # type: Dict[int, int]
        # Maps the source strings
        self.source_index = {}  # type: Dict[str, LocalizedString]
        # Save changed data to update db
        self.new_lang_cache = []

    def _lookup_complex_localization_id(self, source: str) -> None:
        for match in LocalizationMap.complex_re.finditer(source):
            s = match.group("source")
            index = self.lookup_localization_id(s)
            if index is None:
                raise LocalizationException(f"Localization missing for '{s}'")
            source = source[:match.span()[0]] + ("{%s}" % index) + source[match.span()[1]:]
        return None

    def lookup_localization_id(self, source: str, save_new=True) -> Optional[int]:
        if source == "g85tr":
            return None
        if LocalizationMap.complex_re.match(source):
            return self._lookup_complex_localization_id(source)
        source_hash = hash_string(source)
        index = self.msg_index.get(source_hash, None)
        if index is None:
            if not save_new:
                return None
            # String doesn't exist, has to get inserted manually
            index = source_hash
            if index in self.msg_index:
                logger.error("Hash collision detected for string '%s' with hash %s, index %s",
                             source, source_hash, self.msg_index[index])

        if index in self.localization:
            if self.localization[index].source is not None and self.localization[index].source != source:
                logger.warning("Replacing localization entry for index %s", index)
            if self.localization[index].source is None or self.localization[index].source != source:
                self.new_lang_cache.append(self.localization[index])
            self.localization[index].source = source
        else:
            if not save_new:
                return None
            self.localization[index] = LocalizedString(index, source)
            self.new_lang_cache.append(self.localization[index])
        return index

    def _get_complex_string(self, source: str, lang=Language.en) -> str:
        for match in LocalizationMap.complex_re.finditer(source):
            s = match.group("source")
            localized = self.get_localized_string(s, lang)
            if localized is None:
                raise LocalizationException(f"Localization missing for '{s}'")
            source = source[:match.span()[0]] + localized + source[match.span()[1]:]
        return source

    def get_localized_string(self,
                             source: str,
                             lang=Language.en,
                             return_def=True,
                             check_complex=True) -> str:
        if check_complex and LocalizationMap.complex_re.match(source):
            return self._get_complex_string(source, lang)
        if source in self.source_index:
            return self.source_index[source].get(lang)
        index = self.lookup_localization_id(source, save_new=False)
        if index is None:
            if return_def:
                return source
            raise LocalizationException(f"Index for localized string {source} not found")
        if index not in self.localization:
            if return_def:
                return source
            raise LocalizationException(f"Index {index} not found in lookup table for string {source}")
        return self.localization[index].get(lang)

    def load_strings(self, strings: Iterable[models.LocalizedString]):
        for loc_string in strings:
            new_str = LocalizedString(loc_string.id, loc_string.source)
            for lang in Language:
                new_str.set(lang, getattr(loc_string, lang.name))
            self.localization[loc_string.id] = new_str
            if loc_string.source is not None:
                self.source_index[loc_string.source] = new_str

    def load_msg_index(self, file_path: Path):
        with open(file_path, "r", encoding="utf-8") as file:
            raw = json.load(file)
        for key, value in raw.items():
            self.msg_index[int(key)] = value
