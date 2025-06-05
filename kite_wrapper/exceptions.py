class KiteException(Exception):
    """
    Base class for all Kite Connect API exceptions.
    """
    def __init__(self, message, code=None):
        super(KiteException, self).__init__(message)
        self.code = code


class GeneralException(KiteException):
    """
    An unclassified error.
    """
    pass


class TokenException(KiteException):
    """
    An authentication, token parse or token expiry error.
    """
    pass


class PermissionException(KiteException):
    """
    An permission error.
    """
    pass


class OrderException(KiteException):
    """
    An order placement or modification error.
    """
    pass


class InputException(KiteException):
    """
    A validation error.
    """
    pass


class DataException(KiteException):
    """
    A data parse error.
    """
    pass


class NetworkException(KiteException):
    """
    A network down or request timeout error.
    """
    pass
