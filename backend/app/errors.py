"""Application errors with a stable JSON shape."""


class DomainError(Exception):
    def __init__(self, detail: str, status_code: int = 400, code: str = "bad_request") -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code
        self.code = code
