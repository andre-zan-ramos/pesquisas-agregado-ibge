from django.urls import include, path

urlpatterns = [path("api/v1/agregados-ibge/", include("agregados.urls"))]
