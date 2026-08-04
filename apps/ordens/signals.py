from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.checklists.models import ChecklistItem
from apps.relatorios.pdf import gerar_pdf_os

from .models import OrdemServico, OsChecklistResposta, StatusOS


def _regenerar_se_concluida(ordem_servico):
    if ordem_servico.status == StatusOS.CONCLUIDA:
        gerar_pdf_os(ordem_servico)


@receiver(post_save, sender=OsChecklistResposta)
@receiver(post_delete, sender=OsChecklistResposta)
def resposta_checklist_alterada(sender, instance, **kwargs):
    _regenerar_se_concluida(instance.os)


@receiver(post_save, sender=ChecklistItem)
@receiver(post_delete, sender=ChecklistItem)
def item_checklist_alterado(sender, instance, **kwargs):
    ordens_afetadas = OrdemServico.objects.filter(tipo=instance.template.tipo, status=StatusOS.CONCLUIDA)
    for ordem_servico in ordens_afetadas:
        gerar_pdf_os(ordem_servico)
