from django import forms

from apps.clientes.models import Cliente
from apps.contas.models import Usuario
from apps.financas.models import MaterialCatalogo

from .models import OrdemServico, OsMaterialUso


class OsCriarForm(forms.ModelForm):
    class Meta:
        model = OrdemServico
        fields = ["cliente", "tipo", "tecnico", "data_agendada", "observacoes"]
        widgets = {
            "data_agendada": forms.DateInput(attrs={"type": "date"}),
            "observacoes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tecnico"].queryset = Usuario.objects.filter(role=Usuario.Papel.TECNICO)
        if user is not None:
            self.fields["cliente"].queryset = Cliente.objects.filter(criado_por=user)


class OsMaterialUsoForm(forms.ModelForm):
    class Meta:
        model = OsMaterialUso
        fields = ["material", "quantidade"]
        widgets = {"quantidade": forms.NumberInput(attrs={"min": 1})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["material"].queryset = MaterialCatalogo.objects.filter(ativo=True)
        self.fields["material"].label_from_instance = lambda obj: obj.nome


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
