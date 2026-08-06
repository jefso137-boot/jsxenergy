from django import forms

from .models import Cliente


class ClienteCriarForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            "nome",
            "telefone",
            "email",
            "endereco",
            "cidade",
            "link_localizacao",
            "quantidade_modulos",
            "instalacao_padrao",
            "precisa_material_ca",
        ]
        labels = {
            "link_localizacao": "Link da localização",
            "quantidade_modulos": "Quantidade de módulos",
            "instalacao_padrao": "Terá instalação de padrão?",
            "precisa_material_ca": "Vai precisar de material C.A.?",
        }
        widgets = {
            "telefone": forms.TextInput(attrs={"placeholder": "(11) 99999-0000"}),
            "quantidade_modulos": forms.NumberInput(attrs={"min": 0}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            self.fields["quantidade_modulos"].initial = 0
