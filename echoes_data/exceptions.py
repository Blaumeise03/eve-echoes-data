
class DataException(Exception):
    """
    The root exception for every database related error
    """
    pass


class DataNotFoundException(DataException):
    pass


class CacheException(DataException):
    pass


class DataIntegrityException(DataException):
    pass


class LocalizationException(DataException):
    pass
