from tortoise import migrations
from tortoise.migrations import operations as ops
from orjson import loads
from tortoise.fields.base import OnDelete
from tortoise.fields.data import JSON_DUMPS
from tortoise import fields
from tortoise.indexes import Index

class Migration(migrations.Migration):
    initial = True

    operations = [
        ops.CreateModel(
            name='User',
            fields=[
                ('id', fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),
                ('username', fields.CharField(unique=True, max_length=40)),
                ('email', fields.CharField(unique=True, max_length=255)),
                ('display_name', fields.CharField(default='', max_length=80)),
                ('password_hash', fields.CharField(null=True, max_length=255)),
                ('avatar_color', fields.CharField(default='#5865f2', max_length=7)),
                ('is_active', fields.BooleanField(default=True)),
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
            ],
            options={'table': 'dc_users', 'app': 'models', 'pk_attr': 'id'},
            bases=['Model'],
        ),
        ops.CreateModel(
            name='Bot',
            fields=[
                ('id', fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),
                ('owner', fields.ForeignKeyField('models.User', source_field='owner_id', db_constraint=True, to_field='id', related_name='bots', on_delete=OnDelete.CASCADE)),
                ('name', fields.CharField(max_length=80)),
                ('description', fields.CharField(default='', max_length=300)),
                ('is_enabled', fields.BooleanField(default=True)),
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
            ],
            options={'table': 'dc_bots', 'app': 'models', 'pk_attr': 'id'},
            bases=['Model'],
        ),
        ops.CreateModel(
            name='BotToken',
            fields=[
                ('id', fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),
                ('bot', fields.ForeignKeyField('models.Bot', source_field='bot_id', db_constraint=True, to_field='id', related_name='tokens', on_delete=OnDelete.CASCADE)),
                ('token_hash', fields.CharField(max_length=64)),
                ('token_prefix', fields.CharField(max_length=12)),
                ('label', fields.CharField(default='default', max_length=80)),
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
                ('revoked_at', fields.DatetimeField(null=True, auto_now=False, auto_now_add=False)),
                ('last_used_at', fields.DatetimeField(null=True, auto_now=False, auto_now_add=False)),
            ],
            options={'table': 'dc_bot_tokens', 'app': 'models', 'pk_attr': 'id', 'table_description': 'One-way stored bot credentials. The plaintext token is shown ONCE.'},
            bases=['Model'],
        ),
        ops.CreateModel(
            name='EventSubscription',
            fields=[
                ('id', fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),
                ('bot', fields.ForeignKeyField('models.Bot', source_field='bot_id', db_constraint=True, to_field='id', related_name='subscriptions', on_delete=OnDelete.CASCADE)),
                ('event_type', fields.CharField(max_length=60)),
                ('is_enabled', fields.BooleanField(default=True)),
            ],
            options={'table': 'dc_event_subscriptions', 'app': 'models', 'unique_together': (('bot_id', 'event_type'),), 'pk_attr': 'id'},
            bases=['Model'],
        ),
        ops.CreateModel(
            name='EventDelivery',
            fields=[
                ('id', fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),
                ('bot', fields.ForeignKeyField('models.Bot', source_field='bot_id', db_constraint=True, to_field='id', related_name='deliveries', on_delete=OnDelete.CASCADE)),
                ('subscription', fields.ForeignKeyField('models.EventSubscription', source_field='subscription_id', null=True, db_constraint=True, to_field='id', related_name='deliveries', on_delete=OnDelete.CASCADE)),
                ('event_type', fields.CharField(max_length=60)),
                ('idempotency_key', fields.CharField(db_index=True, max_length=64)),
                ('payload', fields.JSONField(default=dict, encoder=JSON_DUMPS, decoder=loads)),
                ('status', fields.CharField(default='pending', max_length=16)),
                ('attempt_count', fields.IntField(default=0)),
                ('last_error', fields.CharField(null=True, max_length=500)),
                ('delivered_at', fields.DatetimeField(null=True, auto_now=False, auto_now_add=False)),
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
            ],
            options={'table': 'dc_event_deliveries', 'app': 'models', 'pk_attr': 'id', 'table_description': 'One outbound event dispatch to a bot, with retry/backoff tracking.'},
            bases=['Model'],
        ),
        ops.CreateModel(
            name='Server',
            fields=[
                ('id', fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),
                ('name', fields.CharField(max_length=100)),
                ('owner', fields.ForeignKeyField('models.User', source_field='owner_id', db_constraint=True, to_field='id', related_name='owned_servers', on_delete=OnDelete.CASCADE)),
                ('invite_code', fields.CharField(unique=True, max_length=12)),
                ('icon_color', fields.CharField(default='#232428', max_length=7)),
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
            ],
            options={'table': 'dc_servers', 'app': 'models', 'pk_attr': 'id'},
            bases=['Model'],
        ),
        ops.CreateModel(
            name='Channel',
            fields=[
                ('id', fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),
                ('server', fields.ForeignKeyField('models.Server', source_field='server_id', db_constraint=True, to_field='id', related_name='channels', on_delete=OnDelete.CASCADE)),
                ('name', fields.CharField(max_length=100)),
                ('topic', fields.CharField(default='', max_length=300)),
                ('is_private', fields.BooleanField(default=False)),
                ('position', fields.IntField(default=0)),
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
            ],
            options={'table': 'dc_channels', 'app': 'models', 'indexes': [Index(fields=['server_id', 'position'])], 'pk_attr': 'id'},
            bases=['Model'],
        ),
        ops.CreateModel(
            name='ChannelAccess',
            fields=[
                ('id', fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),
                ('channel', fields.ForeignKeyField('models.Channel', source_field='channel_id', db_constraint=True, to_field='id', related_name='access_grants', on_delete=OnDelete.CASCADE)),
                ('user', fields.ForeignKeyField('models.User', source_field='user_id', db_constraint=True, to_field='id', related_name='channel_access', on_delete=OnDelete.CASCADE)),
                ('granted_by', fields.ForeignKeyField('models.User', source_field='granted_by_id', null=True, db_constraint=True, to_field='id', related_name='granted_access', on_delete=OnDelete.CASCADE)),
            ],
            options={'table': 'dc_channel_access', 'app': 'models', 'unique_together': (('channel_id', 'user_id'),), 'pk_attr': 'id', 'table_description': 'Explicit grant letting a member read a private channel.'},
            bases=['Model'],
        ),
        ops.CreateModel(
            name='Message',
            fields=[
                ('id', fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),
                ('channel', fields.ForeignKeyField('models.Channel', source_field='channel_id', db_constraint=True, to_field='id', related_name='messages', on_delete=OnDelete.CASCADE)),
                ('author', fields.ForeignKeyField('models.User', source_field='author_id', null=True, db_constraint=True, to_field='id', related_name='messages', on_delete=OnDelete.CASCADE)),
                ('author_bot', fields.ForeignKeyField('models.Bot', source_field='author_bot_id', null=True, db_constraint=True, to_field='id', related_name='messages', on_delete=OnDelete.CASCADE)),
                ('content', fields.TextField(unique=False)),
                ('type', fields.IntField(default=0)),
                ('edited_at', fields.DatetimeField(null=True, auto_now=False, auto_now_add=False)),
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
            ],
            options={'table': 'dc_messages', 'app': 'models', 'indexes': [Index(fields=['channel_id', 'created_at'])], 'pk_attr': 'id'},
            bases=['Model'],
        ),
        ops.CreateModel(
            name='Role',
            fields=[
                ('id', fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),
                ('server', fields.ForeignKeyField('models.Server', source_field='server_id', db_constraint=True, to_field='id', related_name='roles', on_delete=OnDelete.CASCADE)),
                ('name', fields.CharField(max_length=60)),
                ('permissions', fields.IntField(default=0)),
                ('color', fields.CharField(default='#99aab5', max_length=7)),
                ('position', fields.IntField(default=0)),
            ],
            options={'table': 'dc_roles', 'app': 'models', 'pk_attr': 'id'},
            bases=['Model'],
        ),
        ops.CreateModel(
            name='BotMembership',
            fields=[
                ('id', fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),
                ('server', fields.ForeignKeyField('models.Server', source_field='server_id', db_constraint=True, to_field='id', related_name='bot_members', on_delete=OnDelete.CASCADE)),
                ('bot', fields.ForeignKeyField('models.Bot', source_field='bot_id', db_constraint=True, to_field='id', related_name='server_memberships', on_delete=OnDelete.CASCADE)),
                ('role', fields.ForeignKeyField('models.Role', source_field='role_id', null=True, db_constraint=True, to_field='id', related_name='bot_members', on_delete=OnDelete.CASCADE)),
            ],
            options={'table': 'dc_bot_memberships', 'app': 'models', 'unique_together': (('server_id', 'bot_id'),), 'pk_attr': 'id', 'table_description': 'Grants a bot a role (and therefore scoped permissions) inside a server.'},
            bases=['Model'],
        ),
        ops.CreateModel(
            name='Membership',
            fields=[
                ('id', fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),
                ('server', fields.ForeignKeyField('models.Server', source_field='server_id', db_constraint=True, to_field='id', related_name='members', on_delete=OnDelete.CASCADE)),
                ('user', fields.ForeignKeyField('models.User', source_field='user_id', db_constraint=True, to_field='id', related_name='memberships', on_delete=OnDelete.CASCADE)),
                ('role', fields.ForeignKeyField('models.Role', source_field='role_id', null=True, db_constraint=True, to_field='id', related_name='members', on_delete=OnDelete.CASCADE)),
                ('nickname', fields.CharField(default='', max_length=80)),
                ('joined_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
            ],
            options={'table': 'dc_memberships', 'app': 'models', 'unique_together': (('server_id', 'user_id'),), 'pk_attr': 'id'},
            bases=['Model'],
        ),
        ops.CreateModel(
            name='SlashCommand',
            fields=[
                ('id', fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),
                ('bot', fields.ForeignKeyField('models.Bot', source_field='bot_id', db_constraint=True, to_field='id', related_name='commands', on_delete=OnDelete.CASCADE)),
                ('name', fields.CharField(max_length=32)),
                ('description', fields.CharField(default='', max_length=200)),
                ('parameters', fields.JSONField(default=list, encoder=JSON_DUMPS, decoder=loads)),
                ('is_enabled', fields.BooleanField(default=True)),
            ],
            options={'table': 'dc_commands', 'app': 'models', 'unique_together': (('bot_id', 'name'),), 'pk_attr': 'id'},
            bases=['Model'],
        ),
        ops.CreateModel(
            name='CommandInvocation',
            fields=[
                ('id', fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),
                ('bot', fields.ForeignKeyField('models.Bot', source_field='bot_id', db_constraint=True, to_field='id', related_name='invocations', on_delete=OnDelete.CASCADE)),
                ('command', fields.ForeignKeyField('models.SlashCommand', source_field='command_id', db_constraint=True, to_field='id', related_name='invocations', on_delete=OnDelete.CASCADE)),
                ('server_id', fields.IntField(null=True)),
                ('channel_id', fields.IntField(null=True)),
                ('user_id', fields.IntField(null=True)),
                ('status', fields.CharField(default='success', max_length=16)),
                ('result', fields.TextField(default='', unique=False)),
                ('error', fields.TextField(default='', unique=False)),
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
            ],
            options={'table': 'dc_command_invocations', 'app': 'models', 'pk_attr': 'id', 'table_description': 'Record of a slash command executed by a bot (result or error).'},
            bases=['Model'],
        ),
    ]
