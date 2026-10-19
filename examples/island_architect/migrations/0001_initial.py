from tortoise import migrations
from tortoise.migrations import operations as ops
from orjson import loads
from tortoise.fields.data import JSON_DUMPS
from tortoise import fields

class Migration(migrations.Migration):
    initial = True

    operations = [
        ops.CreateModel(
            name='Design',
            fields=[
                ('id', fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),
                ('name', fields.CharField(max_length=120)),
                ('scenario', fields.CharField(default='calm-day', max_length=40)),
                ('seed', fields.IntField(default=7)),
                ('graph', fields.JSONField(default=dict, encoder=JSON_DUMPS, decoder=loads)),
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
                ('updated_at', fields.DatetimeField(auto_now=True, auto_now_add=False)),
            ],
            options={'table': 'island_designs', 'app': 'models', 'pk_attr': 'id'},
            bases=['Model'],
        ),
    ]
