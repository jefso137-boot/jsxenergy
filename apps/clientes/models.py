from django.conf import settings
from django.db import models


class Cliente(models.Model):
    nome = models.CharField("Nome", max_length=200)
    telefone = models.CharField("Telefone", max_length=30, blank=True)
    email = models.EmailField("E-mail", blank=True)
    endereco = models.CharField("Endereço", max_length=255, blank=True)
    cidade = models.CharField("Cidade", max_length=120, blank=True)
    link_localizacao = models.URLField("Link da localização", blank=True)
    quantidade_modulos = models.PositiveIntegerField("Quantidade de módulos", default=0)
    instalacao_padrao = models.BooleanField("Terá instalação de padrão", default=False)
    precisa_material_ca = models.BooleanField("Vai precisar de material C.A.", default=False)
    pago = models.BooleanField("Pago", default=False)
    data_pagamento = models.DateTimeField("Pago em", null=True, blank=True)
    data_referencia_medicao = models.DateField(
        "Data de referência da medição", null=True, blank=True,
        help_text="Usada só para decidir em qual semana de fechamento o cliente entra. "
        "Deixe em branco para usar a data de cadastro.",
    )
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="clientes_criados",
        null=True,
        blank=True,
        verbose_name="Criado por",
    )
    criado_em = models.DateTimeField("Criado em", auto_now_add=True)

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    def valor_estimado_instalacao(self):
        from apps.financas.models import ConfiguracaoPreco

        precos = ConfiguracaoPreco.get_solo()
        total = self.quantidade_modulos * precos.valor_placa
        if self.instalacao_padrao:
            total += precos.valor_padrao
        return total

    def valor_materiais_usados(self):
        from apps.ordens.models import OsMaterialUso

        usos = OsMaterialUso.objects.filter(os__cliente=self).select_related("material")
        return sum((uso.subtotal() for uso in usos), start=0)

    def valor_custos_extras_usados(self):
        from apps.ordens.models import OsCustoExtraUso

        usos = OsCustoExtraUso.objects.filter(os__cliente=self).select_related("custo")
        return sum((uso.subtotal() for uso in usos), start=0)

    def valor_total(self):
        return (
            self.valor_estimado_instalacao()
            + self.valor_materiais_usados()
            + self.valor_custos_extras_usados()
        )


class FechamentoMedicao(models.Model):
    """Controle de pagamento por semana de medição (quinta a quarta), por líder.
    Criado automaticamente quando a semana aparece na tela de Medição; o
    admin marca "pago" quando efetua o pagamento daquele fechamento."""

    lider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="fechamentos_medicao",
        verbose_name="Líder",
    )
    inicio = models.DateField("Início da semana")
    fim = models.DateField("Fim da semana")
    pago = models.BooleanField("Pago", default=False)
    data_pagamento = models.DateTimeField("Pago em", null=True, blank=True)

    class Meta:
        verbose_name = "Fechamento de medição"
        verbose_name_plural = "Fechamentos de medição"
        unique_together = ("lider", "inicio", "fim")
        ordering = ["-inicio"]

    def __str__(self):
        return f"{self.lider} — {self.inicio:%d/%m} a {self.fim:%d/%m}"
