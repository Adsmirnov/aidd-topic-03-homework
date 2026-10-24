from django_filters import rest_framework as filters
from rest_framework import permissions, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter

from dashboard.models import Share

from .serializer import ShareSerializer


class ShareFilter(filters.FilterSet):
    class Meta:
        model = Share
        fields = ("name", "ticker")


class RegexSearchFilter(SearchFilter):
    """Regex search that answers 400 instead of 500 on an invalid expression."""

    def filter_queryset(self, request, queryset, view):
        queryset = super().filter_queryset(request, queryset, view)
        if self.get_search_terms(request):
            try:
                # Evaluate here: PostgreSQL validates the expression on execution
                queryset.exists()
            except Exception:
                raise ValidationError({"search": "Некорректное регулярное выражение"})
        return queryset


class ShareViewSet(viewsets.ModelViewSet):
    serializer_class = ShareSerializer
    queryset = Share.objects.all()
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    filter_backends = (OrderingFilter, filters.DjangoFilterBackend, RegexSearchFilter)
    filterset_class = ShareFilter
    ordering_fields = ["name", "ticker"]
    search_fields = ["$name"]
