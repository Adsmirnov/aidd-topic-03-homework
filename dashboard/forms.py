from django import forms

from .models import Portfolio, PortfolioTransaction, PriceAlert, Share, Watchlist


class ShareModelForm(forms.ModelForm):
    """Инструмент"""

    class Meta:
        model = Share
        fields = "__all__"


class WatchlistForm(forms.ModelForm):
    def __init__(self, *args, owner, **kwargs):
        self.owner = owner
        super().__init__(*args, **kwargs)

    class Meta:
        model = Watchlist
        fields = ("name",)

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        duplicate = Watchlist.objects.filter(owner=self.owner, name__iexact=name)
        if self.instance.pk:
            duplicate = duplicate.exclude(pk=self.instance.pk)
        if duplicate.exists():
            raise forms.ValidationError("У вас уже есть список с таким названием.")
        return name


class WatchlistEntryForm(forms.Form):
    share = forms.ModelChoiceField(queryset=Share.objects.none())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["share"].queryset = Share.objects.order_by("name")


class PriceAlertForm(forms.Form):
    direction = forms.ChoiceField(choices=PriceAlert.Direction.choices)
    target_price = forms.DecimalField(
        max_digits=20,
        decimal_places=8,
        min_value=0.00000001,
    )


class PortfolioForm(forms.ModelForm):
    class Meta:
        model = Portfolio
        fields = ("name",)


class PortfolioTransactionForm(forms.Form):
    share = forms.ModelChoiceField(queryset=Share.objects.none())
    side = forms.ChoiceField(choices=PortfolioTransaction.Side.choices)
    quantity = forms.DecimalField(max_digits=20, decimal_places=8, min_value=0.00000001)
    unit_price = forms.DecimalField(max_digits=20, decimal_places=8, min_value=0.00000001)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["share"].queryset = Share.objects.order_by("name")


class PriceHistoryFilterForm(forms.Form):
    share = forms.ModelChoiceField(queryset=Share.objects.none(), required=False)
    start_date = forms.DateField(
        required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    end_date = forms.DateField(
        required=False, widget=forms.DateInput(attrs={"type": "date"})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["share"].queryset = Share.objects.order_by("name")

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("Начало периода должно быть не позже его конца.")
        return cleaned_data
