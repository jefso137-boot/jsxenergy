import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.checklists.models import ChecklistItem
from apps.relatorios.pdf import gerar_pdf_os

from .models import OrdemServico, OsChecklistResposta, StatusOS

logger = logging.getLogger(__name__)


def _regenerar_se_concluida(ordem_servico):
    if ordem_servico.status != StatusOS.CONCLUIDA:
        return
    try:
        gerar_pdf_os(ordem_servico)
    except Exception:
        # Nunca deixa uma falha ao regerar o PDF de UMA OS derrubar a operação que
        # disparou o sinal (ex.: salvar um ChecklistItem no admin) com um 500 - isso
        # já aconteceu ao desmarcar "obrigatório" num item de foto: o admin tentava
        # regerar o PDF de toda OS concluída daquele tipo e uma falha em qualquer
        # uma delas quebrava o salvamento inteiro.
        logger.exception("Falha ao regerar PDF da OS #%s após alteração de checklist", ordem_servico.pk)


@receiver(post_save, sender=OsChecklistResposta)
@receiver(post_delete, sender=OsChecklistResposta)
def resposta_checklist_alterada(sender, instance, **kwargs):
    _regenerar_se_concluida(instance.os)


@receiver(post_save, sender=ChecklistItem)
@receiver(post_delete, sender=ChecklistItem)
def item_checklist_alterado(sender, instance, **kwargs):
    ordens_afetadas = OrdemServico.objects.filter(tipo=instance.template.tipo, status=StatusOS.CONCLUIDA)
    for ordem_servico in ordens_afetadas:
        _regenerar_se_concluida(ordem_servico)
