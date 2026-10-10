class ServiceError(Exception):
    def __init__(self, code: str, message: str, status: int = 503, retryable: bool = False):
        super().__init__(code)
        self.code, self.message, self.status, self.retryable = code, message, status, retryable

    def public(self, request_id: str) -> dict:
        return {'error': {'code': self.code, 'message': self.message, 'retryable': self.retryable}, 'requestId': request_id}
