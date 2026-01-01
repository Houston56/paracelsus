from dataclasses import dataclass, field

from .base import ValidationError, Attribute



def forbid_wildcard_for_modules(name: str, value: str) -> str:
    if value.endswith("**"):
        raise ValidationError("Wildcard (**) not allowed for modules scope")
    return value


def forbid_empty_segment(name: str, value: str) -> str:
    if any(not segment for segment in value.split(".")):
        raise ValidationError("Empty segment not allowed")
    return value


@dataclass(init=True, frozen=True)
class Pattern:
    errors: list[ValidationError] = field(default_factory=list)
    mask: Attribute[str] = field(
        default=Attribute[str](str, validators=[
            forbid_wildcard_for_modules,
            forbid_empty_segment
        ])
    )

    @property
    def tokens(self) -> list[str]:
        return self.mask.split(".")

    @property
    def serialized_errors(self) -> str:
        messages = [f"Errors found for {self.mask}:"]
        for error in self.errors:
            messages.append(f"  - {error}")
        return "\n".join(messages)

