from shared.domain.base import DomainException


class GroupNotFoundError(DomainException):
    pass


class InvalidInvitationCodeError(DomainException):
    pass


class AlreadyMemberError(DomainException):
    pass


class NotGroupAdminError(DomainException):
    pass


class CannotRemoveAdminError(DomainException):
    pass
