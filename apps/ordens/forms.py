from django import forms

from .models import OrdemServico, OsFoto


class OsNarrativaForm(forms.ModelForm):
    class Meta:
        model = OrdemServico
        fields = [
            "status_pill_text",
            "cover_footnote",
            "narrativa_paragrafos",
            "resumo_tecnico_bullets",
            "observacoes",
        ]
        widgets = {
            "status_pill_text": forms.TextInput(attrs={"placeholder": "Ex.: INSTALAÇÃO FINALIZADA"}),
            "cover_footnote": forms.TextInput(attrs={"placeholder": "Resumo curto do resultado"}),
            "narrativa_paragrafos": forms.Textarea(attrs={"rows": 6}),
            "resumo_tecnico_bullets": forms.Textarea(attrs={"rows": 5}),
            "observacoes": forms.Textarea(attrs={"rows": 3}),
        }


class OsFotoForm(forms.ModelForm):
    class Meta:
        model = OsFoto
        fields = ["titulo_secao", "legenda", "imagem", "ordem"]
        widgets = {
            "titulo_secao": forms.TextInput(attrs={"placeholder": "Ex.: Disjuntor de Proteção CC"}),
            "legenda": forms.Textarea(attrs={"rows": 2, "placeholder": "Legenda técnica da foto"}),
            "imagem": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }
