from shared.domain.base import DomainException


class PredictionDeadlinePassedError(DomainException):
    pass


class PredictionAlreadyExistsError(DomainException):
    pass


class PredictionNotFoundError(DomainException):
    pass


class ValorInvalidoError(DomainException):
    pass


class EventoCerradoError(DomainException):
    pass
