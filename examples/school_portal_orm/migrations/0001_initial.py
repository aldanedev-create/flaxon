from tortoise import migrations
from tortoise.migrations import operations as ops
from tortoise import fields

class Migration(migrations.Migration):
    initial = True

    operations = [
        ops.CreateModel(
            name='Course',
            fields=[
                ('id', fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),
                ('code', fields.CharField(unique=True, max_length=20)),
                ('name', fields.CharField(max_length=120)),
                ('teacher', fields.CharField(max_length=120)),
                ('room', fields.CharField(max_length=20)),
            ],
            options={'table': 'school_courses', 'app': 'models', 'pk_attr': 'id'},
            bases=['Model'],
        ),
        ops.CreateModel(
            name='Staff',
            fields=[
                ('id', fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),
                ('name', fields.CharField(max_length=120)),
                ('role', fields.CharField(max_length=80)),
                ('email', fields.CharField(max_length=255)),
            ],
            options={'table': 'school_staff', 'app': 'models', 'pk_attr': 'id'},
            bases=['Model'],
        ),
        ops.CreateModel(
            name='Student',
            fields=[
                ('id', fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),
                ('name', fields.CharField(max_length=120)),
                ('grade', fields.CharField(max_length=10)),
                ('email', fields.CharField(max_length=255)),
                ('active', fields.BooleanField(default=True)),
            ],
            options={'table': 'school_students', 'app': 'models', 'pk_attr': 'id'},
            bases=['Model'],
        ),
    ]
