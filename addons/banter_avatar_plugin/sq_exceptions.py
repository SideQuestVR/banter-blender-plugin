class SqApiException(Exception):
    def __init__(self, http_code=None, message="Api Exception", inner=None):
        super().__init__(message)
        self.http_code = http_code
        self.inner = inner


class SqApiNetworkException(SqApiException):
    pass


class SqApiAuthException(SqApiException):
    pass


class SqAlreadyExistsException(SqApiException):
    pass
