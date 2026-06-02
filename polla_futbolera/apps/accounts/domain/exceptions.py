from shared.domain.base import DomainException


class UserAlreadyExistsError(DomainException):
    pass


class InvalidCredentialsError(DomainException):
    pass


class ProfileNotFoundError(DomainException):
    pass
