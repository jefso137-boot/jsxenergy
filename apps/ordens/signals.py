import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.relatorios.pdf import gerar_pdf_os

from .models import OsChecklistResposta, StatusOS

logger = logging.getLogger(__name__)


@receiver(post_save, sender=OsChecklistResposta)
@receiver(post_delete, sender=OsChecklistResposta)
def resposta_checklist_alterada(sender, instance, **kwargs):
    """Regera o PDF quando a resposta de UMA OS já concluída muda (ex.: o admin
    corrige uma foto/observação enviada errada). Editar a configuração do
    checklist em si (ChecklistItem, incl. "obrigatório") não entra aqui de
    propósito: isso só deve valer para as OS pendentes/em aberto que ainda vão
    ser preenchidas, sem mexer no PDF das que já foram concluídas."""
    ordem_servico = instance.os
    if ordem_servico.status != StatusOS.CONCLUIDA:
        return
    try:
        gerar_pdf_os(ordem_servico)
    except Exception:
        logger.exception("Falha ao regerar PDF da OS #%s após alteração de checklist", ordem_servico.pk)
