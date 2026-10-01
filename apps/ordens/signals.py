import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.relatorios.pdf import gerar_pdf_os

from .models import OsChecklistResposta, OsCustoExtraFoto, OsCustoExtraUso, StatusOS

logger = logging.getLogger(__name__)


def _regerar_pdf_se_concluida(ordem_servico, motivo):
    if ordem_servico.status != StatusOS.CONCLUIDA:
        return
    try:
        gerar_pdf_os(ordem_servico)
    except Exception:
        logger.exception("Falha ao regerar PDF da OS #%s após %s", ordem_servico.pk, motivo)


@receiver(post_save, sender=OsChecklistResposta)
@receiver(post_delete, sender=OsChecklistResposta)
def resposta_checklist_alterada(sender, instance, **kwargs):
    """Regera o PDF quando a resposta de UMA OS já concluída muda (ex.: o admin
    corrige uma foto/observação enviada errada). Editar a configuração do
    checklist em si (ChecklistItem, incl. "obrigatório") não entra aqui de
    propósito: isso só deve valer para as OS pendentes/em aberto que ainda vão
    ser preenchidas, sem mexer no PDF das que já foram concluídas."""
    _regerar_pdf_se_concluida(instance.os, "alteração de checklist")


@receiver(post_save, sender=OsCustoExtraUso)
@receiver(post_delete, sender=OsCustoExtraUso)
def custo_extra_alterado(sender, instance, **kwargs):
    """Mesma lógica do checklist, mas pros custos extras - cobre o admin
    excluindo um item lançado errado ou ajustando o valor_manual numa OS que
    já tinha sido concluída (o técnico já regenera pela view, isso aqui cobre
    as edições feitas direto no /admin)."""
    _regerar_pdf_se_concluida(instance.os, "alteração de custo extra")


@receiver(post_save, sender=OsCustoExtraFoto)
@receiver(post_delete, sender=OsCustoExtraFoto)
def foto_custo_extra_alterada(sender, instance, **kwargs):
    _regerar_pdf_se_concluida(instance.uso.os, "alteração de foto de custo extra")
