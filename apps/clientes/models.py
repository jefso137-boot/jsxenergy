from django.conf import settings
from django.db import models


class Cliente(models.Model):
    nome = models.CharField("Nome", max_length=200)
    telefone = models.CharField("Telefone", max_length=30, blank=True)
    email = models.EmailField("E-mail", blank=True)
    endereco = models.CharField("Endereço", max_length=255, blank=True)
    cidade = models.CharField("Cidade", max_length=120, blank=True)
    quantidade_modulos = models.PositiveIntegerField("Quantidade de módulos", default=0)
    instalacao_padrao = models.BooleanField("Terá instalação de padrão", default=False)
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

    def valor_total(self):
        return self.valor_estimado_instalacao() + self.valor_materiais_usados()
