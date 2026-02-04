"""Typed property value models for HxAI Ingestion API.

These models represent the different value types that can be used
in content event properties, matching the v2 API schema.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class StringValue(BaseModel):
    """String property value.

    Supports single string or array of strings.

    Example:
        {"type": "string", "value": "Hello World"}
        {"type": "string", "value": ["tag1", "tag2"]}
    """

    model_config = ConfigDict(populate_by_name=True)

    type: Literal["string"] = "string"
    value: str | list[str]


class IntegerValue(BaseModel):
    """Integer property value.

    Supports single integer or array of integers.
    Range: -9007199254740991 to 9007199254740991 (JavaScript safe integers)

    Example:
        {"type": "integer", "value": 42}
        {"type": "integer", "value": [1, 2, 3]}
    """

    model_config = ConfigDict(populate_by_name=True)

    type: Literal["integer"] = "integer"
    value: int | list[int]


class FloatValue(BaseModel):
    """Float property value.

    Supports single float or array of floats.

    Example:
        {"type": "float", "value": 3.14159}
        {"type": "float", "value": [1.0, 2.5, 3.7]}
    """

    model_config = ConfigDict(populate_by_name=True)

    type: Literal["float"] = "float"
    value: float | list[float]


class BooleanValue(BaseModel):
    """Boolean property value.

    Supports single boolean or array of booleans.

    Example:
        {"type": "boolean", "value": true}
        {"type": "boolean", "value": [true, false, true]}
    """

    model_config = ConfigDict(populate_by_name=True)

    type: Literal["boolean"] = "boolean"
    value: bool | list[bool]


class DateValue(BaseModel):
    """Date property value (YYYY-MM-DD format).

    Supports single date string or array of date strings.
    Pattern: ^\\d{4}-\\d{2}-\\d{2}$

    Example:
        {"type": "date", "value": "2024-01-15"}
        {"type": "date", "value": ["2024-01-01", "2024-12-31"]}
    """

    model_config = ConfigDict(populate_by_name=True)

    type: Literal["date"] = "date"
    value: str | list[str]


class DatetimeValue(BaseModel):
    """Datetime property value (ISO 8601 with Z suffix).

    Supports single datetime string or array of datetime strings.
    Pattern: ^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d{1,3})?Z$

    Example:
        {"type": "datetime", "value": "2024-01-15T10:30:00.000Z"}
    """

    model_config = ConfigDict(populate_by_name=True)

    type: Literal["datetime"] = "datetime"
    value: str | list[str]


class CurrencyValue(BaseModel):
    """Currency property value (amount + 3-letter currency code).

    Supports single currency string or array of currency strings.
    Pattern: ^(-)?\\d+(\\.\\d+)?[A-Z]{3}$

    Example:
        {"type": "currency", "value": "12.34USD"}
        {"type": "currency", "value": ["-10.00EUR", "25.50GBP"]}
    """

    model_config = ConfigDict(populate_by_name=True)

    type: Literal["currency"] = "currency"
    value: str | list[str]


class ObjectValue(BaseModel):
    """Object property value.

    Supports single object (dict) or array of objects.

    Example:
        {"type": "object", "value": {"key": "value"}}
        {"type": "object", "value": [{"a": 1}, {"b": 2}]}
    """

    model_config = ConfigDict(populate_by_name=True)

    type: Literal["object"] = "object"
    value: dict[str, Any] | list[dict[str, Any]]


# Type alias for all typed property values
TypedPropertyValue = (
    StringValue
    | IntegerValue
    | FloatValue
    | BooleanValue
    | DateValue
    | DatetimeValue
    | CurrencyValue
    | ObjectValue
)
