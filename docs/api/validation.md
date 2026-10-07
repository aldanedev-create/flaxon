
# Validation API

## Schema

Base schema class for data validation.

### Constructor

```python
class Schema(metaclass=SchemaMeta):
    __fields__: dict[str, Field]
````

---

## Class Methods

### load

```python
@classmethod
def load(cls, data: Any) -> Schema
```

Load and validate data from a dictionary.

| Parameter | Type | Description                             |
| --------- | ---- | --------------------------------------- |
| data      | Any  | Data to validate (must be a dictionary) |

**Raises:**

`ValidationError` if validation fails.

**Returns:**

A schema instance with validated data.

Example:

```python
user = CreateUser.load({
    "name": "Alice",
    "email": "alice@example.com"
})
```

---

## Methods

### to_dict

```python
def to_dict(self) -> dict[str, Any]
```

Convert schema to a dictionary.

Example:

```python
data = user.to_dict()

# {
#   "name": "Alice",
#   "email": "alice@example.com"
# }
```

### to_json

```python
def to_json(self) -> dict[str, Any]
```

Convert schema to a JSON serializable dictionary.

Example:

```python
json_data = user.to_json()
```

### validate

```python
def validate(self) -> None
```

Validate schema data manually.

**Raises:**

`ValidationError` if validation fails.

---

# Fields

## StrField

String field with validation options.

```python
StrField(
    *,
    required: bool = False,
    default: Any = None,
    nullable: bool = False,
    min_length: int | None = None,
    max_length: int | None = None,
    strip: bool = True,
    pattern: str | None = None,
)
```

| Parameter  | Type       | Description              |
| ---------- | ---------- | ------------------------ |
| required   | bool       | Field must be present    |
| default    | Any        | Default value if missing |
| nullable   | bool       | Allow null values        |
| min_length | int | None | Minimum string length    |
| max_length | int | None | Maximum string length    |
| strip      | bool       | Remove whitespace        |
| pattern    | str | None | Regex pattern            |

Example:

```python
name = fields.StrField(
    required=True,
    min_length=2,
    max_length=80
)
```

---

## IntField

Integer field with range validation.

```python
IntField(
    *,
    required: bool = False,
    default: Any = None,
    nullable: bool = False,
    minimum: int | None = None,
    maximum: int | None = None,
)
```

| Parameter | Type       | Description           |
| --------- | ---------- | --------------------- |
| minimum   | int | None | Minimum allowed value |
| maximum   | int | None | Maximum allowed value |

Example:

```python
age = fields.IntField(
    minimum=13,
    maximum=120
)
```

---

## FloatField

Float field with range validation.

```python
FloatField(
    *,
    required: bool = False,
    default: Any = None,
    nullable: bool = False,
    minimum: float | None = None,
    maximum: float | None = None,
)
```

Example:

```python
price = fields.FloatField(
    minimum=0.0,
    maximum=9999.99
)
```

---

## BoolField

Boolean field.

```python
BoolField(
    *,
    required: bool = False,
    default: Any = None,
    nullable: bool = False,
)
```

Example:

```python
active = fields.BoolField(default=True)
```

---

## ChoiceField

Field with allowed values.

```python
ChoiceField(
    choices: list[Any] | tuple[Any, ...] | set[Any],
    *,
    required: bool = False,
    default: Any = None,
    nullable: bool = False,
)
```

| Parameter | Type               | Description    |
| --------- | ------------------ | -------------- |
| choices   | list | tuple | set | Allowed values |

Example:

```python
status = fields.ChoiceField(
    ["pending", "active", "deleted"],
    default="pending"
)
```

---

## EmailField

Email validation field.

```python
EmailField(
    *,
    required: bool = False,
    default: Any = None,
    nullable: bool = False,
    min_length: int | None = None,
    max_length: int | None = None,
)
```

Example:

```python
email = fields.EmailField(required=True)
```

---

## DateField

Date validation field.

```python
DateField(
    *,
    required: bool = False,
    default: Any = None,
    nullable: bool = False,
    format: str = "%Y-%m-%d",
)
```

| Parameter | Type | Description        |
| --------- | ---- | ------------------ |
| format    | str  | Date format string |

Example:

```python
birthday = fields.DateField(
    format="%Y-%m-%d"
)
```

---

## DateTimeField

Datetime validation field.

```python
DateTimeField(
    *,
    required: bool = False,
    default: Any = None,
    nullable: bool = False,
    format: str = "%Y-%m-%dT%H:%M:%S",
)
```

Example:

```python
created_at = fields.DateTimeField(
    format="%Y-%m-%dT%H:%M:%S"
)
```

---

## DecimalField

Decimal validation field.

```python
DecimalField(
    *,
    required: bool = False,
    default: Any = None,
    nullable: bool = False,
    minimum: Decimal | None = None,
    maximum: Decimal | None = None,
    places: int | None = None,
)
```

| Parameter | Type       | Description            |
| --------- | ---------- | ---------------------- |
| places    | int | None | Maximum decimal places |

Example:

```python
amount = fields.DecimalField(
    minimum=0,
    places=2
)
```

---

## UUIDField

UUID validation field.

```python
UUIDField(
    *,
    required: bool = False,
    default: Any = None,
    nullable: bool = False,
)
```

Example:

```python
token = fields.UUIDField(required=True)
```

---

## ListField

List field with item validation.

```python
ListField(
    item_field: Field | None = None,
    *,
    required: bool = False,
    default: Any = None,
    nullable: bool = False,
    min_items: int | None = None,
    max_items: int | None = None,
)
```

| Parameter  | Type         | Description                |
| ---------- | ------------ | -------------------------- |
| item_field | Field | None | Validation field for items |
| min_items  | int | None   | Minimum items              |
| max_items  | int | None   | Maximum items              |

Example:

```python
tags = fields.ListField(
    fields.StrField(min_length=1),
    min_items=1,
    max_items=10
)
```

---

## NestedField

Nested schema field.

```python
NestedField(
    schema_class: type[Schema],
    *,
    required: bool = False,
    default: Any = None,
    nullable: bool = False,
)
```

Example:

```python
class AddressSchema(Schema):
    street = fields.StrField(required=True)
    city = fields.StrField(required=True)


