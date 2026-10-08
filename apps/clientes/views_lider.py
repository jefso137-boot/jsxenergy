import datetime
from collections import defaultdict

from django.contrib import messages
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
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
from apps.relatorios.pdf import gerar_orcamento_pdf_bytes, gerar_recibo_pdf_bytes, os_referencia_recibo

from .forms import ClienteCriarForm
from .models import Cliente, FechamentoMedicao


def periodo_fechamento(data):
    """Semana de fechamento: quinta-feira até a quarta-feira seguinte
    (recebimento sempre na quinta seguinte ao fechamento). `data` deve ser
    um datetime.date."""
    dias_desde_quinta = (data.weekday() - 3) % 7  # quinta-feira = 3
    inicio = data - datetime.timedelta(days=dias_desde_quinta)
    fim = inicio + datetime.timedelta(days=6)
    return inicio, fim


def periodo_para_os(ordem):
    """Semana de fechamento de uma OS concluída: entra na semana da própria
    data agendada dela - vistoria e instalação do mesmo cliente podem cair
    em semanas diferentes. Só o admin pode mover uma OS pra outra semana
    (OrdemServico.data_referencia_medicao)."""
    data = ordem.data_referencia_medicao or ordem.data_agendada
    return periodo_fechamento(data)


@lider_required
def meus_clientes(request):
    clientes = Cliente.objects.filter(criado_por=request.user).order_by("nome")
    return render(request, "lider/meus_clientes.html", {"clientes": clientes})


