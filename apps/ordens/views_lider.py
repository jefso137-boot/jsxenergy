from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from .decorators import lider_required
from .forms import OsCriarForm
from .models import OrdemServico
from .utils import checklist_com_respostas


@lider_required
def minhas_os(request):
    ordens = (
        OrdemServico.objects.filter(criado_por=request.user)
        .select_related("cliente", "tecnico")
        .order_by("status", "-data_agendada")
    )
    return render(request, "lider/minhas_os.html", {"ordens": ordens})


@lider_required
def criar_os(request):
    if request.method == "POST":
        form = OsCriarForm(request.POST, user=request.user)
        if form.is_valid():
            os = form.save(commit=False)
            os.criado_por = request.user
            os.save()
            messages.success(request, "OS criada e atribuída ao técnico.")
            return redirect("lider_cliente_detalhe", pk=os.cliente_id)
    else:
        initial = {}
        cliente_id = request.GET.get("cliente")
        if cliente_id:
            initial["cliente"] = cliente_id
        form = OsCriarForm(user=request.user, initial=initial)
    return render(request, "lider/criar_os.html", {"form": form})


@lider_required
def detalhe_os(request, pk):
    os = get_object_or_404(OrdemServico, pk=pk, criado_por=request.user)
    materiais_usados = os.materiais_usados.select_related("material").all()
    custos_extras_usados = os.custos_extras.select_related("custo").all()
    context = {
        "os": os,
        "checklist": checklist_com_respostas(os),
        "materiais_usados": materiais_usados,
        "valor_materiais_os": sum((uso.subtotal() for uso in materiais_usados), start=0),
        "custos_extras_usados": custos_extras_usados,
        "valor_custos_extras_os": sum((uso.subtotal() for uso in custos_extras_usados), start=0),
    }
    return render(request, "lider/detalhe_os.html", context)
