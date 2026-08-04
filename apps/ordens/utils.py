def checklist_com_respostas(os):
    template = os.get_checklist_template()
    if not template:
        return []
    itens = list(template.itens.all())
    respostas = {r.item_id: r for r in os.respostas_checklist.all()}
    linhas = []
    for item in itens:
        resposta = respostas.get(item.id)
        linhas.append(
            {
                "item": item,
                "marcado": resposta.marcado if resposta else False,
                "texto": resposta.texto if resposta else "",
                "foto": resposta.foto if resposta else None,
                "observacao": resposta.observacao if resposta else "",
            }
        )
    return linhas
