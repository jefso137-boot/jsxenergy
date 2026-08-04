from django.contrib import messages
from django.shortcuts import redirect, render

from apps.ordens.decorators import lider_required

from .forms import ClienteCriarForm
from .models import Cliente


@lider_required
def meus_clientes(request):
    clientes = Cliente.objects.filter(criado_por=request.user).order_by("nome")
    return render(request, "lider/meus_clientes.html", {"clientes": clientes})


@lider_required
def criar_cliente(request):
    if request.method == "POST":
        form = ClienteCriarForm(request.POST)
        if form.is_valid():
            cliente = form.save(commit=False)
            cliente.criado_por = request.user
            cliente.save()
            messages.success(request, "Cliente cadastrado.")
            return redirect("lider_meus_clientes")
    else:
        form = ClienteCriarForm()
    return render(request, "lider/criar_cliente.html", {"form": form})
