from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    class Papel(models.TextChoices):
        ADMIN = "admin", "Administrativo"
        LIDER = "lider", "Líder de equipe"
        TECNICO = "tecnico", "Técnico de campo"

    role = models.CharField(max_length=10, choices=Papel.choices, default=Papel.TECNICO)
    nome_empresa_recibo = models.CharField(
        "Empresa (aparece no recibo)",
        max_length=150,
        blank=True,
        help_text=(
            "Nome que aparece como \"Cliente\" no cabeçalho dos recibos gerados para os "
            "clientes cadastrados por este líder. Ex.: RED SOLAR."
        ),
    )

    @property
    def is_admin_jsx(self):
        return self.role == self.Papel.ADMIN

    @property
    def is_lider(self):
        return self.role == self.Papel.LIDER

    @property
    def is_tecnico(self):
        return self.role == self.Papel.TECNICO

    def __str__(self):
        return self.get_full_name() or self.username
