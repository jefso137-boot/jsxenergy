from django.db import models

from apps.checklists.models import TipoCampo, TipoOS


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


class AplicavelEm(models.TextChoices):
    INSTALACAO = "INSTALACAO", "Somente instalação"
    VISTORIA = "VISTORIA", "Somente vistoria"
    AMBOS = "AMBOS", "Instalação e vistoria"
    MANUTENCAO = "MANUTENCAO", "Somente manutenção"


class CustoExtraCatalogo(models.Model):
    nome = models.CharField("Serviço / custo extra", max_length=150)
    valor = models.DecimalField("Valor", max_digits=10, decimal_places=2, default=0)
    area_por_placa = models.DecimalField(
        "Área por placa (m²)", max_digits=6, decimal_places=3, null=True, blank=True,
        help_text=(
            "Preencha só se esse custo for cobrado por metro quadrado (ex.: impermeabilização). "
            "Quando preenchido, o valor \"por unidade\" acima passa a ser o valor por m², e a "
            "quantidade informada na baixa/calculadora vira quantidade de placas: "
            "valor = quantidade de placas × área por placa × valor por m². "
            "Deixe em branco pra custos cobrados por unidade simples."
        ),
    )
    tipo_campo = models.CharField(
        "Como o técnico vai registrar",
        max_length=15,
        choices=TipoCampo.choices,
        default=TipoCampo.FOTO,
    )
    aplicavel_em = models.CharField(
        "Aplicável em",
        max_length=12,
        choices=AplicavelEm.choices,
        default=AplicavelEm.INSTALACAO,
        help_text="Em qual tipo de OS o técnico pode lançar esse custo extra.",
    )
    valor_definido_pelo_tecnico = models.BooleanField(
        "Técnico informa o valor na hora", default=False,
        help_text="Marque quando o preço varia de serviço pra serviço (ex.: reforma de telhado) - "
        "em vez do valor fixo do catálogo, o técnico digita o valor dessa vez específica ao "
        "registrar o custo extra.",
    )
    ativo = models.BooleanField("Ativo", default=True)
    criado_em = models.DateTimeField("Criado em", auto_now_add=True)

    class Meta:
        verbose_name = "Custo extra do catálogo"
        verbose_name_plural = "Catálogo de custos extras"
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    def aplica_a(self, tipo_os):
        if self.aplicavel_em == AplicavelEm.AMBOS:
            # "Instalação e vistoria" nunca inclui manutenção - é um terceiro
            # tipo de OS com catálogo próprio (aplicavel_em=MANUTENCAO).
            return tipo_os in (TipoOS.INSTALACAO, TipoOS.VISTORIA)
        return self.aplicavel_em == tipo_os

    @classmethod
    def filtro_aplicavel_em(cls, tipo_os):
        """Mesma regra de aplica_a(), em forma de Q pra filtrar no banco."""
        from django.db.models import Q

        if tipo_os in (TipoOS.INSTALACAO, TipoOS.VISTORIA):
            return Q(aplicavel_em=AplicavelEm.AMBOS) | Q(aplicavel_em=tipo_os)
        return Q(aplicavel_em=tipo_os)


class ServicoCatalogo(models.Model):
    """Serviço escolhido na criação da OS (hoje só pra manutenção, que não
    tem valor automático fixo/por módulo como vistoria/instalação) - define
    o valor cobrado automaticamente ao dar baixa. O administrativo ainda
    pode sobrescrever esse valor só numa OS específica (ver
    OrdemServico.valor_servico_manual)."""

    nome = models.CharField("Serviço", max_length=150)
    valor = models.DecimalField("Valor", max_digits=10, decimal_places=2, default=0)
    aplicavel_em = models.CharField(
        "Tipo de OS", max_length=12, choices=TipoOS.choices, default=TipoOS.MANUTENCAO,
        help_text="Em qual tipo de OS esse serviço pode ser escolhido na criação.",
    )
    ativo = models.BooleanField("Ativo", default=True)
    criado_em = models.DateTimeField("Criado em", auto_now_add=True)

    class Meta:
        verbose_name = "Serviço do catálogo"
        verbose_name_plural = "Catálogo de serviços"
        ordering = ["nome"]

    def __str__(self):
        return self.nome
