import logging
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.checklists.models import TipoCampo
from apps.financas.models import ConfiguracaoPreco, CustoExtraCatalogo, MaterialCatalogo
from apps.relatorios.pdf import gerar_materiais_pdf_bytes, gerar_orcamento_pdf_bytes, gerar_pdf_os

from .decorators import tecnico_required
from .forms import OsNarrativaForm
from .models import (
    OrdemServico,
    OsChecklistResposta,
    OsCustoExtraFoto,
    OsCustoExtraUso,
    OsMaterialUso,
    StatusOS,
)
from .utils import ORDENACAO_PRIORIDADE_STATUS, checklist_com_respostas

logger = logging.getLogger(__name__)


@tecnico_required
def minhas_os(request):
    ordens = (
        OrdemServico.objects.filter(tecnico=request.user)
        .select_related("cliente")
        .annotate(status_prioridade=ORDENACAO_PRIORIDADE_STATUS)
        .order_by("status_prioridade", "-data_agendada")
    )
    return render(request, "tecnico/minhas_os.html", {"ordens": ordens})


def _quantidade_da_calculadora(request, campo):
    from decimal import Decimal, InvalidOperation

    try:
        quantidade = Decimal(request.POST.get(campo, "0").replace(",", "."))
    except (TypeError, ValueError, InvalidOperation):
        return Decimal("0")
    return quantidade if quantidade > 0 else Decimal("0")


@tecnico_required
def calculadora(request):
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
            return redirect("tecnico_calculadora")

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
    return render(request, "tecnico/calculadora.html", context)


def _get_os_do_tecnico(request, pk):
    return get_object_or_404(OrdemServico, pk=pk, tecnico=request.user)


def _atualizar_pdf_se_concluida(request, os):
    """Reemite o PDF do relatório quando a OS já foi concluída - sem isso, o
    PDF ficava "congelado" com o conteúdo de quando o técnico deu baixa,
    mesmo que o checklist, as informações do relatório ou os custos extras
    fossem editados depois."""
    if os.status != StatusOS.CONCLUIDA:
        return
    try:
        gerar_pdf_os(os)
    except Exception:
        logger.exception("Falha ao atualizar PDF da OS #%s (tipo=%s)", os.pk, os.tipo)
        messages.error(
            request,
            "As informações foram salvas, mas houve um erro ao atualizar o PDF. "
            "Use o botão \"Atualizar PDF do relatório\" abaixo para tentar novamente.",
        )


def _salvar_respostas_checklist(request, os, template):
    for item in template.itens.all():
        defaults = {"observacao": request.POST.get(f"obs_{item.id}", "").strip()}
        if item.tipo_campo == TipoCampo.CAIXA_SELECAO:
            defaults["marcado"] = request.POST.get(f"item_{item.id}") == "on"
        elif item.tipo_campo == TipoCampo.TEXTO:
            defaults["texto"] = request.POST.get(f"item_{item.id}", "").strip()
        elif item.tipo_campo == TipoCampo.FOTO:
            arquivo = request.FILES.get(f"item_{item.id}")
            if arquivo:
                defaults["foto"] = arquivo
        OsChecklistResposta.objects.update_or_create(os=os, item=item, defaults=defaults)


@tecnico_required
def pdf_materiais(request, pk):
    os = _get_os_do_tecnico(request, pk)
    if os.status != StatusOS.CONCLUIDA:
        messages.error(request, "Só é possível ver o PDF de materiais de uma OS concluída.")
        return redirect("tecnico_detalhe_os", pk=os.pk)

    pdf_bytes = gerar_materiais_pdf_bytes(os)
    nome_arquivo = f"Materiais-OS-{os.pk}-{os.cliente.nome}".replace(" ", "_")
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{nome_arquivo}.pdf"'
    return response


