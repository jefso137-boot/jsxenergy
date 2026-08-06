from django.db import models

from apps.checklists.models import TipoCampo


class ConfiguracaoPreco(models.Model):
    valor_placa = models.DecimalField(
        "Valor da instalação por placa", max_digits=10, decimal_places=2, default=0
    )
    valor_padrao = models.DecimalField(
        "Valor da instalação do padrão", max_digits=10, decimal_places=2, default=0
    )
    valor_vistoria = models.DecimalField(
        "Valor da vistoria técnica", max_digits=10, decimal_places=2, default=100
    )
    atualizado_em = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        verbose_name = "Configuração de preços"
        verbose_name_plural = "Configuração de preços"

    def __str__(self):
        return "Preços padrão da JSX Energy"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)


class MaterialCatalogo(models.Model):
    nome = models.CharField("Produto", max_length=150)
    valor = models.DecimalField("Valor unitário", max_digits=10, decimal_places=2, default=0)
    ativo = models.BooleanField("Ativo", default=True)
    criado_em = models.DateTimeField("Criado em", auto_now_add=True)

    class Meta:
        verbose_name = "Material do catálogo"
        verbose_name_plural = "Catálogo de materiais"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class CustoExtraCatalogo(models.Model):
    nome = models.CharField("Serviço / custo extra", max_length=150)
    valor = models.DecimalField("Valor", max_digits=10, decimal_places=2, default=0)
    tipo_campo = models.CharField(
        "Como o técnico vai registrar",
        max_length=15,
        choices=TipoCampo.choices,
        default=TipoCampo.FOTO,
    )
    ativo = models.BooleanField("Ativo", default=True)
    criado_em = models.DateTimeField("Criado em", auto_now_add=True)

    class Meta:
        verbose_name = "Custo extra do catálogo"
        verbose_name_plural = "Catálogo de custos extras"
        ordering = ["nome"]

    def __str__(self):
        return self.nome
