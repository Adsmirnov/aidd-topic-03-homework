from django import forms

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
