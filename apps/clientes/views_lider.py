import datetime
from collections import defaultdict

from django.contrib import messages
from django.db.models import F, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.checklists.models import TipoOS
from apps.ordens.decorators import lider_required
from apps.ordens.models import (
    OrdemServico,
    OsChecklistResposta,
    OsCustoExtraFoto,
    OsCustoExtraUso,
    OsMaterialUso,
    StatusOS,
)
from apps.relatorios.pdf import gerar_recibo_pdf_bytes, os_referencia_recibo

from .forms import ClienteCriarForm
from .models import Cliente, FechamentoMedicao


def periodo_fechamento(data):
    """Semana de fechamento: quinta-feira até a quarta-feira seguinte
    (recebimento sempre na quinta seguinte ao fechamento). `data` deve ser
    um datetime.date (veja data_referencia_do_cliente)."""
    dias_desde_quinta = (data.weekday() - 3) % 7  # quinta-feira = 3
    inicio = data - datetime.timedelta(days=dias_desde_quinta)
    fim = inicio + datetime.timedelta(days=6)
    return inicio, fim


def periodo_para_contribuicao(cliente, data_conclusao):
    """Semana de fechamento de um valor apurado numa OS concluída: usa a
    data manual do cliente (se movido) ou a data de conclusão da própria OS."""
    if cliente.data_referencia_medicao:
        data = cliente.data_referencia_medicao
    else:
        data = timezone.localtime(data_conclusao).date()
    return periodo_fechamento(data)


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
        if acao == "mover_semana":
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

    from apps.financas.models import ConfiguracaoPreco

    precos = ConfiguracaoPreco.get_solo()
    grupos = defaultdict(list)

    vistorias = OrdemServico.objects.filter(
        criado_por=request.user, tipo=TipoOS.VISTORIA, status=StatusOS.CONCLUIDA
    ).select_related("cliente")
    for os in vistorias:
        periodo = periodo_para_contribuicao(os.cliente, os.data_conclusao)
        grupos[periodo].append({"cliente": os.cliente, "descricao": "Vistoria", "valor": precos.valor_vistoria})

    instalacoes = OrdemServico.objects.filter(
        criado_por=request.user, tipo=TipoOS.INSTALACAO, status=StatusOS.CONCLUIDA
    ).select_related("cliente")
    for os in instalacoes:
        cliente = os.cliente
        valor_painel = cliente.quantidade_modulos * precos.valor_placa
        valor_padrao = precos.valor_padrao if cliente.instalacao_padrao else 0
        materiais = OsMaterialUso.objects.filter(os=os).select_related("material")
        valor_materiais = sum((u.subtotal() for u in materiais), start=0)
        custos = OsCustoExtraUso.objects.filter(os=os).select_related("custo")
        valor_custos = sum((u.subtotal() for u in custos), start=0)
        valor_os = valor_painel + valor_padrao + valor_materiais + valor_custos

        periodo = periodo_para_contribuicao(cliente, os.data_conclusao)
        grupos[periodo].append({"cliente": cliente, "descricao": "Instalação", "valor": valor_os})

    hoje = timezone.localdate()
    fechamentos = []
    for (inicio, fim), linhas in sorted(grupos.items(), key=lambda item: item[0][0], reverse=True):
        fechamento_obj, _ = FechamentoMedicao.objects.get_or_create(lider=request.user, inicio=inicio, fim=fim)
        valor_semana = sum((l["valor"] for l in linhas), start=0)
        fechamentos.append(
            {
                "inicio": inicio,
                "fim": fim,
                "recebimento": fim + datetime.timedelta(days=1),
                "aberto": hoje <= fim,
                "pago": fechamento_obj.pago,
                "data_pagamento": fechamento_obj.data_pagamento,
                "linhas": linhas,
                "valor_semana": valor_semana,
            }
        )

    context = {
        "fechamentos": fechamentos,
        "valor_pendente": sum((f["valor_semana"] for f in fechamentos if not f["pago"]), start=0),
        "qtd_pago": sum(1 for f in fechamentos if f["pago"]),
    }
    return render(request, "lider/medicao.html", context)


@lider_required
def calculadora(request):
    from apps.financas.models import ConfiguracaoPreco, CustoExtraCatalogo, MaterialCatalogo

    precos = ConfiguracaoPreco.get_solo()
    context = {
        "valor_placa": precos.valor_placa,
        "valor_padrao": precos.valor_padrao,
        "valor_vistoria": precos.valor_vistoria,
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
