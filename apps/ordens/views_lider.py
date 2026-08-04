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
        form = OsCriarForm(request.POST)
        if form.is_valid():
            os = form.save(commit=False)
            os.criado_por = request.user
            os.save()
            messages.success(request, "OS criada e atribuída ao técnico.")
            return redirect("lider_minhas_os")
    else:
        form = OsCriarForm()
    return render(request, "lider/criar_os.html", {"form": form})


@lider_required
def detalhe_os(request, pk):
    os = get_object_or_404(OrdemServico, pk=pk, criado_por=request.user)
    context = {
        "os": os,
        "checklist": checklist_com_respostas(os),
    }
    return render(request, "lider/detalhe_os.html", context)
