import base64
import mimetypes

from django.conf import settings
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.utils import timezone
from weasyprint import HTML

from apps.checklists.models import TipoCampo

LOGO_PATH = settings.BASE_DIR / "static" / "images" / "jsx_energy_logo.jpeg"


def _foto_para_data_uri(campo_arquivo):
    campo_arquivo.open("rb")
    try:
        conteudo = campo_arquivo.read()
    finally:
        campo_arquivo.close()
    mime, _ = mimetypes.guess_type(campo_arquivo.name)
    mime = mime or "image/jpeg"
    b64 = base64.b64encode(conteudo).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _logo_data_uri():
    if not LOGO_PATH.exists():
        return None
    conteudo = LOGO_PATH.read_bytes()
    mime, _ = mimetypes.guess_type(str(LOGO_PATH))
    mime = mime or "image/jpeg"
    b64 = base64.b64encode(conteudo).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _montar_paragrafos(texto):
    if not texto:
        return []
    blocos = [b.strip() for b in texto.split("\n\n")]
    return [b for b in blocos if b]


def _montar_bullets(texto):
    if not texto:
        return []
    linhas = [linha.strip() for linha in texto.splitlines()]
    return [linha for linha in linhas if linha]


def montar_contexto(ordem_servico):
    fotos = []
    template = ordem_servico.get_checklist_template()
    if template:
        respostas = {r.item_id: r for r in ordem_servico.respostas_checklist.all()}
        for item in template.itens.filter(tipo_campo=TipoCampo.FOTO):
            resposta = respostas.get(item.id)
            if resposta and resposta.foto:
                fotos.append(
                    {
                        "titulo_secao": item.descricao,
                        "legenda": resposta.observacao,
                        "data_uri": _foto_para_data_uri(resposta.foto),
                    }
                )

    for uso in ordem_servico.custos_extras.select_related("custo"):
        if not uso.respondido():
            continue
        entrada = {"titulo_secao": uso.custo.nome, "legenda": "", "data_uri": None, "texto": ""}
        if uso.custo.tipo_campo == TipoCampo.FOTO:
            entrada["data_uri"] = _foto_para_data_uri(uso.foto)
        elif uso.custo.tipo_campo == TipoCampo.TEXTO:
            entrada["texto"] = uso.texto
        fotos.append(entrada)

    data_relatorio = ordem_servico.data_conclusao or timezone.now()

    return {
        "titulo_pdf": ordem_servico.titulo_pdf,
        "status_page_titulo_pdf": ordem_servico.status_page_titulo_pdf,
        "photo_header_line1_pdf": ordem_servico.photo_header_line1_pdf,
        "cliente_nome": ordem_servico.cliente.nome,
        "report_date": timezone.localtime(data_relatorio).strftime("%d/%m/%Y"),
        "status_pill_text": ordem_servico.status_pill_text,
        "cover_footnote": ordem_servico.cover_footnote,
        "narrativa_paragrafos": _montar_paragrafos(ordem_servico.narrativa_paragrafos),
        "resumo_bullets": _montar_bullets(ordem_servico.resumo_tecnico_bullets),
        "fotos": fotos,
        "logo_data_uri": _logo_data_uri(),
    }


def gerar_pdf_os(ordem_servico):
    """Gera o PDF do relatório da OS (WeasyPrint) e salva em ordem_servico.pdf_file."""
    contexto = montar_contexto(ordem_servico)
    html_string = render_to_string("relatorios/relatorio_os.html", contexto)
    pdf_bytes = HTML(string=html_string).write_pdf()

    nome_arquivo = f"OS-{ordem_servico.pk}-{ordem_servico.cliente.nome}".replace(" ", "_")
    ordem_servico.pdf_file.save(f"{nome_arquivo}.pdf", ContentFile(pdf_bytes), save=True)
    return ordem_servico.pdf_file
