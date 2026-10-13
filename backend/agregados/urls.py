from django.urls import path, re_path
from .views import health, dominios, pesquisas, metadados

urlpatterns = [
    path("health/", health, name="health"),
    path("dominios/", dominios, name="dominios"),
    path("pesquisas/", pesquisas, name="pesquisas"),
    re_path(r"^agregados/(?P<aggregate_id>[0-9]+)/metadados/$", metadados, name="metadados"),
]
