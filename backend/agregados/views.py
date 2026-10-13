from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["GET"])
def health(request):
    # Liveness local; não consulta IBGE nem banco.
    return Response({"status": "ok", "service": "agregados-ibge", "phase": 1})
