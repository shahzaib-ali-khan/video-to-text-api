from django_filters import rest_framework as filters
from django_filters.fields import IsoDateTimeField

from transcriber.models import Transcription


class CustomDateFilter(filters.DateFilter):
    field_class = IsoDateTimeField

    def __init__(self, *args, **kwargs):
        # Accept multiple input formats. Supports both m-d-Y and ISO
        kwargs.setdefault(
            "input_formats",
            ["%d-%m-%Y"],
        )
        super().__init__(*args, **kwargs)


class TranscriptionFilter(filters.FilterSet):
    created_at_date__gte = CustomDateFilter(method="filter_by_created_at_date_gte")
    created_at__lte = CustomDateFilter(method="filter_by_created_at_date_lte")

    def filter_by_created_at_date_gte(self, queryset, name, value):
        return queryset.filter(created_at__date__gte=value)

    def filter_by_created_at_date_lte(self, queryset, name, value):
        return queryset.filter(created_at__date__lte=value)

    class Meta:
        model = Transcription
        fields = {
            "status": ["exact"],
            "created_at": ["gte", "lte"],
        }
