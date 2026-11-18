# network/forms.py
# Partnership request form.

from django import forms


class PartnershipRequestForm(forms.Form):
    message = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        max_length=500,
        required=False,
        label="Short message",
    )
    