from django import forms

from .models import PriceAlert, Share, Watchlist


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
