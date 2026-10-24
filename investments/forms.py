from django import forms

from dashboard.models import Share
from investments.models import PriceAlert
from investments.services.history import DEFAULT_PERIOD, PERIODS

DATE_INPUT = forms.DateInput(attrs={"type": "date"})


class HistoryPeriodForm(forms.Form):
    period = forms.ChoiceField(
        label="Период",
        choices=[(key, label) for key, (label, _) in PERIODS.items()],
        initial=DEFAULT_PERIOD,
        required=False,
    )
    date_from = forms.DateField(label="С", required=False, widget=DATE_INPUT)
    date_to = forms.DateField(label="По", required=False, widget=DATE_INPUT)

    def clean(self):
        cleaned_data = super().clean()
        date_from, date_to = cleaned_data.get("date_from"), cleaned_data.get("date_to")
        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError("Дата начала позже даты окончания")
        return cleaned_data


class NameForm(forms.Form):
    name = forms.CharField(label="Название", max_length=100)


class AddShareForm(forms.Form):
    ticker = forms.CharField(label="Тикер", max_length=10)

    def __init__(self, *args, watchlist=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.watchlist = watchlist

    def clean_ticker(self):
        ticker = self.cleaned_data["ticker"].strip()
        share = Share.objects.filter(ticker__iexact=ticker).first()
        if share is None:
            raise forms.ValidationError(f"Акции с тикером {ticker} нет в справочнике")
        if self.watchlist.items.filter(share=share).exists():
            raise forms.ValidationError(f"{share.ticker} уже есть в списке")
        return share


class PriceAlertForm(forms.ModelForm):
    class Meta:
        model = PriceAlert
        fields = ["condition", "target_price"]
