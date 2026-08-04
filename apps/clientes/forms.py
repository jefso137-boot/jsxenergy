from django import forms

from .models import Cliente


class ClienteCriarForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ["nome", "telefone", "email", "endereco", "cidade"]
        widgets = {
            "telefone": forms.TextInput(attrs={"placeholder": "(11) 99999-0000"}),
        }
