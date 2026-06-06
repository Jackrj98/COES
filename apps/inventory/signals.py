from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Batch


@receiver(post_save, sender=Batch)
def update_batch_status_on_depletion(sender, instance, **kwargs):
    if instance.current_quantity == 0 and instance.status != Batch.BatchStatus.DEPLETED:
        Batch.objects.filter(pk=instance.pk).update(status=Batch.BatchStatus.DEPLETED)
