from django.db import models


class Cliente(models.Model):
    nome = models.CharField("Nome", max_length=200)
    telefone = models.CharField("Telefone", max_length=30, blank=True)
    email = models.EmailField("E-mail", blank=True)
    endereco = models.CharField("Endereço", max_length=255, blank=True)
    cidade = models.CharField("Cidade", max_length=120, blank=True)
    criado_em = models.DateTimeField("Criado em", auto_now_add=True)

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["nome"]

    def __str__(self):
        return self.nome
