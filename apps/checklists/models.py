from django.db import models


class TipoOS(models.TextChoices):
    VISTORIA = "VISTORIA", "Vistoria Técnica"
    INSTALACAO = "INSTALACAO", "Instalação Fotovoltaica"


class ChecklistTemplate(models.Model):
    tipo = models.CharField("Tipo de OS", max_length=12, choices=TipoOS.choices, unique=True)
    nome = models.CharField("Nome do template", max_length=150)

    class Meta:
        verbose_name = "Template de checklist"
        verbose_name_plural = "Templates de checklist"

    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()})"


class TipoCampo(models.TextChoices):
    CAIXA_SELECAO = "CAIXA_SELECAO", "Caixa de seleção (sim/não)"
    TEXTO = "TEXTO", "Texto"
    FOTO = "FOTO", "Foto"


class ChecklistItem(models.Model):
    template = models.ForeignKey(ChecklistTemplate, on_delete=models.CASCADE, related_name="itens")
    ordem = models.PositiveIntegerField("Ordem", default=0)
    descricao = models.CharField("Pergunta / descrição do item", max_length=255)
    tipo_campo = models.CharField(
        "Tipo de campo", max_length=15, choices=TipoCampo.choices, default=TipoCampo.CAIXA_SELECAO
    )
    obrigatorio = models.BooleanField("Obrigatório para dar baixa", default=False)

    class Meta:
        verbose_name = "Item de checklist"
        verbose_name_plural = "Itens de checklist"
        ordering = ["template", "ordem"]

    def __str__(self):
        return self.descricao
