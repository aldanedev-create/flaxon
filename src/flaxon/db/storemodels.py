"""Admin metadata tables managed through explicit Tortoise migrations."""

from tortoise import fields
from tortoise.models import Model


class AdminEntry(Model):
    """Admin entry implementation for the db subsystem."""

    id = fields.CharField(max_length=64, primary_key=True)
    namespace = fields.CharField(max_length=255, db_index=True)
    key = fields.CharField(max_length=255)
    value = fields.JSONField()

    class Meta:
        """Meta implementation for the db subsystem."""

        table = "flaxon_admin_entries"
        unique_together = (("namespace", "key"),)


class AdminOperation(Model):
    """Admin operation implementation for the db subsystem."""

    id = fields.CharField(max_length=64, primary_key=True)
    kind = fields.CharField(max_length=128)
    payload = fields.JSONField()
    created_at = fields.FloatField(db_index=True)

    class Meta:
        """Meta implementation for the db subsystem."""

        table = "flaxon_admin_operation_records"
