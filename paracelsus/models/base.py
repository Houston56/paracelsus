from typing import Callable, Generic, Protocol, Sequence, TypeVar, Type

ReturnT = TypeVar("ReturnT")


class ValidationError(ValueError):
    pass

class ErrorContainer(Protocol):
    errors: list[ValidationError]


class Attribute(Generic[ReturnT]):
    """
    A simple descriptor to implement attributes validation upon assignment.
    """

    def __init__(self, type: Type, validators: Sequence[Callable[[str, ReturnT], ReturnT]] = ()):
        self.type = type
        self.validators = validators

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, instance: ErrorContainer, owner):
        if not instance:
            return self
        return instance.__dict__[self.name]

    def __delete__(self, instance: ErrorContainer):
        del instance.__dict__[self.name]

    def __set__(self, instance: ErrorContainer, value):
        if not isinstance(value, self.type):
            raise TypeError(f"{self.name!r} values must be of type {self.type!r}")

        for validator in self.validators:
            try:
                validator(self.name, value)
            except ValidationError as e:
                instance.errors.append(e)

        instance.__dict__[self.name] = value
