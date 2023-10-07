
class DataException(Exception):
    """
    The root exception for every database related error
    """
    pass


class DataNotFoundException(DataException):
    pass


class CacheException(DataException):
    pass
