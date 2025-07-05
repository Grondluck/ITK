import uuid

from django.db import models
from django.core.validators import MinValueValidator

class Wallet(models.Model):
    id = models.UUIDField(primary_key=True, 
                          default=uuid.uuid4, 
                          editable=False
    )
    balance = models.DecimalField(default=0, max_digits=12, decimal_places=2, 
                                  validators=[MinValueValidator(0)]
    )