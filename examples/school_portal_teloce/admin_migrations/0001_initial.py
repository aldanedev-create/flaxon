from tortoise import migrations
from tortoise.migrations import operations as ops
from orjson import loads
from tortoise.fields.data import JSON_DUMPS
from tortoise import fields

class Migration(migrations.Migration):
    initial = True

    operations = [
        ops.CreateModel(
            name='AdminEntry',
            fields=[
                ('id', fields.CharField(primary_key=True, unique=True, db_index=True, max_length=64)),
                ('namespace', fields.CharField(db_index=True, max_length=255)),
                ('key', fields.CharField(max_length=255)),
                ('value', fields.JSONField(encoder=JSON_DUMPS, decoder=loads)),
            ],
            options={'table': 'flaxon_admin_entries', 'app': 'flaxon_admin', 'unique_together': (('namespace', 'key'),), 'pk_attr': 'id', 'table_description': 'Admin entry implementation for the db subsystem.'},
            bases=['Model'],
        ),
        ops.CreateModel(
            name='AdminOperation',
            fields=[
                ('id', fields.CharField(primary_key=True, unique=True, db_index=True, max_length=64)),
                ('kind', fields.CharField(max_length=128)),
                ('payload', fields.JSONField(encoder=JSON_DUMPS, decoder=loads)),
                ('created_at', fields.FloatField(db_index=True)),
            ],
            options={'table': 'flaxon_admin_operation_records', 'app': 'flaxon_admin', 'pk_attr': 'id', 'table_description': 'Admin operation implementation for the db subsystem.'},
            bases=['Model'],
        ),
    ]
