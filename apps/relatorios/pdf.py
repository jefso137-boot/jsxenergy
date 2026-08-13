import base64
import io
import logging
import mimetypes

import pillow_heif
from django.conf import settings
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.utils import timezone
from PIL import Image, ImageOps, UnidentifiedImageError
from weasyprint import HTML

from apps.checklists.models import TipoCampo

pillow_heif.register_heif_opener()

logger = logging.getLogger(__name__)

LOGO_PATH = settings.BASE_DIR / "static" / "images" / "jsx_energy_logo.jpeg"


def _foto_para_data_uri(campo_arquivo):
    """Decodifica a foto com Pillow (com suporte a HEIC das câmeras de iPhone) e
    reconverte para JPEG antes de embutir no PDF - o WeasyPrint não consegue
    renderizar HEIC diretamente, e confiar só na extensão do arquivo para o
    mime-type falha sempre que ela não bate com o conteúdo real. Retorna None
    se a foto estiver corrompida/ilegível, para essa foto não derrubar o
    relatório inteiro.
    """
    campo_arquivo.open("rb")
    try:
        conteudo = campo_arquivo.read()
    finally:
        campo_arquivo.close()

    try:
        imagem = Image.open(io.BytesIO(conteudo))
        imagem = ImageOps.exif_transpose(imagem)
        if imagem.mode not in ("RGB", "L"):
            imagem = imagem.convert("RGB")
        # Fotos de celular saem em 3000-4000px de lado, muito mais do que a página
        # do PDF exibe - reduzir aqui evita estourar tempo/memória do WeasyPrint
        # no plano free do Render ao gerar um relatório com várias fotos.
        imagem.thumbnail((1600, 1600), Image.LANCZOS)
        buffer = io.BytesIO()
        imagem.save(buffer, format="JPEG", quality=82)
    except (UnidentifiedImageError, OSError):
        logger.warning("Foto ilegível ao gerar PDF: %s", campo_arquivo.name)
        return None

    b64 = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


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

    for uso in ordem_servico.custos_extras.select_related("custo").prefetch_related("fotos"):
        if not uso.respondido():
            continue
        if uso.custo.tipo_campo == TipoCampo.FOTO:
            fotos_uso = list(uso.fotos.all())
            for indice, foto_uso in enumerate(fotos_uso, start=1):
                titulo = uso.custo.nome
                if len(fotos_uso) > 1:
                    titulo = f"{titulo} ({indice}/{len(fotos_uso)})"
                fotos.append(
                    {
                        "titulo_secao": titulo,
                        "legenda": "",
                        "data_uri": _foto_para_data_uri(foto_uso.foto),
                        "texto": "",
                    }
                )
        else:
            entrada = {"titulo_secao": uso.custo.nome, "legenda": "", "data_uri": None, "texto": ""}
            if uso.custo.tipo_campo == TipoCampo.TEXTO:
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


def os_referencia_recibo(cliente):
    """A OS de instalação concluída mais recente do cliente - fonte da data e da
    descrição do serviço que aparecem no recibo."""
    from apps.ordens.models import OrdemServico

    return (
        OrdemServico.objects.filter(cliente=cliente, tipo="INSTALACAO", status="CONCLUIDA")
        .order_by("-data_conclusao")
        .first()
    )


def montar_contexto_recibo(cliente):
    from collections import defaultdict

    from apps.financas.models import ConfiguracaoPreco
    from apps.ordens.models import OsCustoExtraUso

    precos = ConfiguracaoPreco.get_solo()
    os_referencia = os_referencia_recibo(cliente)

    servicos = []

    if cliente.quantidade_modulos:
        servicos.append(
            {
                "nome": "PAINÉL",
                "preco": precos.valor_placa,
                "quantidade": cliente.quantidade_modulos,
                "valor": cliente.quantidade_modulos * precos.valor_placa,
            }
        )

    if cliente.instalacao_padrao:
        servicos.append(
            {
                "nome": "PADRÃO CONVENCIONAL",
                "preco": precos.valor_padrao,
                "quantidade": 1,
                "valor": precos.valor_padrao,
            }
        )

    # Agrupa por custo usando subtotal() (não uma soma/multiplicação manual aqui) para
    # respeitar corretamente custos por m² (quantidade × área da placa × valor) e
    # valor_manual - duplicar essa conta aqui já causou o recibo cobrar só
    # quantidade × valor, ignorando a área, para custos como a impermeabilização.
    usos_extras = (
        OsCustoExtraUso.objects.filter(os__cliente=cliente)
        .select_related("custo")
        .order_by("custo__nome")
    )
    agrupado = defaultdict(lambda: {"preco": None, "quantidade": 0, "valor": 0})
    for uso in usos_extras:
        grupo = agrupado[uso.custo.nome]
        grupo["preco"] = uso.custo.valor
        grupo["quantidade"] += uso.quantidade
        grupo["valor"] += uso.subtotal()

    for nome, dados in agrupado.items():
        servicos.append(
            {
                "nome": nome.upper(),
                "preco": dados["preco"],
                "quantidade": dados["quantidade"],
                "valor": dados["valor"],
            }
        )

    valor_materiais = cliente.valor_materiais_usados()
    if valor_materiais:
        servicos.append({"nome": "MATERIAL C.A", "preco": None, "quantidade": None, "valor": valor_materiais})

    total = sum((s["valor"] for s in servicos), start=0)

    return {
        "recibo_info": settings.JSX_ENERGY_RECIBO,
        "empresa_cliente": cliente.criado_por.nome_empresa_recibo if cliente.criado_por else "",
        "data_servico": (
            timezone.localtime(os_referencia.data_conclusao).strftime("%d/%m/%Y") if os_referencia else ""
        ),
        "cliente": cliente,
        "descricao": os_referencia.descricao_recibo if os_referencia else "",
        "servicos": servicos,
        "total": total,
        "logo_data_uri": _logo_data_uri(),
    }


def gerar_recibo_pdf_bytes(cliente):
    """Gera o PDF do recibo do cliente (WeasyPrint) e retorna os bytes, sem persistir em disco."""
    contexto = montar_contexto_recibo(cliente)
    html_string = render_to_string("relatorios/recibo_cliente.html", contexto)
    return HTML(string=html_string).write_pdf()
