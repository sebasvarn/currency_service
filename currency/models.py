from django.db import models

class Exchange(models.Model):
    CURRENCY_CHOICES = [
        ('USD', 'Dolar Americano'),
        ('EUR', 'Euro'),
        ('JPY', 'Yen Japones'),
        ('PYG', 'Guarani Paraguayo'),
        ("BRL", "Real Brasileño"),
        ("ARS", "Peso Argentino"),
    ]

    base_currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='PYG')
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES)
    buy = models.DecimalField(max_digits=15, decimal_places=6)
    sell = models.DecimalField(max_digits=15, decimal_places=6)
    source = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)


    class Meta:
        indexes = [
            models.Index(fields=['currency', '-timestamp']),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.currency}: buy {self.buy}, sell {self.sell} ({self.timestamp:%Y-%m-%d %H:%M:%S})"