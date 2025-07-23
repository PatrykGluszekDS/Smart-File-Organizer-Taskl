class AutoSorterError(Exception):
    """Base error for the project."""

class InvalidPathError(AutoSorterError):
    pass

class RuleFileError(AutoSorterError):
    pass

class MoveError(AutoSorterError):
    pass
