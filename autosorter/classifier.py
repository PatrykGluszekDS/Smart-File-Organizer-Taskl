from pathlib import Path
import json
from typing import Dict, Tuple, List
from .models import FileRecord
from .default_rules import DEFAULT_EXTENSION_MAP, DEFAULT_OTHER_FOLDER

class RuleSet:
    """Holds extension→folder mapping, loaded from defaults + optional JSON file."""
    def __init__(self, user_rules_path: Path | None = None):
        self.map: Dict[str, str] = dict(DEFAULT_EXTENSION_MAP)
        if user_rules_path:
            self._load_user_rules(user_rules_path)

    def _load_user_rules(self, path: Path):
        if not path.exists():
            raise FileNotFoundError(f"Rules file not found: {path}")
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        for ext, folder in data.items():
            if ext == "folders":
                continue
            if not ext.startswith(".") and ext != "no_extension":
                # Be kind: auto-fix missing dot
                ext = "." + ext.lower()
            self.map[ext.lower()] = folder

    def classify(self, rec: FileRecord) -> str:
        ext = rec.ext.lower()
        if ext == "":
            return self.map.get("no_extension", DEFAULT_OTHER_FOLDER)
        return self.map.get(ext, DEFAULT_OTHER_FOLDER)

class Classifier:
    """Given a list of FileRecord, return (record, target_folder_name) tuples."""
    def __init__(self, rule_set: RuleSet):
        self.rules = rule_set

    def assign(self, files: List[FileRecord]) -> List[Tuple[FileRecord, str]]:
        return [(f, self.rules.classify(f)) for f in files]
