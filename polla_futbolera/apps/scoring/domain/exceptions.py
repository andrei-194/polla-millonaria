from shared.domain.base import DomainException


class ScoreAlreadyCalculatedError(DomainException):
    pass


class EventoSinResultadoError(DomainException):
    pass
