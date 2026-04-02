"""Base models for multi-tenant isolation and common fields."""
import uuid
from django.db import models
from django.conf import settings


class TimeStampedModel(models.Model):
    """Abstract model with created/updated timestamps."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TenantModel(TimeStampedModel):
    """Abstract model that enforces multi-tenant isolation via empresa FK."""
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='%(class)s_set',
        db_index=True,
    )

    class Meta:
        abstract = True


class TenantManager(models.Manager):
    """Manager that filters by empresa automatically."""

    def for_empresa(self, empresa):
        return self.get_queryset().filter(empresa=empresa)
