from shared.domain.base import DomainException


class UserAlreadyExistsError(DomainException):
    pass


class InvalidCredentialsError(DomainException):
    pass


class ProfileNotFoundError(DomainException):
    pass


class InvalidInvitationCodeError(DomainException):
    pass


class InvitationCodeExhaustedError(DomainException):
    pass


class InvitationCodeInactiveError(DomainException):
    pass
