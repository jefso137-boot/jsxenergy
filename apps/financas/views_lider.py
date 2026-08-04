from django.contrib import messages
from django.shortcuts import redirect, render

from apps.ordens.decorators import lider_required

from .forms import ConfiguracaoPrecoForm, MaterialCatalogoForm
from .models import ConfiguracaoPreco, MaterialCatalogo


@lider_required
def financas(request):
    precos = ConfiguracaoPreco.get_solo()

    if request.method == "POST" and request.POST.get("acao") == "salvar_precos":
        preco_form = ConfiguracaoPrecoForm(request.POST, instance=precos)
        if preco_form.is_valid():
            preco_form.save()
            messages.success(request, "Preços atualizados.")
            return redirect("lider_financas")
    else:
        preco_form = ConfiguracaoPrecoForm(instance=precos)

    if request.method == "POST" and request.POST.get("acao") == "add_material":
        material_form = MaterialCatalogoForm(request.POST)
        if material_form.is_valid():
            material_form.save()
            messages.success(request, "Material adicionado ao catálogo.")
            return redirect("lider_financas")
    else:
        material_form = MaterialCatalogoForm()

    context = {
        "preco_form": preco_form,
        "material_form": material_form,
        "materiais": MaterialCatalogo.objects.filter(ativo=True),
    }
    return render(request, "lider/financas.html", context)
