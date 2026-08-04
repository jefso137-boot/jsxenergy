from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.checklists.models import TipoCampo
from apps.relatorios.pdf import gerar_pdf_os

from .decorators import tecnico_required
from .forms import OsMaterialUsoForm, OsNarrativaForm
from .models import OrdemServico, OsChecklistResposta, OsMaterialUso, StatusOS
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

        if acao == "add_material":
            material_form = OsMaterialUsoForm(request.POST)
            if material_form.is_valid():
                material_uso = material_form.save(commit=False)
                material_uso.os = os
                material_uso.save()
                messages.success(request, "Material registrado.")
            else:
                messages.error(request, "Não foi possível registrar o material.")
            return redirect("tecnico_detalhe_os", pk=os.pk)

        if acao == "excluir_material":
            OsMaterialUso.objects.filter(os=os, pk=request.POST.get("uso_id")).delete()
            messages.success(request, "Material removido.")
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

    context = {
        "os": os,
        "checklist": checklist_com_respostas(os),
        "narrativa_form": OsNarrativaForm(instance=os),
        "materiais_usados": os.materiais_usados.select_related("material").all(),
        "material_form": OsMaterialUsoForm(),
    }
    return render(request, "tecnico/detalhe_os.html", context)