@lider_required
def cliente_detalhe(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk, criado_por=request.user)
    ordens = OrdemServico.objects.filter(cliente=cliente, criado_por=request.user).select_related("tecnico")

    # Agrupa via subtotal() (não uma multiplicação direta aqui) pra respeitar
    # custos por m² (quantidade × área da placa × valor) e valor_manual - ver
    # apps/relatorios/pdf.py:montar_contexto_recibo pro mesmo bug já corrigido lá.
    valores_por_custo = defaultdict(lambda: 0)
    for uso in OsCustoExtraUso.objects.filter(os__cliente=cliente).select_related("custo"):
        valores_por_custo[uso.custo.nome] += uso.subtotal()
    custos_extras_agrupados = [
        {"custo__nome": nome, "valor": valor} for nome, valor in sorted(valores_por_custo.items())
    ]

    fotos_checklist = OsChecklistResposta.objects.filter(os__cliente=cliente, os__criado_por=request.user)
    fotos_custo_extra = OsCustoExtraFoto.objects.filter(uso__os__cliente=cliente, uso__os__criado_por=request.user)
    fotos_cliente = [r.foto for r in fotos_checklist if r.foto] + [f.foto for f in fotos_custo_extra]

    context = {
        "cliente": cliente,
        "vistorias": ordens.filter(tipo=TipoOS.VISTORIA),
        "instalacoes": ordens.filter(tipo=TipoOS.INSTALACAO),
        "manutencoes": ordens.filter(tipo=TipoOS.MANUTENCAO),
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


def montar_grupos_do_lider(lider):
    """Recalcula, direto das OS concluídas, quanto cada semana de fechamento
    desse líder vale - agrupado por período (início, fim). Usado tanto pela
    tela de Medição quanto pelo diagnóstico automático de divergência (ver
    diagnosticar_diferenca), pra nunca ter duas fórmulas de valor da OS
    divergindo uma da outra."""
    from apps.financas.models import ConfiguracaoPreco

    precos = ConfiguracaoPreco.get_solo()
    grupos = defaultdict(list)

    vistorias = OrdemServico.objects.filter(
        criado_por=lider, tipo=TipoOS.VISTORIA, status=StatusOS.CONCLUIDA
    ).select_related("cliente")
    for os in vistorias:
        periodo = periodo_para_os(os)
        valor = os.valor_servico_manual if os.valor_servico_manual is not None else precos.valor_vistoria
        grupos[periodo].append(
            {
                "cliente": os.cliente, "os": os, "descricao": "Vistoria", "valor": valor,
                "tipo_linha": "servico", "uso_id": None,
            }
        )
        # Cada custo extra vira uma linha própria (não soma tudo junto num só
        # valor) - assim fica claro de qual custo específico se trata e
        # quanto ele vale, em vez de um "custo extra" genérico. "tipo_linha" +
        # "uso_id" permitem montar o link pra tela de detalhe certa de cada
        # linha (ver medicao_cliente / detalhe_custo_extra).
        custos = OsCustoExtraUso.objects.filter(os=os).select_related("custo")
        for uso in custos:
            grupos[periodo].append(
                {
                    "cliente": os.cliente,
                    "os": os,
                    "descricao": uso.custo.nome,
                    "valor": uso.subtotal(),
                    "tipo_linha": "custo_extra",
                    "uso_id": uso.pk,
                }
            )

    instalacoes = OrdemServico.objects.filter(
        criado_por=lider, tipo=TipoOS.INSTALACAO, status=StatusOS.CONCLUIDA
    ).select_related("cliente")
    for os in instalacoes:
        cliente = os.cliente
        valor_painel = cliente.quantidade_modulos * precos.valor_placa
        valor_padrao = precos.valor_padrao if cliente.instalacao_padrao else 0
        valor_automatico = valor_painel + valor_padrao
        valor_base = os.valor_servico_manual if os.valor_servico_manual is not None else valor_automatico

        periodo = periodo_para_os(os)
        grupos[periodo].append(
            {
                "cliente": cliente, "os": os, "descricao": "Instalação", "valor": valor_base,
                "tipo_linha": "servico", "uso_id": None,
            }
        )

        # Os materiais viram UMA linha agregada "Material" (não uma por item,
        # como custo extra) - o detalhe de cada material (quantidade, preço
        # unitário) fica pra tela de detalhe dessa linha, igual à lista que
        # já existia dentro do detalhe da OS.
        materiais = OsMaterialUso.objects.filter(os=os).select_related("material")
        valor_materiais = sum((u.subtotal() for u in materiais), start=0)
        if valor_materiais:
            grupos[periodo].append(
                {
                    "cliente": cliente,
                    "os": os,
                    "descricao": "Material",
                    "valor": valor_materiais,
                    "tipo_linha": "material",
                    "uso_id": None,
                }
            )

        # Idem: cada custo extra da instalação vira sua própria linha, com
        # nome e valor específicos (ex.: "Cabo multiplexado").
        custos = OsCustoExtraUso.objects.filter(os=os).select_related("custo")
        for uso in custos:
            grupos[periodo].append(
                {
                    "cliente": cliente,
                    "os": os,
                    "descricao": uso.custo.nome,
                    "valor": uso.subtotal(),
                    "tipo_linha": "custo_extra",
                    "uso_id": uso.pk,
                }
            )

    # Manutenção não tem valor base fixo/por módulo como vistoria/instalação:
    # o líder escolhe um "serviço" do catálogo na criação da OS (os.servico),
    # e o valor dele vira a linha "servico" automaticamente ao dar baixa. Se
    # nenhum serviço for escolhido, não há linha automática - o valor pode
    # ainda assim ser lançado como custo extra na hora (ver loop abaixo).
    # Em qualquer um dos dois casos, o administrativo pode sobrescrever só
    # nesta OS com valor_servico_manual. Materiais seguem o padrão agregado
    # da instalação.
    manutencoes = OrdemServico.objects.filter(
        criado_por=lider, tipo=TipoOS.MANUTENCAO, status=StatusOS.CONCLUIDA
    ).select_related("cliente", "servico")
    for os in manutencoes:
        cliente = os.cliente
        periodo = periodo_para_os(os)

        if os.valor_servico_manual is not None:
            grupos[periodo].append(
                {
                    "cliente": cliente,
                    "os": os,
                    "descricao": os.servico.nome if os.servico_id else "Manutenção",
                    "valor": os.valor_servico_manual,
                    "tipo_linha": "servico",
                    "uso_id": None,
                }
            )
        elif os.servico_id:
            grupos[periodo].append(
                {
                    "cliente": cliente,
                    "os": os,
                    "descricao": os.servico.nome,
                    "valor": os.servico.valor,
                    "tipo_linha": "servico",
                    "uso_id": None,
                }
            )

        materiais = OsMaterialUso.objects.filter(os=os).select_related("material")
        valor_materiais = sum((u.subtotal() for u in materiais), start=0)
        if valor_materiais:
            grupos[periodo].append(
                {
                    "cliente": cliente,
                    "os": os,
                    "descricao": "Material",
                    "valor": valor_materiais,
                    "tipo_linha": "material",
                    "uso_id": None,
                }
            )

        custos = OsCustoExtraUso.objects.filter(os=os).select_related("custo")
        for uso in custos:
            grupos[periodo].append(
                {
                    "cliente": cliente,
                    "os": os,
                    "descricao": uso.custo.nome,
                    "valor": uso.subtotal(),
                    "tipo_linha": "custo_extra",
                    "uso_id": uso.pk,
                }
            )

    return grupos


def diagnosticar_diferenca(fechamento):
    """Tenta explicar automaticamente a diferença entre o valor pago e o
    valor esperado de um fechamento, procurando um item (ou combinação de
    até 4 itens) daquela semana cujo valor bata exatamente com a diferença -
    ex.: a diferença é exatamente o valor de uma vistoria específica, que
    pode ter ficado de fora da conta. Quando não acha nada que explique,
    devolve um aviso dizendo isso, em vez de deixar sem explicação nenhuma."""
    import itertools

    diferenca = fechamento.diferenca
    if not diferenca:
        return ""

    alvo = abs(diferenca)
    itens = []

    grupos = montar_grupos_do_lider(fechamento.lider)
    linhas = grupos.get((fechamento.inicio, fechamento.fim), [])
    for linha in linhas:
        if linha["valor"]:
            rotulo = f"{linha['descricao']} de {linha['cliente'].nome} (OS #{linha['os'].pk})"
            itens.append((rotulo, linha["valor"]))

    if fechamento.valor_repasse_recebido:
        itens.append(("valor repassado da semana anterior", fechamento.valor_repasse_recebido))

    sentido = "menor" if diferenca < 0 else "maior"

    # Combinação simples (1 item) primeiro, depois até 4 itens juntos - achar
    # com poucos itens é uma explicação bem mais provável (e mais útil) do
    # que uma combinação grande que bate por coincidência.
    tamanho_maximo = min(len(itens), 4)
    for tamanho in range(1, tamanho_maximo + 1):
        for combinacao in itertools.combinations(itens, tamanho):
            soma = sum((valor for _, valor in combinacao), start=0)
            if soma == alvo:
                rotulos = " + ".join(rotulo for rotulo, _ in combinacao)
                return (
                    f"O valor pago ficou R$ {alvo} {sentido} do esperado - essa diferença bate "
                    f"exatamente com: {rotulos}."
                )

    return (
        "Não foi possível identificar automaticamente o que causou essa diferença. "
        "Confira manualmente e anote o que encontrar no campo de observação."
    )


def _agrupar_linhas_por_cliente(linhas):
    """Agrupa as linhas (uma por serviço/custo extra) de uma semana por
    cliente, somando o valor de tudo que é daquele cliente naquela semana -
    usado pra mostrar só "Cliente — valor total" na tela de Medição, sem
    listar cada serviço direto ali (ver medicao_cliente pro detalhe)."""
    agrupado = {}
    ordem = []
    for linha in linhas:
        cliente = linha["cliente"]
        if cliente.pk not in agrupado:
            agrupado[cliente.pk] = {"cliente": cliente, "valor": 0}
            ordem.append(cliente.pk)
        agrupado[cliente.pk]["valor"] += linha["valor"]
    return [agrupado[pk] for pk in ordem]


@lider_required
def medicao(request):
    grupos = montar_grupos_do_lider(request.user)

    hoje = timezone.localdate()
    periodo_atual = periodo_fechamento(hoje)

    fechamentos = []
    if grupos:
        ultimo_inicio_com_os = max(periodo[0] for periodo in grupos.keys())
        cursor = min(periodo[0] for periodo in grupos.keys())
        saldo_anterior = 0

        while True:
            inicio, fim = periodo_fechamento(cursor)
            linhas = grupos.get((inicio, fim), [])
            fechamento_obj, _ = FechamentoMedicao.objects.get_or_create(lider=request.user, inicio=inicio, fim=fim)
            valor_semana = sum((l["valor"] for l in linhas), start=0)
            valor_esperado_total = valor_semana + saldo_anterior

            # Só atualiza enquanto o fechamento ainda não foi pago - depois de
            # pago, os valores ficam congelados pra continuar servindo de
            # referência caso apareça uma OS lançada/movida pra essa semana depois.
            if not fechamento_obj.pago and (
                fechamento_obj.valor_esperado != valor_esperado_total
                or fechamento_obj.valor_repasse_recebido != saldo_anterior
            ):
                fechamento_obj.valor_esperado = valor_esperado_total
                fechamento_obj.valor_repasse_recebido = saldo_anterior
                fechamento_obj.save(update_fields=["valor_esperado", "valor_repasse_recebido"])

            # O que ficar pendente aqui (quando "repassar_pendente" estiver
            # ligado) entra automaticamente no valor esperado da semana
            # seguinte, montada na próxima volta deste loop.
            pendente_efetivo = fechamento_obj.valor_pendente_efetivo
            pago_parcialmente = fechamento_obj.valor_pago is not None and not fechamento_obj.pago
            repassa = bool(pago_parcialmente and fechamento_obj.repassar_pendente and pendente_efetivo)
            saldo_para_proxima = pendente_efetivo if repassa else 0

            fechamentos.append(
                {
                    "inicio": inicio,
                    "fim": fim,
                    "recebimento": fim + datetime.timedelta(days=1),
                    "aberto": hoje <= fim,
                    "pago": fechamento_obj.pago,
                    "data_pagamento": fechamento_obj.data_pagamento,
                    "valor_pago": fechamento_obj.valor_pago,
                    "valor_pendente_fechamento": fechamento_obj.valor_pendente,
                    "valor_pendente_efetivo": pendente_efetivo,
                    "valor_repasse_recebido": fechamento_obj.valor_repasse_recebido,
                    "repassar_pendente": fechamento_obj.repassar_pendente,
                    "tem_divergencia": fechamento_obj.tem_divergencia,
                    "comprovante_pagamento": fechamento_obj.comprovante_pagamento,
                    # Observação só aparece pro líder enquanto o pagamento está
                    # parcial - depois de completar, ela some da tela dele
                    # (continua visível pro admin no /admin).
                    "observacao_divergencia": (
                        fechamento_obj.observacao_divergencia if pago_parcialmente else ""
                    ),
                    "diagnostico_diferenca": (
                        fechamento_obj.diagnostico_diferenca if pago_parcialmente else ""
                    ),
                    "linhas": linhas,
                    "linhas_por_cliente": _agrupar_linhas_por_cliente(linhas),
                    "valor_semana": valor_semana,
                    "valor_esperado_total": fechamento_obj.valor_esperado,
                    "repassado_para_proxima": repassa,
                }
            )

            # Nunca passa da semana atual. Depois da última semana com OS,
            # só continua criando semanas (vazias) se ainda tiver saldo pra
            # repassar - sem isso, toda semana sem OS apareceria em branco.
            if fim >= periodo_atual[1]:
                break
            if inicio >= ultimo_inicio_com_os and not saldo_para_proxima:
                break

            saldo_anterior = saldo_para_proxima
            cursor = fim + datetime.timedelta(days=1)

    fechamentos.reverse()  # semana mais recente primeiro, como antes

    def _pendente_para_resumo(f):
        # Se o pendente dessa semana já foi repassado pra próxima, ele já está
        # embutido no valor total da semana seguinte - contar aqui também
        # duplicaria o valor no resumo.
        if f["repassado_para_proxima"]:
            return 0
        # Numa semana paga parcialmente, o que resta é o valor pendente
        # efetivo (já abatendo o que foi pago, e respeitando um ajuste manual
        # do admin) - não o valor total esperado da semana.
        if f["valor_pago"] is not None:
            return f["valor_pendente_efetivo"] or 0
        return f["valor_esperado_total"] or 0

    context = {
        "fechamentos": fechamentos,
        "valor_pendente": sum((_pendente_para_resumo(f) for f in fechamentos if not f["pago"]), start=0),
        "qtd_pago": sum(1 for f in fechamentos if f["pago"]),
    }
    return render(request, "lider/medicao.html", context)


@lider_required
def medicao_cliente(request, inicio, cliente_id):
    """Nível 2 da Medição: cada serviço/material/custo extra de um cliente
    específico, dentro de uma semana de fechamento específica - uma linha
    por item, explicando como o valor total foi composto. Cada linha leva
    pra tela de detalhe certa daquele tipo de item (ver detalhe_custo_extra,
    detalhe_material; serviço base vai direto pro detalhe da OS)."""
    try:
        data_inicio = datetime.datetime.strptime(inicio, "%Y-%m-%d").date()
    except ValueError:
        raise Http404("Data inválida.")

    periodo_inicio, periodo_fim = periodo_fechamento(data_inicio)
    cliente = get_object_or_404(Cliente, pk=cliente_id, criado_por=request.user)

    grupos = montar_grupos_do_lider(request.user)
    linhas = [
        linha
        for linha in grupos.get((periodo_inicio, periodo_fim), [])
        if linha["cliente"].pk == cliente.pk
    ]
    if not linhas:
        raise Http404("Nenhum serviço desse cliente nessa semana.")

    context = {
        "cliente": cliente,
        "inicio": periodo_inicio,
        "fim": periodo_fim,
        "linhas": linhas,
        "valor_total": sum((linha["valor"] for linha in linhas), start=0),
    }
    return render(request, "lider/medicao_cliente.html", context)


@lider_required
def detalhe_custo_extra(request, os_pk, uso_id):
    """Nível 3 (um dos tipos) da Medição: detalhe de um custo extra
    específico lançado numa OS - nome, valor e o que o técnico registrou
    (texto, foto, PDF ou confirmação, dependendo do tipo do custo)."""
    os = get_object_or_404(OrdemServico, pk=os_pk, criado_por=request.user)
    uso = get_object_or_404(OsCustoExtraUso, pk=uso_id, os=os)
    periodo = periodo_para_os(os)
    context = {
        "os": os,
        "uso": uso,
        "medicao_cliente_url": reverse(
            "lider_medicao_cliente", args=[periodo[0].isoformat(), os.cliente_id]
        ),
    }
    return render(request, "lider/detalhe_custo_extra.html", context)


@lider_required
def detalhe_materiais(request, os_pk):
    """Nível 3 (um dos tipos) da Medição: todos os materiais usados numa OS -
    uma linha "Material" agregada leva aqui, igual já existia dentro do
    detalhe da OS, com o mesmo PDF de materiais/custos reaproveitado."""
    os = get_object_or_404(OrdemServico, pk=os_pk, criado_por=request.user)
    materiais_usados = os.materiais_usados.select_related("material").all()
    periodo = periodo_para_os(os)
    context = {
        "os": os,
        "materiais_usados": materiais_usados,
        "valor_total": sum((uso.subtotal() for uso in materiais_usados), start=0),
        "medicao_cliente_url": reverse(
            "lider_medicao_cliente", args=[periodo[0].isoformat(), os.cliente_id]
        ),
    }
    return render(request, "lider/detalhe_materiais.html", context)


def _quantidade_da_calculadora(request, campo):
    from decimal import Decimal, InvalidOperation

    try:
        quantidade = Decimal(request.POST.get(campo, "0").replace(",", "."))
    except (TypeError, ValueError, InvalidOperation):
        return Decimal("0")
    return quantidade if quantidade > 0 else Decimal("0")


@lider_required
def calculadora(request):
    from apps.financas.models import ConfiguracaoPreco, CustoExtraCatalogo, MaterialCatalogo

    precos = ConfiguracaoPreco.get_solo()
    custos_extras = CustoExtraCatalogo.objects.filter(ativo=True)
    materiais = MaterialCatalogo.objects.filter(ativo=True)

    if request.method == "POST":
        itens = []

        def add_item(nome, preco, campo, area=None):
            quantidade = _quantidade_da_calculadora(request, campo)
            if not quantidade:
                return
            valor = preco * quantidade * (area or 1)
            itens.append({"nome": nome, "preco": preco, "area": area, "quantidade": quantidade, "valor": valor})

        add_item("Painel", precos.valor_placa, "placa")
        add_item("Padrão convencional", precos.valor_padrao, "padrao")
        add_item("Vistoria técnica", precos.valor_vistoria, "vistoria")
        for c in custos_extras:
            add_item(c.nome, c.valor, f"custo_{c.id}", area=c.area_por_placa)
        for m in materiais:
            add_item(m.nome, m.valor, f"material_{m.id}")

        if not itens:
            messages.error(request, "Adicione pelo menos um item com quantidade maior que zero pra gerar o orçamento.")
            return redirect("lider_calculadora")

        nome_cliente = request.POST.get("nome_cliente", "").strip()
        total = sum((item["valor"] for item in itens), start=0)
        pdf_bytes = gerar_orcamento_pdf_bytes(nome_cliente, itens, total)
        nome_arquivo = f"Orcamento-{nome_cliente or 'Cliente'}".replace(" ", "_")
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{nome_arquivo}.pdf"'
        return response

    context = {
        "valor_placa": precos.valor_placa,
        "valor_padrao": precos.valor_padrao,
        "valor_vistoria": precos.valor_vistoria,
        "custos_extras": custos_extras,
        "materiais": materiais,
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
