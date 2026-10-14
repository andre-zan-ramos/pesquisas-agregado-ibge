from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import CatalogSerializer, DomainsSerializer, MetadataSerializer, DiscoverySerializer, query_params
from .services.catalogo import CatalogService
from .services.consultas import QueryService
from .serializers import LocalityQuerySerializer


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


@api_view(["GET"])
def periodos(request, aggregate_id):
    query_params(request)
    service = QueryService()
    return Response(service.envelope(service.periods(aggregate_id)))


@api_view(["GET"])
def localidades(request, aggregate_id):
    params = query_params(request, LocalityQuerySerializer)
    service = QueryService()
    return Response(service.envelope(service.locations(aggregate_id, params)))


@api_view(["POST"])
def validar(request):
    query_params(request)
    service = QueryService()
    return Response(service.envelope(service.validate(request.data)))


@api_view(["POST"])
def executar(request):
    query_params(request)
    service = QueryService()
    return Response(service.envelope(service.execute(request.data)))
