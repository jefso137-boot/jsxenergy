from django import forms

from apps.contas.models import Usuario

from .models import OrdemServico


class OsCriarForm(forms.ModelForm):
    class Meta:
        model = OrdemServico
        fields = ["cliente", "tipo", "tecnico", "data_agendada", "observacoes"]
        widgets = {
            "data_agendada": forms.DateInput(attrs={"type": "date"}),
            "observacoes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tecnico"].queryset = Usuario.objects.filter(role=Usuario.Papel.TECNICO)


class OsNarrativaForm(forms.ModelForm):
    class Meta:
        model = OrdemServico
        fields = [
            "narrativa_paragrafos",
            "status_pill_text",
        ]
        labels = {
            "narrativa_paragrafos": "Relatório técnico",
            "status_pill_text": "Status",
        }
        widgets = {
            "narrativa_paragrafos": forms.Textarea(
                attrs={"rows": 8, "placeholder": "Descreva o que foi feito/encontrado e a situação final"}
            ),
            "status_pill_text": forms.TextInput(attrs={"placeholder": "Ex.: INSTALAÇÃO FINALIZADA"}),
        }
