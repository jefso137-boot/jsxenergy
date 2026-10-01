import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Cliente

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Cliente)
def cliente_atualizado(sender, instance, created, **kwargs):
    """Regera o PDF das OS já concluídas desse cliente quando os dados dele
    mudam (ex.: corrigir o nome, endereço, etc.) - sem isso, o PDF ficava
    com a informação antiga mesmo depois do cadastro do cliente ser
    corrigido."""
    if created:
        return

    from apps.ordens.models import OrdemServico, StatusOS
    from apps.relatorios.pdf import gerar_pdf_os

    ordens = OrdemServico.objects.filter(cliente=instance, status=StatusOS.CONCLUIDA)
    for ordem_servico in ordens:
        try:
            gerar_pdf_os(ordem_servico)
        except Exception:
            logger.exception(
                "Falha ao regerar PDF da OS #%s após atualização do cliente #%s",
                ordem_servico.pk, instance.pk,
            )