class UserSchema(Schema):
    name = fields.StrField(required=True)
    address = fields.NestedField(AddressSchema)
```

---

## AnyField

Accepts any value.

```python
AnyField(
    *,
    required: bool = False,
    default: Any = None,
    nullable: bool = False,
)
```

Example:

```python
metadata = fields.AnyField()
```

---

# Exceptions

## ValidationError

Raised when validation fails.

```python
ValidationError(
    fields: dict[str, list[str]]
)
```

| Attribute | Type                 | Description          |
| --------- | -------------------- | -------------------- |
| fields    | dict[str, list[str]] | Field error messages |

Example:

```python
try:
    user = CreateUser.load(data)

except ValidationError as exc:
    print(exc.fields)
```

---

## FieldError

Raised when a field validation fails.

```python
FieldError(message: str)
```

| Attribute | Type | Description   |
| --------- | ---- | ------------- |
| message   | str  | Error message |

---

# Complete Example

```python
from flaxon.validation import Schema, fields
from flaxon.validation.validators import (
    custom_validator,
    and_validators,
    pattern_validator,
)


def validate_unique_email(value, field):
    if value == "admin@example.com":
        raise FieldError("Email already registered")


class CreateUser(Schema):
    username = fields.StrField(
        required=True,
        min_length=3,
        max_length=30,
        validators=[
            and_validators(
                pattern_validator(
                    r"^[a-zA-Z0-9_]+$"
                )
            )
        ],
    )

    email = fields.EmailField(
        required=True,
        validators=[
            custom_validator(validate_unique_email)
        ],
    )

    password = fields.StrField(
        required=True,
        min_length=8,
        max_length=128,
    )

    age = fields.IntField(
        required=False,
        minimum=13,
        maximum=120,
    )

    role = fields.ChoiceField(
        ["user", "moderator", "admin"],
        default="user",
    )

    tags = fields.ListField(
        fields.StrField(min_length=1),
        max_items=10,
    )


@app.post("/users")
async def create_user(data: CreateUser):
    return {
        "user": data.to_dict()
    }
```


## Use this capability in a full-stack app

Flaxon serves Python APIs and Teloce interfaces in one project. Keep validation,
authorization and privileged operations on the server; components call those
endpoints and present their results. Follow the [full-stack lessons](../fullstack/index.md)
and [Teloce integration reference](../api/teloce.md) to connect this capability
to pages, components and application modules.
