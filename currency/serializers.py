from rest_framework import serializers
from .models import Exchange

class ExchangeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exchange
        fields = ['base_currency', 'currency', 'buy', 'sell', 'source', 'timestamp']
        read_only_fields = ['id', 'timestamp']