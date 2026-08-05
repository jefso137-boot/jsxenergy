from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.checklists.models import TipoCampo
from apps.financas.models import CustoExtraCatalogo, MaterialCatalogo
from apps.relatorios.pdf import gerar_pdf_os

from .decorators import tecnico_required
from .forms import OsNarrativaForm
from .models import OrdemServico, OsChecklistResposta, OsCustoExtraUso, OsMaterialUso, StatusOS
from .utils import checklist_com_respostas


@tecnico_required
def minhas_os(request):
    ordens = (
        OrdemServico.objects.filter(tecnico=request.user)
        .select_related("cliente")
        .order_by("status", "-data_agendada")
    )
    return render(request, "tecnico/minhas_os.html", {"ordens": ordens})


def _get_os_do_tecnico(request, pk):
    return get_object_or_404(OrdemServico, pk=pk, tecnico=request.user)


@tecnico_required
def detalhe_os(request, pk):
    os = _get_os_do_tecnico(request, pk)

    if request.method == "POST":
        acao = request.POST.get("acao")

        if acao == "salvar_checklist":
            template = os.get_checklist_template()
            if template:
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
            if os.status == StatusOS.ABERTA:
                os.status = StatusOS.EM_ANDAMENTO
                os.save(update_fields=["status"])
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
            if os.tipo != "INSTALACAO":
                raise PermissionDenied("Custos extras só se aplicam a OS de instalação.")
            catalogo = {str(c.id): c for c in CustoExtraCatalogo.objects.filter(ativo=True)}
            salvos = 0
            for custo_id in request.POST.getlist("custo_id"):
                custo = catalogo.get(custo_id)
                if not custo:
                    continue
                defaults = {}
                if custo.tipo_campo == TipoCampo.CAIXA_SELECAO:
                    defaults["marcado"] = request.POST.get(f"custo_{custo_id}") == "on"
                elif custo.tipo_campo == TipoCampo.TEXTO:
                    defaults["texto"] = request.POST.get(f"custo_{custo_id}", "").strip()
                elif custo.tipo_campo == TipoCampo.FOTO:
                    arquivo = request.FILES.get(f"custo_{custo_id}")
                    if not arquivo:
                        continue
                    defaults["foto"] = arquivo
                OsCustoExtraUso.objects.update_or_create(os=os, custo=custo, defaults=defaults)
                salvos += 1
            if salvos:
                messages.success(request, "Custos extras registrados.")
            else:
                messages.error(request, "Nenhum custo extra válido para registrar.")
            return redirect("tecnico_detalhe_os", pk=os.pk)

        if acao == "excluir_custo_extra":
            if os.tipo != "INSTALACAO":
                raise PermissionDenied("Custos extras só se aplicam a OS de instalação.")
            OsCustoExtraUso.objects.filter(os=os, pk=request.POST.get("uso_id")).delete()
            messages.success(request, "Custo extra removido.")
            return redirect("tecnico_detalhe_os", pk=os.pk)

        if acao == "salvar_narrativa":
            narrativa_form = OsNarrativaForm(request.POST, instance=os)
            if narrativa_form.is_valid():
                narrativa_form.save()
                messages.success(request, "Informações do relatório salvas.")
            else:
                messages.error(request, "Verifique os campos do relatório.")
            return redirect("tecnico_detalhe_os", pk=os.pk)

        if acao == "dar_baixa":
            template = os.get_checklist_template()
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

            gerar_pdf_os(os)

            messages.success(request, "OS concluída e relatório PDF gerado com sucesso.")
            return redirect("tecnico_detalhe_os", pk=os.pk)

    materiais_usados = os.materiais_usados.select_related("material").all()
    custos_extras_usados = os.custos_extras.select_related("custo").all()
    context = {
        "os": os,
        "checklist": checklist_com_respostas(os),
        "narrativa_form": OsNarrativaForm(instance=os),
        "materiais_usados": materiais_usados,
        "materiais_disponiveis": MaterialCatalogo.objects.filter(ativo=True).exclude(
            id__in=materiais_usados.values_list("material_id", flat=True)
        ),
        "custos_extras_usados": custos_extras_usados,
        "custos_extras_disponiveis": CustoExtraCatalogo.objects.filter(ativo=True).exclude(
            id__in=custos_extras_usados.values_list("custo_id", flat=True)
        ),
    }
    return render(request, "tecnico/detalhe_os.html", context)
