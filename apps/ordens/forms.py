from django import forms

from apps.clientes.models import Cliente
from apps.contas.models import Usuario

from .models import OrdemServico


class OsCriarForm(forms.ModelForm):
    class Meta:
        model = OrdemServico
        fields = ["cliente", "tipo", "tecnico", "data_agendada", "observacoes", "documento_pdf_1", "documento_pdf_2"]
        labels = {
            "documento_pdf_1": "Projeto (PDF)",
            "documento_pdf_2": "Vistoria (PDF)",
        }
        widgets = {
            "data_agendada": forms.DateInput(attrs={"type": "date"}),
            "observacoes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tecnico"].queryset = Usuario.objects.filter(role=Usuario.Papel.TECNICO)
        if user is not None:
            self.fields["cliente"].queryset = Cliente.objects.filter(criado_por=user)


class OsNarrativaForm(forms.ModelForm):
    class Meta:
        model = OrdemServico
        fields = [
            "narrativa_paragrafos",
            "status_pill_text",
            "descricao_recibo",
        ]
        labels = {
            "narrativa_paragrafos": "Relatório técnico",
            "status_pill_text": "Status",
            "descricao_recibo": "Descrição do serviço (aparece no recibo)",
        }
        widgets = {
            "narrativa_paragrafos": forms.Textarea(
                attrs={"rows": 8, "placeholder": "Descreva o que foi feito/encontrado e a situação final"}
            ),
            "descricao_recibo": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Ex.: Serviço de instalação de sistema fotovoltaico conectado à rede com fornecimento de material",
                }
            ),
        }
