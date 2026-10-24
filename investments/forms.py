from decimal import Decimal

from django import forms

from dashboard.models import Share
from investments.models import PortfolioOperation, PriceAlert, Strategy
from investments.services.history import DEFAULT_PERIOD, PERIODS, to_decimal
from investments.services.portfolio import held_quantity

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


class OperationForm(forms.Form):
    side = forms.ChoiceField(label="Операция", choices=PortfolioOperation.SIDES)
    ticker = forms.CharField(label="Тикер", max_length=10)
    quantity = forms.IntegerField(label="Количество", min_value=1)
    price = forms.DecimalField(
        label="Цена", required=False, min_value=Decimal("0.000001"), max_digits=18,
        decimal_places=6, help_text="Пусто — текущая цена акции",
    )
    comment = forms.CharField(label="Комментарий", max_length=255, required=False)

    def __init__(self, *args, portfolio=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.portfolio = portfolio

    def clean_ticker(self):
        ticker = self.cleaned_data["ticker"].strip()
        share = Share.objects.filter(ticker__iexact=ticker).first()
        if share is None:
            raise forms.ValidationError(f"Акции с тикером {ticker} нет в справочнике")
        return share

    def clean(self):
        cleaned_data = super().clean()
        share = cleaned_data.get("ticker")
        quantity = cleaned_data.get("quantity")
        if share is None or quantity is None:
            return cleaned_data
        if cleaned_data.get("price") is None:
            if share.last_price is None:
                raise forms.ValidationError("Текущая цена акции неизвестна — укажите цену")
            cleaned_data["price"] = to_decimal(share.last_price)
        if cleaned_data["side"] == PortfolioOperation.SELL:
            held = held_quantity(self.portfolio, share)
            if quantity > held:
                raise forms.ValidationError(
                    f"Нельзя продать {quantity} {share.ticker}: в портфеле {held}"
                )
        return cleaned_data

    def save(self):
        data = self.cleaned_data
        return PortfolioOperation.objects.create(
            portfolio=self.portfolio, share=data["ticker"], side=data["side"],
            quantity=data["quantity"], price=data["price"], comment=data["comment"],
        )


class StrategyForm(forms.ModelForm):
    ticker = forms.CharField(label="Тикер", max_length=10)

    class Meta:
        model = Strategy
        fields = ["name", "buy_price", "sell_price", "stop_price", "quantity", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["ticker"].initial = self.instance.share.ticker

    def clean_ticker(self):
        ticker = self.cleaned_data["ticker"].strip()
        share = Share.objects.filter(ticker__iexact=ticker).first()
        if share is None:
            raise forms.ValidationError(f"Акции с тикером {ticker} нет в справочнике")
        # Set before model validation so Strategy.clean() sees a complete object
        self.instance.share = share
        return share
