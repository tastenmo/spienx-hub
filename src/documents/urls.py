from django.urls import path
from .views import DocumentListCreateView, DocumentDetailView, BuildListCreateView, BuildDetailView


urlpatterns = [
    path('documents/', DocumentListCreateView.as_view(), name='document-list-create'),
    path('documents/<int:pk>/', DocumentDetailView.as_view(), name='document-detail'),
    path('builds/', BuildListCreateView.as_view(), name='build-list-create'),
    path('builds/<int:pk>/', BuildDetailView.as_view(), name='build-detail'),
]
