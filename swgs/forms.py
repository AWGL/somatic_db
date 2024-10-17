from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

class DownloadCsvForm(forms.Form):
    """
    Download a csv of variants from SVD
    TEMPORARY FUNCTIONALITY FOR VALIDATION ONLY
    """

    def __init__(self, *args, **kwargs):
        super(DownloadCsvForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "POST"
        self.helper.add_input(
            Submit("submit", "Download CSV", css_class="btn btn-info w-100")
            )

class UpdatePanelNotesForm(forms.Form):
    """
    Update the notes for a panel
    """
    panel_notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 15}),
        required=False,
        label='Panel update notes:'
    )

    def __init__(self, *args, **kwargs):
        print(kwargs)
        self.panel_notes = kwargs.pop("panel_notes")

        super(UpdatePanelNotesForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "update-panel-notes-form"
        self.helper.form_method = "POST"
        self.fields["panel_notes"].initial = self.panel_notes
        self.helper.add_input(
            Submit("submit", "Submit", css_class="btn btn-info w-25")
        )