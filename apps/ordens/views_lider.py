import logging

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from apps.relatorios.pdf import gerar_pdf_os

from .decorators import lider_required
from .forms import OsCriarForm
from .models import OrdemServico, StatusOS
from .utils import ORDENACAO_PRIORIDADE_STATUS, checklist_com_respostas

logger = logging.getLogger(__name__)


@lider_required
def minhas_os(request):
    ordens = (
        OrdemServico.objects.filter(criado_por=request.user)
        .select_related("cliente", "tecnico")
        .annotate(status_prioridade=ORDENACAO_PRIORIDADE_STATUS)
        .order_by("status_prioridade", "-data_agendada")
    )
    return render(request, "lider/minhas_os.html", {"ordens": ordens})


@lider_required
def criar_os(request):
    if request.method == "POST":
        form = OsCriarForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            os = form.save(commit=False)
            os.criado_por = request.user
            if os.tipo != "INSTALACAO":
                os.documento_pdf_1 = None
                os.documento_pdf_2 = None
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

    if request.method == "POST" and request.POST.get("acao") == "gerar_pdf":
        if os.status != StatusOS.CONCLUIDA:
            messages.error(request, "Só é possível gerar o PDF de uma OS concluída.")
        else:
            try:
                gerar_pdf_os(os)
                messages.success(request, "PDF gerado com sucesso.")
            except Exception:
                logger.exception("Falha ao gerar PDF da OS #%s (tipo=%s)", os.pk, os.tipo)
                messages.error(request, "Não foi possível gerar o PDF. Tente novamente em instantes.")
        return redirect("lider_detalhe_os", pk=os.pk)

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


@lider_required
def editar_os(request, pk):
    os = get_object_or_404(OrdemServico, pk=pk, criado_por=request.user)
    if request.method == "POST":
        form = OsCriarForm(request.POST, request.FILES, instance=os, user=request.user)
        if form.is_valid():
            os = form.save(commit=False)
            if os.tipo != "INSTALACAO":
                os.documento_pdf_1 = None
                os.documento_pdf_2 = None
            os.save()
            messages.success(request, "OS atualizada.")
            return redirect("lider_detalhe_os", pk=os.pk)
    else:
        form = OsCriarForm(instance=os, user=request.user)
    return render(request, "lider/editar_os.html", {"form": form, "os": os})


@lider_required
def excluir_os(request, pk):
    os = get_object_or_404(OrdemServico, pk=pk, criado_por=request.user)
    if request.method != "POST":
        return redirect("lider_detalhe_os", pk=os.pk)
    os.delete()
    messages.success(request, "OS excluída.")
    return redirect("lider_minhas_os")
