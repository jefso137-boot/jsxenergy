from django import forms

from .models import OrdemServico


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
