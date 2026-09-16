
# Validation

## Overview

Flaxon provides declarative validation schemas that automatically validate request data and inject validated objects into route handlers.

Validation supports:

- Type checking
- Required fields
- Length validation
- Range validation
- Custom validators
- Nested schemas
- Serialization
- Automatic error responses

---

# Basic Schema

```python
from flaxon.validation import Schema, fields


class CreateUser(Schema):

    name = fields.StrField(
        required=True,
        min_length=2,
        max_length=80
    )

    email = fields.EmailField(
        required=True
    )

    age = fields.IntField(
        required=False,
        minimum=13,
        maximum=120
    )
````

---

# Using Schemas in Routes

```python
@app.post("/users")
async def create_user(data: CreateUser):

    # Data is automatically validated

    return {
        "success": True,
        "user": data.to_dict()
    }
```

Invalid data automatically returns:

```json
{
    "error": {
        "code": "FX-VAL-001",
        "message": "Validation failed"
    }
}
```

---

# Field Types

## String

```python
class UserSchema(Schema):

    name = fields.StrField(
        required=True,
        min_length=2,
        max_length=80,
        strip=True,
        pattern=r"^[a-zA-Z\s]+$"
    )
```

---

## Integer

```python
class ProductSchema(Schema):

    price = fields.IntField(
        required=True,
        minimum=0,
        maximum=999999
    )
```

---

## Float

```python
class PriceSchema(Schema):

    amount = fields.FloatField(
        required=True,
        minimum=0.0,
        maximum=9999.99
    )
```

---

## Boolean

```python
class SettingsSchema(Schema):

    active = fields.BoolField(
        required=True
    )

    notifications = fields.BoolField(
        default=True
    )
```

---

## Choice

```python
class StatusSchema(Schema):

    status = fields.ChoiceField(
        [
            "pending",
            "active",
            "suspended",
            "deleted"
        ],
        required=True
    )
```

---

## Email

```python
class ContactSchema(Schema):

    email = fields.EmailField(
        required=True
    )
```

---

## Date

```python
class EventSchema(Schema):

    date = fields.DateField(
        required=True,
        format="%Y-%m-%d"
    )
```

---

## DateTime

```python
class ScheduleSchema(Schema):

    datetime = fields.DateTimeField(
        required=True,
        format="%Y-%m-%dT%H:%M:%S"
    )
```

---

## UUID

```python
class TokenSchema(Schema):

    token = fields.UUIDField(
        required=True
    )
```

---

## List Field

```python
class BulkCreateSchema(Schema):

    users = fields.ListField(
        item_field=fields.StrField(
            min_length=2
        ),
        min_items=1,
        max_items=100
    )
```

---

## Nested Schemas

```python
class AddressSchema(Schema):

    street = fields.StrField(
        required=True
    )

    city = fields.StrField(
        required=True
    )

    zipcode = fields.StrField(
        required=True,
        pattern=r"^\d{5}$"
    )



class UserSchema(Schema):

    name = fields.StrField(
        required=True
    )

    address = fields.NestedField(
        AddressSchema
    )
```

---

# Validation Errors

```python
@app.post("/users")
async def create_user(data: CreateUser):

    return {
        "user": data.to_dict()
    }
```

If validation fails:

```json
{
    "success": false,
    "error": {
        "code": "FX-VAL-001",
        "message": "Request validation failed.",
        "fields": {
            "email": [
                "Enter a valid email address."
            ],
            "age": [
                "Must be at least 13."
            ]
        }
    }
}
```

---

# Custom Validators

```python
from flaxon.validation.validators import custom_validator


def validate_unique_email(value, field):

    if email_exists(value):

        raise ValueError(
            "Email already registered"
        )


class CreateUser(Schema):

    email = fields.EmailField(
        required=True,
        validators=[
            custom_validator(
                validate_unique_email
            )
        ]
    )
```

---

# Combining Validators

```python
from flaxon.validation.validators import (
    and_validators,
    or_validators,
)



class UserSchema(Schema):

    username = fields.StrField(
        validators=[
            and_validators(
                length_validator(3, 20),
                pattern_validator(
                    r"^[a-zA-Z0-9_]+$"
                )
            )
        ]
    )


    contact = fields.StrField(
        validators=[
            or_validators(
                email_validator(),
                pattern_validator(
                    r"^\+\d{10,15}$"
                )
            )
        ]
    )
```

---

# Serialization

Objects returned from routes are automatically serialized.

```python
@app.get("/users/<int:user_id>")
async def get_user(user_id: int):

    user = await db.fetch_one(
        "SELECT * FROM users WHERE id = $1",
        user_id
    )

    return user
```

---

## Custom Serialization

```python
class UserSchema(Schema):

    name = fields.StrField()

    email = fields.EmailField()


    def to_dict(self):

        return {
            "name": self.name,
            "email": self.email,
            "display_name": self.name.upper()
        }
```

---

# Full Example

```python
from flaxon import Flaxon

from flaxon.validation import (
    Schema,
    fields
)

from flaxon.validation.validators import (
    custom_validator
)



app = Flaxon(
    "validation-demo"
)



def validate_unique_username(value, field):

    if value == "admin":

        raise ValueError(
            "Username already exists"
        )



class CreateUser(Schema):

    username = fields.StrField(
        required=True,
        min_length=3,
        max_length=30,
        pattern=r"^[a-zA-Z0-9_]+$",
        validators=[
            custom_validator(
                validate_unique_username
            )
        ]
    )


    email = fields.EmailField(
        required=True
    )


    password = fields.StrField(
        required=True,
        min_length=8,
        max_length=128
    )


    age = fields.IntField(
        required=False,
        minimum=13,
        maximum=120
    )


    role = fields.ChoiceField(
        [
            "user",
            "moderator",
            "admin"
        ],
        default="user"
    )



class UpdateUser(Schema):

    username = fields.StrField(
        min_length=3,
        max_length=30
    )


    email = fields.EmailField()


    age = fields.IntField(
        minimum=13,
        maximum=120
    )



@app.post("/users")
async def create_user(data: CreateUser):

    # Hash password before saving

    return {
        "success": True,
        "user": data.to_dict()
    }



@app.patch("/users/<int:user_id>")
async def update_user(
    user_id: int,
    data: UpdateUser
):

    return {
        "updated": True,
        "id": user_id,
        "data": data.to_dict()
    }
```

---

# Validation Best Practices

* Validate all incoming data.
* Never trust client input.
* Use schemas for API requests.
* Keep validation separate from business logic.
* Create reusable validators.
* Return meaningful validation errors.
* Validate file uploads.
* Validate authentication payloads.
* Use nested schemas for complex objects.

---

# Next Steps

Continue with:

* Authentication
* Authorization
* Serialization
* Error Handling
* Database Integration
* API Development


