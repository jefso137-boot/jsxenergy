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
            "quantidade_modulos",
            "instalacao_padrao",
        ]
        labels = {
            "quantidade_modulos": "Quantidade de módulos",
            "instalacao_padrao": "Terá instalação de padrão?",
        }
        widgets = {
            "telefone": forms.TextInput(attrs={"placeholder": "(11) 99999-0000"}),
            "quantidade_modulos": forms.NumberInput(attrs={"min": 0}),
        }
