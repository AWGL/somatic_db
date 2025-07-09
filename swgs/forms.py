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
        self.panel_notes = kwargs.pop("panel_notes")

        super(UpdatePanelNotesForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "update-panel-notes-form"
        self.helper.form_method = "POST"
        self.fields["panel_notes"].initial = self.panel_notes
        self.helper.add_input(
            Submit("submit", "Submit", css_class="btn btn-info w-25")
        )

class UpdateMDTNotesForm(forms.Form):
    """
    Add MDT notes
    """
    mdt_notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 15}),
        required=False,
        label='MDT notes:'
    )
    mdt_date = forms.DateField(
        widget=forms.TextInput(     
            attrs={'type': 'date'} 
        )
    )
    
    def __init__(self, *args, **kwargs):
        super(UpdateMDTNotesForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "update-mdt-notes-form"
        self.helper.form_method = "POST"
        self.helper.add_input(
            Submit("submit", "Submit", css_class="btn btn-info w-25")
        )

class AbstractCheckForm(forms.Form):
    """
    Base form for completing a check
    """

    complete = forms.BooleanField(required=True, initial=False)
    comment = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False
    )

    def __init__(self, *args, **kwargs):
        super(AbstractCheckForm, self).__init__(*args, **kwargs)
        self.fields["complete"].label = "This check is complete"
        self.helper = FormHelper()
        self.helper.form_method = "POST"
        self.helper.add_input(Submit("submit","Submit", css_class="btn-success"))

class QCCheckForm(AbstractCheckForm):
    """
    Form to say that QC checks are complete
    """

    qc_check = forms.CharField(widget=forms.HiddenInput(), required=False)

class CoverageCheckForm(AbstractCheckForm):
    """
    Form to say that coverage checks are complete
    """

    coverage_check = forms.CharField(widget=forms.HiddenInput(), required=False)

class GeneralCommentForm(forms.Form):
    """
    Form for a generic comment to attach to a patient analysis
    """
    
    comment = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False
    )

    def __init__(self, *args, **kwargs):
        super(GeneralCommentForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "POST"
        self.helper.add_input(Submit("submit","Submit", css_class="btn-success"))