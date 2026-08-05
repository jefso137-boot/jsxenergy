from django.conf import settings
from django.db import models

from apps.checklists.models import ChecklistItem, ChecklistTemplate, TipoOS
from apps.clientes.models import Cliente


class StatusOS(models.TextChoices):
    ABERTA = "ABERTA", "Aberta"
    EM_ANDAMENTO = "EM_ANDAMENTO", "Em andamento"
    CONCLUIDA = "CONCLUIDA", "Concluída"


class OrdemServico(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="ordens_servico")
    tipo = models.CharField("Tipo de OS", max_length=12, choices=TipoOS.choices)
    tecnico = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="ordens_atribuidas",
        limit_choices_to={"role": "tecnico"},
        verbose_name="Técnico responsável",
    )
    status = models.CharField("Status", max_length=15, choices=StatusOS.choices, default=StatusOS.ABERTA)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="ordens_criadas",
        null=True,
        blank=True,
        verbose_name="Criado por",
    )
    data_agendada = models.DateField("Data agendada")
    data_conclusao = models.DateTimeField("Data de conclusão", null=True, blank=True)
    observacoes = models.TextField("Observações internas", blank=True)

    # Campos usados na geração do PDF (spec "editable_fields_for_new_client")
    status_pill_text = models.CharField(
        "Selo de status (PDF)", max_length=60, blank=True,
        help_text="Ex.: INSTALAÇÃO FINALIZADA, VISTORIA APROVADA, APROVADO COM RESSALVAS",
    )
    cover_footnote = models.CharField(
        "Rodapé da capa (PDF)", max_length=200, blank=True,
        help_text="Frase curta em itálico resumindo o resultado",
    )
    narrativa_paragrafos = models.TextField(
        "Narrativa (PDF)", blank=True,
        help_text="2 a 3 parágrafos, separados por linha em branco",
    )
    resumo_tecnico_bullets = models.TextField(
        "Resumo técnico (PDF)", blank=True,
        help_text="Um item por linha. Se deixado em branco, é pré-preenchido com os itens do checklist marcados.",
    )
    pdf_file = models.FileField("PDF gerado", upload_to="relatorios_os/", null=True, blank=True)

    criado_em = models.DateTimeField("Criado em", auto_now_add=True)

    class Meta:
        verbose_name = "Ordem de Serviço"
        verbose_name_plural = "Ordens de Serviço"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"OS #{self.pk} - {self.cliente.nome} ({self.get_tipo_display()})"

    def get_checklist_template(self):
        return ChecklistTemplate.objects.filter(tipo=self.tipo).prefetch_related("itens").first()

    @property
    def titulo_pdf(self):
        return {
            TipoOS.INSTALACAO: "RELATÓRIO FOTOGRÁFICO DE INSTALAÇÃO FOTOVOLTAICA",
            TipoOS.VISTORIA: "RELATÓRIO FOTOGRÁFICO DE VISTORIA TÉCNICA",
        }[self.tipo]

    @property
    def status_page_titulo_pdf(self):
        return {
            TipoOS.INSTALACAO: "Status da Instalação",
            TipoOS.VISTORIA: "Status da Vistoria",
        }[self.tipo]

    @property
    def photo_header_line1_pdf(self):
        return {
            TipoOS.INSTALACAO: "Relatório Fotográfico de Instalação",
            TipoOS.VISTORIA: "Relatório Fotográfico de Vistoria",
        }[self.tipo]


class OsChecklistResposta(models.Model):
    os = models.ForeignKey(OrdemServico, on_delete=models.CASCADE, related_name="respostas_checklist")
    item = models.ForeignKey(ChecklistItem, on_delete=models.CASCADE, related_name="respostas")
    marcado = models.BooleanField("Marcado", default=False)
    texto = models.TextField("Resposta em texto", blank=True)
    foto = models.ImageField("Foto da resposta", upload_to="checklist_fotos/", null=True, blank=True)
    observacao = models.CharField("Observação", max_length=255, blank=True)

    class Meta:
        verbose_name = "Resposta de checklist"
        verbose_name_plural = "Respostas de checklist"
        unique_together = ("os", "item")
        ordering = ["item__ordem"]

    def respondido(self):
        tipo = self.item.tipo_campo
        if tipo == "TEXTO":
            return bool(self.texto.strip())
        if tipo == "FOTO":
            return bool(self.foto)
        return self.marcado

    def __str__(self):
        return f"{self.item.descricao} - {'OK' if self.respondido() else 'pendente'}"


class OsFoto(models.Model):
    os = models.ForeignKey(OrdemServico, on_delete=models.CASCADE, related_name="fotos")
    imagem = models.ImageField("Foto", upload_to="ordens_fotos/")
    titulo_secao = models.CharField("Título da seção", max_length=150)
    legenda = models.TextField("Legenda técnica", blank=True)
    ordem = models.PositiveIntegerField("Ordem", default=0)
    criado_em = models.DateTimeField("Enviada em", auto_now_add=True)

    class Meta:
        verbose_name = "Foto da OS"
        verbose_name_plural = "Fotos da OS"
        ordering = ["ordem", "criado_em"]

    def __str__(self):
        return f"{self.titulo_secao} (OS #{self.os_id})"


class OsMaterialUso(models.Model):
    os = models.ForeignKey(OrdemServico, on_delete=models.CASCADE, related_name="materiais_usados")
    material = models.ForeignKey(
        "financas.MaterialCatalogo", on_delete=models.PROTECT, related_name="usos"
    )
    quantidade = models.PositiveIntegerField("Quantidade", default=1)
    criado_em = models.DateTimeField("Registrado em", auto_now_add=True)

    class Meta:
        verbose_name = "Material usado na OS"
        verbose_name_plural = "Materiais usados na OS"

    def subtotal(self):
        return self.quantidade * self.material.valor

    def __str__(self):
        return f"{self.quantidade}x {self.material.nome} (OS #{self.os_id})"
