from django import forms

from .models import ConfiguracaoPreco, MaterialCatalogo


class ConfiguracaoPrecoForm(forms.ModelForm):
    class Meta:
        model = ConfiguracaoPreco
        fields = ["valor_placa", "valor_padrao"]
        labels = {
            "valor_placa": "Valor da instalação por placa",
            "valor_padrao": "Valor da instalação do padrão",
        }


class MaterialCatalogoForm(forms.ModelForm):
    class Meta:
        model = MaterialCatalogo
        fields = ["nome", "valor"]
        labels = {"nome": "Produto", "valor": "Valor unitário"}
