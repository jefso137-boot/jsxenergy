from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    class Papel(models.TextChoices):
        ADMIN = "admin", "Administrativo"
        LIDER = "lider", "Líder de equipe"
        TECNICO = "tecnico", "Técnico de campo"

    role = models.CharField(max_length=10, choices=Papel.choices, default=Papel.TECNICO)

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
