from shared.domain.base import DomainException


class TournamentNotFoundError(DomainException):
    pass


class MatchNotFoundError(DomainException):
    pass


class SyncNotAllowedError(DomainException):
    pass
