"""Entrada de descoberta; não recebe expressões livres do upstream."""
from rest_framework import serializers


class ItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    nome = serializers.CharField()


class DomainsSerializer(serializers.Serializer):
    assuntos = ItemSerializer(many=True)
    niveis = ItemSerializer(many=True)
    periodos = ItemSerializer(many=True)


class ResearchSerializer(ItemSerializer):
    agregados = ItemSerializer(many=True)


class PaginationSerializer(serializers.Serializer):
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total_count = serializers.IntegerField()
    has_next = serializers.BooleanField()


class CatalogSerializer(serializers.Serializer):
    items = ResearchSerializer(many=True)
    pagination = PaginationSerializer()


class LevelSerializer(ItemSerializer):
    nome = serializers.CharField(allow_null=True)
    grupo = serializers.CharField()


class VariableSerializer(ItemSerializer):
    unidade = serializers.CharField(allow_null=True)
    sumarizacao = serializers.ListField(child=serializers.CharField())


class CategorySerializer(ItemSerializer):
    unidade = serializers.CharField(allow_null=True)
    nivel = serializers.IntegerField(allow_null=True)


class SummarySerializer(serializers.Serializer):
    status = serializers.BooleanField()
    excecao = serializers.ListField(child=serializers.CharField())


class ClassificationSerializer(ItemSerializer):
    sumarizacao = SummarySerializer()
    categorias = CategorySerializer(many=True)


class PeriodSerializer(serializers.Serializer):
    id = serializers.CharField()
    literals = serializers.ListField(child=serializers.CharField())
    modificacao = serializers.CharField(allow_null=True)
    ordem = serializers.IntegerField()


class PeriodicitySerializer(serializers.Serializer):
    frequencia = serializers.CharField()
    inicio = serializers.CharField()
    fim = serializers.CharField()


class MetadataSerializer(ItemSerializer):
    sidra_url = serializers.CharField()
    pesquisa = serializers.CharField()
    assunto = serializers.CharField()
    periodicidade = PeriodicitySerializer()
    niveis = LevelSerializer(many=True)
    variaveis = VariableSerializer(many=True)
    classificacoes = ClassificationSerializer(many=True)
    periodos = PeriodSerializer(many=True)


class DiscoverySerializer(serializers.Serializer):
    assunto = serializers.CharField(required=False, max_length=128, trim_whitespace=False)
    nivel = serializers.RegexField(r"^N[0-9]+$", required=False)
    periodo = serializers.CharField(required=False, max_length=128, trim_whitespace=False)
    q = serializers.CharField(required=False, max_length=200, allow_blank=True)
    page = serializers.IntegerField(required=False, default=1, min_value=1, max_value=1000000)
    page_size = serializers.IntegerField(required=False, default=50, min_value=1, max_value=200)


class LocalityQuerySerializer(serializers.Serializer):
    nivel = serializers.RegexField(r"^N[0-9]+$", trim_whitespace=False)
    q = serializers.CharField(required=False, max_length=200, allow_blank=True)
    page = serializers.IntegerField(required=False, default=1, min_value=1, max_value=1000000)
    page_size = serializers.IntegerField(required=False, default=50, min_value=1, max_value=200)


def query_params(request, serializer_class=None):
    allowed = set(serializer_class().fields) if serializer_class else set()
    if set(request.query_params) - allowed or any(len(request.query_params.getlist(k)) != 1 for k in request.query_params):
        raise serializers.ValidationError("Parâmetros desconhecidos ou repetidos.")
    if not serializer_class:
        return {}
    serializer = serializer_class(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data
