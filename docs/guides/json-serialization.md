# JSON responses and migration

Flaxon now encodes JSON with `orjson`. Returning a dictionary, list, or tuple
uses the same rules as `JSONResponse`. Python input objects are never modified.

| Python value | JSON output |
| --- | --- |
| Strings, booleans, null, finite floats | Corresponding JSON value |
| Integers from −9,007,199,254,740,991 to 9,007,199,254,740,991 | Number |
| Integers outside that range | Decimal string, preserving browser precision |
| `Decimal` | String, preserving decimal precision and trailing zeros |
| Aware datetime | ISO 8601 in UTC, ending in `Z` |
| Naive datetime | ISO 8601 without a timezone; no timezone is inferred |
| Date or time | ISO 8601 string |
| UUID | String |
| Enum | Its value, under these same rules |
| Dataclass instance or object with `model_dump()` | Object, under these same rules |

Nonfinite floats and decimals (`NaN`, infinity), nonstring dictionary keys,
cycles, bytes, sets, and unsupported objects raise an encoding error. Convert
unsupported objects explicitly. Invalid server response data is a server error,
not a request validation error. Do not expose internal exception details in
production.

```python
from decimal import Decimal
from flaxon import JSONResponse

@app.get('/balance')
async def balance():
    return JSONResponse({'amount': Decimal('12.30'), 'record_id': 2**60})
```

The response is `{"amount":"12.30","record_id":"1152921504606846976"}`.
Treat identifiers as strings in TypeScript and use a decimal library for exact
money arithmetic. JSON whitespace can differ from earlier releases; clients
should parse JSON instead of comparing its raw formatting.

## Preserve previous behavior during migration

For conventional endpoint return values, add this to your project's settings:

```python
JSON_SERIALIZER = 'legacy'
```

For an application constructed directly:

```python
app = Flaxon('example', config={'JSON_SERIALIZER': 'legacy'})
```

Explicit responses choose their own mode:

```python
from flaxon import LegacyJSONResponse

return LegacyJSONResponse(data)
# Equivalent: JSONResponse(data, legacy=True)
```

Legacy mode preserves the previous standard-library encoding, including integer
numbers, the `model_dump()` / `str()` fallback, and nonstandard `NaN` output.
Use it temporarily while updating clients. Explicit `JSONResponse` remains
modern even when application settings select legacy conventional returns.

## Request and routing performance

Headers, cookies, and query dictionaries are parsed once, on first access. Their
existing mutable interfaces remain available. Accessing cookies directly avoids
materializing unrelated headers. Existing session cookies are still loaded for
synchronous session access; empty public requests do not create sessions.

Static routes use exact lookup. Dynamic candidate lists are ordered during
registration instead of sorted for each request. A matching dynamic route may
handle a request whose static path exists only for a different HTTP method.
Dependency plans cache names and annotations, never provider values. Provider
replacement, parent containers, and request-local factories retain their behavior.

## Database tuning

Measure queries before changing indexes. Use pagination for list endpoints,
select only necessary columns, and use Tortoise `prefetch_related` / `select_related`
where relationships otherwise cause one query per row. Check SQLite query plans
with `EXPLAIN QUERY PLAN` and PostgreSQL plans with `EXPLAIN (ANALYZE, BUFFERS)`
in a suitable test environment. Index actual filter and ordering patterns through
explicit migrations; starting the server does not automatically add indexes.
