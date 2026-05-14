from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import AuditModel


# Create your models here.

class Supply(AuditModel):
    """El modelo hace referiencia a un insumo odontológico"""
    name = models.CharField(_('Name'), max_length=255)
    code = models.CharField(_('Code'), max_length=50)
    description = models.CharField(_('Description'), max_length=255)
    image_url = models.ImageField(_('Image url'), upload_to='imagen/')
    stock_min = models.PositiveIntegerField(_('Stock min'), default=10)

    class Meta:
        db_table = 'supply'
        verbose_name = _('Supply')
        verbose_name_plural = _('Supplies')
        ordering = ('name','-created_at')
    def __str__(self):
        return self.name

class Batch(AuditModel):
    """El modelo hace referiencia a un lote """
    class Status(models.IntegerChoices):
        DISCARDED = 0,_('Discarded')
        ACTIVE= 1,_('Active')
        EXPIRED=2,_('Expired')
    suppy = models.ForeignKey(Supply, verbose_name=_('Supply'), on_delete=models.PROTECT, related_name='batches')
    number = models.CharField(_('Number'), max_length=100)
    expiration_date = models.DateField(_('Expiration date'))
    stock = models.PositiveIntegerField(_('Stock'), default= 0, validators=[MinValueValidator(0)]) #stock actual
    purchase_unit_cost =models.DecimalField(_('Purchase unit cost'), max_digits=10, decimal_places=2)
    status = models.PositiveIntegerField(_('Status'), choices=Status.choices, default=Status.ACTIVE)
    purchase_order =models.ForeignKey('purchasing.PurchaseOrder', verbose_name=_('Purchase order'), on_delete=models.SET_NULL, blank=True, null=True)


    class Meta:
        db_table = 'batch'
        verbose_name = _('Batch')
        verbose_name_plural = _('Batches')
        ordering = ('number','-expiration_date',)
        unique_together = (('suppy','number'),)

    def __str__(self):
        return f'{self.suppy.name} - {self.number}'
    @property
    def is_expired(self):
        return self.expiration_date < timezone.now().date()

class InventoryMovement(AuditModel):
    """El modelo hace referiencia a los movimientos """
    class Type(models.IntegerChoices):
        INBOUND = 0, _('Inbound')
        OUTBOUND = 1, _('Outbound')
        ADJUSTMENT = 2, _('Adjustment')
    batch = models.ForeignKey(Batch, verbose_name=_('Batch'), on_delete=models.PROTECT, related_name='movements')
    movement_type = models.PositiveSmallIntegerField(_('Type'), choices=Type.choices)
    concept = models.CharField(_('Concept'), max_length=255)
    quantity = models.PositiveIntegerField(_('Quantity'), validators=[MinValueValidator(0)])
    observation = models.CharField(_('Observation'), max_length=255)
    previus_stock = models.PositiveIntegerField(_('Previus stock'), validators=[MinValueValidator(0)])
    after_stock = models.PositiveIntegerField(_('After stock'), validators=[MinValueValidator(0)])
    is_increment =models.BooleanField(_('Increment'), blank=True, null=True)



    class Meta:
        db_table = 'inventory_movement'
        verbose_name = _('Inventory Movement')
        verbose_name_plural = _('Inventory Movements')
        ordering = ('movement_type','description',)
    def __str__(self):
        return self.type

    from django.db import transaction

    @transaction.atomic
    def save(self, *args, **kwargs):
        """
        Updates batch stock and maintains traceability by calling parent logic.
        """
        if not self.pk:  # Solo para nuevos movimientos
            # 1. Lógica de Inventario
            self.previous_stock = self.batch.stock
            if self.movement_type == self.movement_type.INBOUND:
                self.batch.stock += self.quantity
            elif self.movement_type == self.movement_type.OUTBOUND:
                self.batch.stock -= self.quantity
            elif self.movement_type == self.movement_type.ADJUSTMENT:
                if getattr(self, 'is_increment', False):
                    self.batch.stock += self.quantity
                else:
                    self.batch.stock -= self.quantity

            self.after_stock = self.batch.stock

            self.batch.save()


        super().save(*args, **kwargs)




