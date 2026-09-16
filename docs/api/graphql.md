# GraphQL API Reference

---

# Schema

::: flaxon.graphql.schema.GraphQLSchema
    options:
        members:
            - __init__
            - add_type
            - get_type
            - get_types
            - add_directive
            - get_directives
            - resolver
            - execute
            - introspection

---

# Types

## ObjectType

::: flaxon.graphql.types.ObjectType
    options:
        members:
            - __init__
            - add_interface

---

## InterfaceType

::: flaxon.graphql.types.InterfaceType
    options:
        members:
            - __init__

---

## UnionType

::: flaxon.graphql.types.UnionType
    options:
        members:
            - __init__

---

## InputObjectType

::: flaxon.graphql.types.InputObjectType
    options:
        members:
            - __init__

---

## Field

::: flaxon.graphql.types.Field
    options:
        members:
            - __init__
            - resolve

---

## InputField

::: flaxon.graphql.types.InputField
    options:
        members:
            - __init__

---

## GraphQL List Type

::: flaxon.graphql.types.List
    options:
        members:
            - __init__

---

## NonNull

::: flaxon.graphql.types.NonNull
    options:
        members:
            - __init__

---

## Scalar

::: flaxon.graphql.types.Scalar
    options:
        members:
            - __init__
            - serialize
            - parse_value
            - parse_literal
            - set_serialize
            - set_parse_value
            - set_parse_literal

---

# Scalars

::: flaxon.graphql.scalars.ID

::: flaxon.graphql.scalars.DateTime

::: flaxon.graphql.scalars.Decimal

::: flaxon.graphql.scalars.JSON

::: flaxon.graphql.scalars.UUID

::: flaxon.graphql.scalars.URL

::: flaxon.graphql.scalars.Email

---

# Resolver

::: flaxon.graphql.resolver.Resolver
    options:
        members:
            - __init__
            - register
            - register_type_resolver
            - get
            - resolve

---

# Directives

## Directive

::: flaxon.graphql.directives.Directive
    options:
        members:
            - __init__
            - apply

---

## Built-in Directives

::: flaxon.graphql.directives.SkipDirective

::: flaxon.graphql.directives.IncludeDirective

::: flaxon.graphql.directives.DeprecatedDirective

::: flaxon.graphql.directives.DeferDirective

---

# Decorators

::: flaxon.graphql.decorators.graphql_type

::: flaxon.graphql.decorators.graphql_field

::: flaxon.graphql.decorators.graphql_query

::: flaxon.graphql.decorators.graphql_mutation

::: flaxon.graphql.decorators.graphql_subscription

---

# Subscriptions

## SubscriptionManager

::: flaxon.graphql.subscriptions.SubscriptionManager
    options:
        members:
            - __init__
            - subscribe
            - unsubscribe
            - publish
            - next
            - get_subscription_count
            - get_subscriptions_by_operation

---

## MemorySubscriptionBackend

::: flaxon.graphql.subscriptions.MemorySubscriptionBackend
    options:
        members:
            - connect
            - disconnect
            - subscribe
            - unsubscribe
            - publish
            - next

---

## RedisSubscriptionBackend

::: flaxon.graphql.subscriptions.RedisSubscriptionBackend
    options:
        members:
            - __init__
            - connect
            - disconnect
            - subscribe
            - unsubscribe
            - publish
            - next

---

# Middleware

::: flaxon.graphql.middleware.GraphQLMiddleware
    options:
        members:
            - __init__
            - add
            - __call__

---

# Extensions

## ComplexityExtension

::: flaxon.graphql.extensions.ComplexityExtension
    options:
        members:
            - __init__
            - set_cost
            - set_costs
            - get_cost
            - calculate_complexity
            - validate_complexity

---

## DepthLimitExtension

::: flaxon.graphql.extensions.DepthLimitExtension
    options:
        members:
            - __init__
            - calculate_depth
            - validate_depth

---

## PersistedQueriesExtension

::: flaxon.graphql.extensions.PersistedQueriesExtension
    options:
        members:
            - __init__
            - register
            - register_many
            - get
            - get_auto_hash
            - resolve_persisted_query
            - save_persisted_query
            - load_persisted_queries
            - save_persisted_queries

---

# Playgrounds

## GraphiQL

::: flaxon.graphql.playground.GraphiQLPlayground
    options:
        members:
            - __init__
            - render

---

## Altair

::: flaxon.graphql.playground.AltairPlayground
    options:
        members:
            - __init__
            - render

---

# Utilities

::: flaxon.graphql.utils.graphql

::: flaxon.graphql.utils.graphql_to_dict

::: flaxon.graphql.utils.graphql_to_json

::: flaxon.graphql.utils.graphql_format_error

::: flaxon.graphql.utils.graphql_is_valid_name

::: flaxon.graphql.utils.graphql_sanitize_name

---

# Exceptions

## GraphQLError

::: flaxon.graphql.exceptions.GraphQLError
    options:
        members:
            - __init__
            - to_dict

---

## GraphQL Exceptions

::: flaxon.graphql.exceptions.GraphQLSyntaxError

::: flaxon.graphql.exceptions.GraphQLValidationError

::: flaxon.graphql.exceptions.GraphQLExecutionError

::: flaxon.graphql.exceptions.GraphQLTypeError

---

# AST

::: flaxon.graphql.ast.Document

::: flaxon.graphql.ast.OperationDefinition

::: flaxon.graphql.ast.SelectionSet

::: flaxon.graphql.ast.Field

::: flaxon.graphql.ast.FragmentSpread

::: flaxon.graphql.ast.InlineFragment

::: flaxon.graphql.ast.FragmentDefinition

::: flaxon.graphql.ast.VariableDefinition

::: flaxon.graphql.ast.Variable

::: flaxon.graphql.ast.Name

::: flaxon.graphql.ast.Argument

::: flaxon.graphql.ast.Directive

::: flaxon.graphql.ast.NamedType

::: flaxon.graphql.ast.ListType

::: flaxon.graphql.ast.NonNullType

::: flaxon.graphql.ast.IntValue

::: flaxon.graphql.ast.FloatValue

::: flaxon.graphql.ast.StringValue

::: flaxon.graphql.ast.BooleanValue

::: flaxon.graphql.ast.ListValue

::: flaxon.graphql.ast.ObjectValue

::: flaxon.graphql.ast.ObjectField
