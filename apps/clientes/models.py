from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone


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
    Criado automaticamente quando a semana aparece na tela de Medição. O admin
    sobe o comprovante e digita o valor pago; o sistema compara com o valor
    esperado e marca como pago automaticamente quando bate (ou passa), senão
    mostra o valor pendente - ver save(). Se ficar pago parcialmente e
    `repassar_pendente` estiver ligado, o valor que falta entra automaticamente
    no valor esperado da semana seguinte desse líder - ver
    apps/clientes/views_lider.py:medicao()."""

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
    valor_esperado = models.DecimalField(
        "Valor esperado", max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Calculado automaticamente pela tela de Medição do líder (já inclui o valor "
        "repassado da semana anterior, se houver). Só é atualizado enquanto o fechamento ainda "
        "não foi marcado como pago.",
    )
    valor_repasse_recebido = models.DecimalField(
        "Valor repassado da semana anterior", max_digits=10, decimal_places=2, default=0, blank=True,
        help_text="Preenchido automaticamente quando a semana anterior desse líder ficou paga "
        "parcialmente e o repasse pra próxima semana está ligado. Já está somado no valor esperado.",
    )
    repassar_pendente = models.BooleanField(
        "Repassar valor pendente pra próxima semana", default=True,
        help_text="Se ficar pago parcialmente, o valor que faltar entra automaticamente no valor "
        "esperado da semana seguinte. Desligue se for resolver essa diferença de outra forma.",
    )
    valor_pendente_ajustado = models.DecimalField(
        "Valor pendente (ajuste manual)", max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Preencha só para sobrescrever o valor pendente calculado automaticamente "
        "(esperado − pago) - por exemplo, pra perdoar parte da diferença. É esse valor (quando "
        "preenchido) que é repassado pra próxima semana.",
    )
    valor_pago = models.DecimalField(
        "Valor pago", max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Preencha com o valor que realmente foi transferido ao líder nesse fechamento. "
        "Ao salvar, o sistema marca automaticamente como pago se o valor bater (ou passar) o "
        "esperado, e mostra o valor pendente caso contrário.",
    )
    comprovante_pagamento = models.FileField(
        "Comprovante de pagamento (foto ou PDF)", upload_to="comprovantes_pagamento/", null=True, blank=True,
        validators=[FileExtensionValidator(allowed_extensions=["pdf", "jpg", "jpeg", "png", "heic"])],
    )
    observacao_divergencia = models.TextField(
        "Observação sobre divergência", blank=True,
        help_text="Anote aqui o que foi apurado quando o valor pago não bater com o esperado "
        "(ex.: OS que entrou na semana errada, pagamento duplicado, etc.).",
    )

    class Meta:
        verbose_name = "Fechamento de medição"
        verbose_name_plural = "Fechamentos de medição"
        unique_together = ("lider", "inicio", "fim")
        ordering = ["-inicio"]

    def __str__(self):
        return f"{self.lider} — {self.inicio:%d/%m} a {self.fim:%d/%m}"

    def save(self, *args, **kwargs):
        # Uma vez que o valor pago é informado, ele passa a mandar no status -
        # bateu (ou passou) o esperado marca como pago automaticamente; senão
        # fica pendente, mesmo que alguém tenha marcado "pago" manualmente antes.
        if self.valor_pago is not None and self.valor_esperado is not None:
            self.pago = self.valor_pago >= self.valor_esperado
            if self.pago and not self.data_pagamento:
                self.data_pagamento = timezone.now()
            elif not self.pago:
                self.data_pagamento = None
        super().save(*args, **kwargs)

    @property
    def diferenca(self):
        if self.valor_pago is None or self.valor_esperado is None:
            return None
        return self.valor_pago - self.valor_esperado

    @property
    def tem_divergencia(self):
        diferenca = self.diferenca
        return diferenca is not None and diferenca != 0

    @property
    def valor_pendente(self):
        if self.valor_pago is None or self.valor_esperado is None:
            return None
        pendente = self.valor_esperado - self.valor_pago
        return pendente if pendente > 0 else 0

    @property
    def valor_pendente_efetivo(self):
        """Valor pendente considerando o ajuste manual do admin, quando houver -
        é esse valor que a tela de Medição repassa pra próxima semana."""
        if self.valor_pendente_ajustado is not None:
            return self.valor_pendente_ajustado
        return self.valor_pendente
