import datetime
from collections import defaultdict

from django.contrib import messages
from django.db.models import F, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.checklists.models import TipoOS
from apps.ordens.decorators import lider_required
from apps.ordens.models import OrdemServico, OsChecklistResposta, OsCustoExtraFoto, OsCustoExtraUso
from apps.relatorios.pdf import gerar_recibo_pdf_bytes, os_referencia_recibo

from .forms import ClienteCriarForm
from .models import Cliente


def periodo_fechamento(data):
    """Semana de fechamento: quinta-feira até a quarta-feira seguinte
    (recebimento sempre na quinta seguinte ao fechamento). `data` deve ser
    um datetime.date (veja data_referencia_do_cliente)."""
    dias_desde_quinta = (data.weekday() - 3) % 7  # quinta-feira = 3
    inicio = data - datetime.timedelta(days=dias_desde_quinta)
    fim = inicio + datetime.timedelta(days=6)
    return inicio, fim


def data_referencia_do_cliente(cliente):
    return cliente.data_referencia_medicao or timezone.localtime(cliente.criado_em).date()


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

    fotos_checklist = OsChecklistResposta.objects.filter(os__cliente=cliente, os__criado_por=request.user)
    fotos_custo_extra = OsCustoExtraFoto.objects.filter(uso__os__cliente=cliente, uso__os__criado_por=request.user)
    fotos_cliente = [r.foto for r in fotos_checklist if r.foto] + [f.foto for f in fotos_custo_extra]

    context = {
        "cliente": cliente,
        "vistorias": ordens.filter(tipo=TipoOS.VISTORIA),
        "instalacoes": ordens.filter(tipo=TipoOS.INSTALACAO),
        "valor_instalacao": cliente.valor_estimado_instalacao(),
        "valor_materiais": cliente.valor_materiais_usados(),
        "custos_extras_agrupados": custos_extras_agrupados,
        "valor_total": cliente.valor_total(),
        "tem_recibo_disponivel": os_referencia_recibo(cliente) is not None,
        "fotos_cliente": fotos_cliente,
    }
    return render(request, "lider/cliente_detalhe.html", context)


@lider_required
def recibo_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk, criado_por=request.user)
    if os_referencia_recibo(cliente) is None:
        messages.error(
            request, "Ainda não há nenhuma OS de instalação concluída para gerar o recibo deste cliente."
        )
        return redirect("lider_cliente_detalhe", pk=cliente.pk)

    pdf_bytes = gerar_recibo_pdf_bytes(cliente)
    nome_arquivo = f"Recibo-{cliente.nome}".replace(" ", "_")
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{nome_arquivo}.pdf"'
    return response


@lider_required
def medicao(request):
    if request.method == "POST":
        cliente = get_object_or_404(Cliente, pk=request.POST.get("cliente_id"), criado_por=request.user)
        acao = request.POST.get("acao")
        if acao == "marcar_pago":
            cliente.pago = True
            cliente.data_pagamento = timezone.now()
            cliente.save(update_fields=["pago", "data_pagamento"])
            messages.success(request, f"{cliente.nome} marcado como pago.")
        elif acao == "marcar_pendente":
            cliente.pago = False
            cliente.data_pagamento = None
            cliente.save(update_fields=["pago", "data_pagamento"])
            messages.success(request, f"{cliente.nome} marcado como pendente.")
        elif acao == "mover_semana":
            nova_data = request.POST.get("nova_data")
            try:
                cliente.data_referencia_medicao = datetime.date.fromisoformat(nova_data)
            except (TypeError, ValueError):
                messages.error(request, "Data inválida.")
                return redirect("lider_medicao")
            cliente.save(update_fields=["data_referencia_medicao"])
            messages.success(request, f"{cliente.nome} movido de semana de medição.")
        elif acao == "resetar_semana":
            cliente.data_referencia_medicao = None
            cliente.save(update_fields=["data_referencia_medicao"])
            messages.success(request, f"{cliente.nome} voltou a usar a data de cadastro.")
        return redirect("lider_medicao")

    clientes = Cliente.objects.filter(criado_por=request.user).order_by("-criado_em")

    grupos = defaultdict(list)
    for cliente in clientes:
        periodo = periodo_fechamento(data_referencia_do_cliente(cliente))
        grupos[periodo].append({"cliente": cliente, "valor_total": cliente.valor_total()})

    hoje = timezone.localdate()
    fechamentos = []
    for (inicio, fim), linhas in sorted(grupos.items(), key=lambda item: item[0][0], reverse=True):
        fechamentos.append(
            {
                "inicio": inicio,
                "fim": fim,
                "recebimento": fim + datetime.timedelta(days=1),
                "aberto": hoje <= fim,
                "linhas": linhas,
                "valor_pendente": sum((l["valor_total"] for l in linhas if not l["cliente"].pago), start=0),
                "valor_pago": sum((l["valor_total"] for l in linhas if l["cliente"].pago), start=0),
            }
        )

    context = {
        "fechamentos": fechamentos,
        "valor_pendente": sum((f["valor_pendente"] for f in fechamentos), start=0),
        "valor_pago": sum((f["valor_pago"] for f in fechamentos), start=0),
    }
    return render(request, "lider/medicao.html", context)


@lider_required
def calculadora(request):
    from apps.financas.models import ConfiguracaoPreco, CustoExtraCatalogo, MaterialCatalogo

    precos = ConfiguracaoPreco.get_solo()
    context = {
        "valor_placa": precos.valor_placa,
        "valor_padrao": precos.valor_padrao,
        "custos_extras": CustoExtraCatalogo.objects.filter(ativo=True),
        "materiais": MaterialCatalogo.objects.filter(ativo=True),
    }
    return render(request, "lider/calculadora.html", context)


@lider_required
def criar_cliente(request):
    if request.method == "POST":
        form = ClienteCriarForm(request.POST, request.FILES)
        if form.is_valid():
            cliente = form.save(commit=False)
            cliente.criado_por = request.user
            cliente.save()
            messages.success(request, "Cliente cadastrado.")
            return redirect("lider_cliente_detalhe", pk=cliente.pk)
    else:
        form = ClienteCriarForm()
    return render(request, "lider/criar_cliente.html", {"form": form})