@tecnico_required
def detalhe_os(request, pk):
    os = _get_os_do_tecnico(request, pk)

    if request.method == "POST":
        acao = request.POST.get("acao")

        if acao == "salvar_checklist":
            template = os.get_checklist_template()
            if template:
                _salvar_respostas_checklist(request, os, template)
            if os.status == StatusOS.ABERTA:
                os.status = StatusOS.EM_ANDAMENTO
                os.save(update_fields=["status"])
            _atualizar_pdf_se_concluida(request, os)
            messages.success(request, "Checklist salvo.")
            return redirect("tecnico_detalhe_os", pk=os.pk)

        if acao == "add_materiais":
            if os.tipo != "INSTALACAO" or not os.cliente.precisa_material_ca:
                raise PermissionDenied("Este cliente não precisa de material C.A.")
            catalogo = {str(m.id): m for m in MaterialCatalogo.objects.filter(ativo=True)}
            registrados = 0
            for material_id, quantidade in zip(
                request.POST.getlist("material_id"), request.POST.getlist("quantidade")
            ):
                material = catalogo.get(material_id)
                if not material or not quantidade.isdigit() or int(quantidade) < 1:
                    continue
                uso, criado = OsMaterialUso.objects.get_or_create(
                    os=os, material=material, defaults={"quantidade": int(quantidade)}
                )
                if not criado:
                    uso.quantidade += int(quantidade)
                    uso.save(update_fields=["quantidade"])
                registrados += 1
            if registrados:
                messages.success(request, "Materiais registrados.")
            else:
                messages.error(request, "Nenhum material selecionado.")
            return redirect("tecnico_detalhe_os", pk=os.pk)

        if acao == "excluir_material":
            if os.tipo != "INSTALACAO" or not os.cliente.precisa_material_ca:
                raise PermissionDenied("Este cliente não precisa de material C.A.")
            OsMaterialUso.objects.filter(os=os, pk=request.POST.get("uso_id")).delete()
            messages.success(request, "Material removido.")
            return redirect("tecnico_detalhe_os", pk=os.pk)

        if acao == "salvar_custos_extras":
            catalogo = {
                str(c.id): c
                for c in CustoExtraCatalogo.objects.filter(ativo=True).filter(
                    Q(aplicavel_em="AMBOS") | Q(aplicavel_em=os.tipo)
                )
            }
            salvos = 0
            for custo_id in request.POST.getlist("custo_id"):
                custo = catalogo.get(custo_id)
                if not custo:
                    continue

                if custo.area_por_placa:
                    quantidade = os.cliente.quantidade_modulos
                else:
                    quantidade_raw = request.POST.get(f"quantidade_{custo_id}", "1")
                    quantidade = int(quantidade_raw) if quantidade_raw.isdigit() and int(quantidade_raw) >= 1 else 1

                fotos_novas = []
                defaults = {"quantidade": quantidade}
                if custo.tipo_campo == TipoCampo.CAIXA_SELECAO:
                    defaults["marcado"] = request.POST.get(f"marcado_{custo_id}") == "on"
                elif custo.tipo_campo == TipoCampo.TEXTO:
                    defaults["texto"] = request.POST.get(f"texto_{custo_id}", "").strip()
                elif custo.tipo_campo == TipoCampo.FOTO:
                    fotos_novas = request.FILES.getlist(f"foto_{custo_id}")
                    if not fotos_novas:
                        continue
                elif custo.tipo_campo == TipoCampo.ARQUIVO_PDF:
                    arquivo_pdf = request.FILES.get(f"arquivo_{custo_id}")
                    if not arquivo_pdf:
                        continue
                    defaults["arquivo_pdf"] = arquivo_pdf
                elif custo.tipo_campo == TipoCampo.FOTO_TEXTO:
                    fotos_novas = request.FILES.getlist(f"foto_{custo_id}")
                    texto_material = request.POST.get(f"texto_{custo_id}", "").strip()
                    if not fotos_novas and not texto_material:
                        continue
                    defaults["texto"] = texto_material

                if custo.valor_definido_pelo_tecnico:
                    valor_raw = request.POST.get(f"valor_{custo_id}", "").strip().replace(",", ".")
                    try:
                        valor_manual = Decimal(valor_raw)
                    except (InvalidOperation, ValueError):
                        valor_manual = None
                    if not valor_manual or valor_manual <= 0:
                        messages.error(request, f"Informe um valor válido para \"{custo.nome}\".")
                        continue
                    defaults["valor_manual"] = valor_manual

                uso, criado = OsCustoExtraUso.objects.get_or_create(os=os, custo=custo, defaults=defaults)
                if not criado:
                    uso.quantidade = quantidade
                    if custo.tipo_campo == TipoCampo.CAIXA_SELECAO:
                        uso.marcado = defaults["marcado"]
                    elif custo.tipo_campo == TipoCampo.TEXTO:
                        uso.texto = defaults["texto"]
                    elif custo.tipo_campo == TipoCampo.ARQUIVO_PDF:
                        uso.arquivo_pdf = defaults["arquivo_pdf"]
                    elif custo.tipo_campo == TipoCampo.FOTO_TEXTO:
                        uso.texto = defaults["texto"]
                    if custo.valor_definido_pelo_tecnico:
                        uso.valor_manual = defaults["valor_manual"]
                    uso.save()

                for arquivo in fotos_novas:
                    OsCustoExtraFoto.objects.create(uso=uso, foto=arquivo)

                salvos += 1
            if salvos:
                _atualizar_pdf_se_concluida(request, os)
                messages.success(request, "Custos extras registrados.")
            else:
                messages.error(request, "Nenhum custo extra válido para registrar.")
            return redirect("tecnico_detalhe_os", pk=os.pk)

        if acao == "excluir_custo_extra":
            OsCustoExtraUso.objects.filter(os=os, pk=request.POST.get("uso_id")).delete()
            _atualizar_pdf_se_concluida(request, os)
            messages.success(request, "Custo extra removido.")
            return redirect("tecnico_detalhe_os", pk=os.pk)

        if acao == "salvar_narrativa":
            narrativa_form = OsNarrativaForm(request.POST, instance=os)
            if narrativa_form.is_valid():
                narrativa_form.save()
                _atualizar_pdf_se_concluida(request, os)
                messages.success(request, "Informações do relatório salvas.")
            else:
                messages.error(request, "Verifique os campos do relatório.")
            return redirect("tecnico_detalhe_os", pk=os.pk)

        if acao == "dar_baixa":
            template = os.get_checklist_template()
            if template:
                _salvar_respostas_checklist(request, os, template)

            pendentes = []
            if template:
                respostas = {r.item_id: r for r in os.respostas_checklist.all()}
                for item in template.itens.filter(obrigatorio=True):
                    resposta = respostas.get(item.id)
                    if not resposta or not resposta.respondido():
                        pendentes.append(item.descricao)

            if pendentes:
                messages.error(
                    request,
                    "Não é possível dar baixa. Pendências: " + "; ".join(pendentes),
                )
                return redirect("tecnico_detalhe_os", pk=os.pk)

            if not os.resumo_tecnico_bullets.strip() and template:
                respostas = {r.item_id: r for r in os.respostas_checklist.all()}
                bullets = []
                for item in template.itens.all():
                    resposta = respostas.get(item.id)
                    if not resposta:
                        continue
                    if item.tipo_campo == TipoCampo.CAIXA_SELECAO and resposta.marcado:
                        bullets.append(item.descricao)
                    elif item.tipo_campo == TipoCampo.TEXTO and resposta.texto.strip():
                        bullets.append(f"{item.descricao}: {resposta.texto.strip()}")
                os.resumo_tecnico_bullets = "\n".join(bullets)

            os.status = StatusOS.CONCLUIDA
            os.data_conclusao = timezone.now()
            os.save()

            try:
                gerar_pdf_os(os)
                messages.success(request, "OS concluída e relatório PDF gerado com sucesso.")
            except Exception:
                logger.exception("Falha ao gerar PDF da OS #%s (tipo=%s)", os.pk, os.tipo)
                messages.error(
                    request,
                    "OS concluída, mas houve um erro ao gerar o PDF. Use o botão \"Gerar PDF do relatório\" "
                    "abaixo para tentar novamente.",
                )
            return redirect("tecnico_detalhe_os", pk=os.pk)

        if acao == "gerar_pdf":
            if os.status != StatusOS.CONCLUIDA:
                raise PermissionDenied("Só é possível gerar o PDF de uma OS concluída.")
            try:
                gerar_pdf_os(os)
                messages.success(request, "PDF gerado com sucesso.")
            except Exception:
                logger.exception("Falha ao gerar PDF da OS #%s (tipo=%s)", os.pk, os.tipo)
                messages.error(request, "Não foi possível gerar o PDF. Tente novamente em instantes.")
            return redirect("tecnico_detalhe_os", pk=os.pk)

    materiais_usados = os.materiais_usados.select_related("material").all()
    custos_extras_usados = os.custos_extras.select_related("custo").prefetch_related("fotos").all()
    context = {
        "os": os,
        "checklist": checklist_com_respostas(os),
        "narrativa_form": OsNarrativaForm(instance=os),
        "materiais_usados": materiais_usados,
        "materiais_disponiveis": MaterialCatalogo.objects.filter(ativo=True).exclude(
            id__in=materiais_usados.values_list("material_id", flat=True)
        ),
        "custos_extras_usados": custos_extras_usados,
        "custos_extras_disponiveis": CustoExtraCatalogo.objects.filter(ativo=True)
        .filter(Q(aplicavel_em="AMBOS") | Q(aplicavel_em=os.tipo))
        .exclude(id__in=custos_extras_usados.values_list("custo_id", flat=True)),
    }
    return render(request, "tecnico/detalhe_os.html", context)
