from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit


class PreviousClassificationForm(forms.Form):
    """
    Choose whether to use a previous class of start a new one

    """
    PREVIOUS_CLASS_CHOICES = (
        (True, 'Use previous'),
        (False, 'New classification'),
    )
    use_previous_class = forms.ChoiceField(choices=PREVIOUS_CLASS_CHOICES)
    confirm = forms.BooleanField(required=True, label='Confirm decision')

    def __init__(self, *args, **kwargs):
        super(PreviousClassificationForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        self.helper.add_input(
            Submit('submit', "Submit", css_class='btn btn-info w-100')
        )


class ResetPreviousClassificationsForm(forms.Form):
    """
    Form that users tick after they have checked patient paperwork to confirm referral is correct
    """
    confirm = forms.BooleanField(required=True, label="Confirm that you want to reopen and that any S-VIG analysis you've done so far will be wiped")
    reset_previous = forms.CharField(widget=forms.HiddenInput(), required=False)

    def __init__(self, *args, **kwargs):
        super(ResetPreviousClassificationsForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        self.helper.add_input(
            Submit('submit', 'Reopen', css_class='btn btn-danger w-100')
        )