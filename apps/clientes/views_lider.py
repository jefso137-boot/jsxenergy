from django.contrib import messages
from django.db.models import F, Sum
from django.shortcuts import get_object_or_404, redirect, render

from apps.checklists.models import TipoOS
from apps.ordens.decorators import lider_required
from apps.ordens.models import OrdemServico, OsCustoExtraUso

from .forms import ClienteCriarForm
from .models import Cliente


@lider_required
def meus_clientes(request):
    clientes = Cliente.objects.filter(criado_por=request.user).order_by("nome")
    return render(request, "lider/meus_clientes.html", {"clientes": clientes})


@lider_required
def cliente_detalhe(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk, criado_por=request.user)
    ordens = OrdemServico.objects.filter(cliente=cliente, criado_por=request.user).select_related("tecnico")

    custos_extras_agrupados = (
        OsCustoExtraUso.objects.filter(os__cliente=cliente)
        .values("custo__nome")
        .annotate(valor=Sum(F("quantidade") * F("custo__valor")))
        .order_by("custo__nome")
    )

    context = {
        "cliente": cliente,
        "vistorias": ordens.filter(tipo=TipoOS.VISTORIA),
        "instalacoes": ordens.filter(tipo=TipoOS.INSTALACAO),
        "valor_instalacao": cliente.valor_estimado_instalacao(),
        "valor_materiais": cliente.valor_materiais_usados(),
        "custos_extras_agrupados": custos_extras_agrupados,
        "valor_total": cliente.valor_total(),
    }
    return render(request, "lider/cliente_detalhe.html", context)


@lider_required
def criar_cliente(request):
    if request.method == "POST":
        form = ClienteCriarForm(request.POST)
        if form.is_valid():
            cliente = form.save(commit=False)
            cliente.criado_por = request.user
            cliente.save()
            messages.success(request, "Cliente cadastrado.")
            return redirect("lider_cliente_detalhe", pk=cliente.pk)
    else:
        form = ClienteCriarForm()
    return render(request, "lider/criar_cliente.html", {"form": form})
