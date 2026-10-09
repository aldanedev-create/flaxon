"""Public wire contract, migration mode, and lazy request regressions."""
import datetime as dt
import json
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

import pytest

from flaxon import JSONResponse, LegacyJSONResponse
from flaxon.http import Request
from flaxon.http.serialization import dumps
from flaxon.routing import Router
from flaxon.exceptions import MethodNotAllowed, NotFound
from flaxon.dependency_injection.container import Container
from flaxon.routing.execution import EndpointPlan


def test_browser_safe_values():
    value = {'money': Decimal('12.30'), 'large': 2**60,
             'time': dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc),
             'naive': dt.datetime(2026, 1, 1), 'date': dt.date(2026, 1, 1)}
    assert json.loads(dumps(value)) == {'money': '12.30', 'large': str(2**60),
        'time': '2026-01-01T00:00:00Z', 'naive': '2026-01-01T00:00:00', 'date': '2026-01-01'}
    assert value['large'] == 2**60


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -float('inf'), Decimal('NaN')])
def test_reject_nonfinite(value):
    with pytest.raises((ValueError, TypeError)):
        dumps({'nested': [value]})


@pytest.mark.parametrize('value', [object(), b'bytes', {1: 'invalid key'}, {1, 2}])
def test_reject_unsupported(value):
    with pytest.raises(TypeError):
        dumps(value)


def test_cycles_and_repeated_references():
    shared = {'ok': True}
    assert json.loads(dumps([shared, shared])) == [shared, shared]
    shared['cycle'] = shared
    with pytest.raises(TypeError):
        dumps(shared)


def test_models_and_dataclasses():
    @dataclass
    class Item:
        amount: Decimal
    class Model:
        def model_dump(self):
            return {'item': Item(Decimal('1.20'))}
    assert json.loads(dumps(Model())) == {'item': {'amount': '1.20'}}


def test_enum_numbers_are_safe():
    class Number(Enum):
        BIG = 2**60
    assert json.loads(dumps({'number': Number.BIG})) == {'number': str(2**60)}


def test_legacy_mode_preserves_old_outputs():
    assert json.loads(LegacyJSONResponse({'n': 2**60}).body)['n'] == 2**60
    assert JSONResponse({'n': 2**60}, legacy=True).body == LegacyJSONResponse({'n': 2**60}).body
    assert b'NaN' in dumps(float('nan'), legacy=True)


def test_lazy_request_views_are_cached_and_mutable():
    request = Request({'type': 'http', 'headers': [(b'cookie', b'a=b=c')],
                       'query_string': b'a=1&a=2&empty='}, None)
    assert request._headers is request._cookies is request._query is None
    assert request.cookies['a'] == 'b=c'
    assert request._headers is None
    assert request.query == {'a': '1', 'empty': ''}
    assert request.query_params is request.query
    request.query['a'] = 'changed'
    assert request.query_params['a'] == 'changed'


def test_static_wrong_method_can_fall_back_to_dynamic():
    router = Router()
    router.get('/api/fixed')(lambda: None)
    endpoint = lambda: None
    router.post('/api/<name>')(endpoint)
    assert router.match('/api/fixed', 'POST').route.endpoint is endpoint
    with pytest.raises(MethodNotAllowed):
        router.match('/api/fixed', 'DELETE')
    with pytest.raises(NotFound):
        router.match('/missing', 'GET')


def test_dependency_plan_retains_parent_scope_and_replacements():
    parent = Container()
    parent.register_instance('value', 'parent')
    class ContextProvider:
        def get(self, container):
            return container.get('value')
    parent.register('service', ContextProvider())
    child = parent.create_child()
    child.register_instance('value', 'child')
    def endpoint(service):
        pass
    plan = EndpointPlan.prepare(endpoint)
    assert child._resolver.resolve_plan(plan) == {'service': 'parent'}
    parent.register_instance('service', 'replacement')
    assert child._resolver.resolve_plan(plan) == {'service': 'replacement'}


def test_application_mode_and_explicit_response():
    from flaxon import Flaxon, Response
    app = Flaxon('legacy', debug=True, config={'JSON_SERIALIZER': 'legacy'})
    assert json.loads(Response.from_value({'n': 2**60}, json_mode=app.json_mode).body)['n'] == 2**60
    assert json.loads(JSONResponse({'n': 2**60}).body)['n'] == str(2**60)
    with pytest.raises(ValueError, match='JSON_SERIALIZER'):
        Flaxon('invalid', config={'JSON_SERIALIZER': 'unknown'})


def test_nonfinite_model_and_dataclass():
    @dataclass
    class Item:
        value: float
    class Model:
        def model_dump(self):
            return {'value': float('nan')}
    for value in (Item(float('nan')), Model()):
        with pytest.raises((TypeError, ValueError)):
            dumps(value)
