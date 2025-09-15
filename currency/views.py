
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import Exchange
from .serializers import ExchangeSerializer
from django.utils.timezone import now, timedelta


@api_view(['GET'])
def latest_exchange_rates(request):

    base = request.GET.get('base', 'PYG')
    source = request.GET.get('source', None)


    latest = {}
    qs = Exchange.objects.filter(base_currency=base).order_by("currency", "-timestamp")
    if source:
        qs = qs.filter(source__icontains=source)

    for obj in qs:
        if obj.currency not in latest:
            latest[obj.currency] = obj

    data = ExchangeSerializer(latest.values(), many=True).data
    return Response(data)

@api_view(['GET'])
def currency_history(request, currency_code):

    days = int(request.GET.get('days', 7))
    source = request.GET.get('source', None)
    cutoff = now() - timedelta(days=days)

    qs = Exchange.objects.filter(currency=currency_code, timestamp__gte=cutoff).order_by("timestamp")
    if source:
        qs = qs.filter(source__icontains=source)
    return Response(ExchangeSerializer(qs, many=True).data)

@api_view(['GET'])
def sources_list(request):
    sources = Exchange.objects.values_list('source', flat=True).distinct()
    return Response(sources)

@api_view(["GET"])
def currency_latest(request, currency):
    obj = Exchange.objects.filter(currency=currency).order_by("-timestamp").first()
    if not obj:
        return Response({"error": "Moneda no encontrada"}, status=404)
    return Response(ExchangeSerializer(obj).data)