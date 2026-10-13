from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import CatalogSerializer, DomainsSerializer, MetadataSerializer, DiscoverySerializer, query_params
from .services.catalogo import CatalogService


@api_view(["GET"])
def health(request):
    # Liveness local; não consulta IBGE nem banco.
    return Response({"status": "ok", "service": "agregados-ibge", "phase": 1})


@api_view(["GET"])
def dominios(request):
    query_params(request)
    service = CatalogService()
    return Response(service.envelope(DomainsSerializer(service.domains()).data))


@api_view(["GET"])
def pesquisas(request):
    params = query_params(request, DiscoverySerializer)
    service = CatalogService()
    return Response(service.envelope(CatalogSerializer(service.researches(params)).data))


@api_view(["GET"])
def metadados(request, aggregate_id):
    query_params(request)
    service = CatalogService()
    return Response(service.envelope(MetadataSerializer(service.metadata(aggregate_id)).data))
