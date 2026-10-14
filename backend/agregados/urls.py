from django.urls import path, re_path
from .views import health, dominios, pesquisas, metadados, periodos, localidades, validar, executar

urlpatterns = [
    path("consultas/executar/", executar, name="executar"),
    path("consultas/validar/", validar, name="validar"),
    re_path(r"^agregados/(?P<aggregate_id>[0-9]+)/periodos/$", periodos),
    re_path(r"^agregados/(?P<aggregate_id>[0-9]+)/localidades/$", localidades),
    path("health/", health, name="health"),
    path("dominios/", dominios, name="dominios"),
    path("pesquisas/", pesquisas, name="pesquisas"),
    re_path(r"^agregados/(?P<aggregate_id>[0-9]+)/metadados/$", metadados, name="metadados"),
]
