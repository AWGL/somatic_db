from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit
from crispy_forms.bootstrap import Field, FieldWithButtons, StrictButton


class UnassignForm(forms.Form):
    """
    Search bar for home page
    """
    unassign = forms.CharField(widget=forms.HiddenInput(), required=False)

    def __init__(self, *args, **kwargs):
        super(UnassignForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        self.helper.add_input(
            Submit('submit', "I'm sure", css_class='btn btn-danger w-100')
        )



class PolyForm(forms.Form):
    """

    """
    poly= forms.CharField(widget=forms.Textarea(attrs={'rows': 1}), required=False, label="")
    
    def __init__(self, *args, **kwargs):

        super(PolyForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()

        self.helper.add_input(Submit('submit', 'Submit', css_class='btn btn-success'))


class NewVariantForm(forms.Form):
    """
    """
    hgvs_g = forms.CharField(label='Genomic coordinates')
    hgvs_c = forms.CharField(label='HGVS c.')
    hgvs_p = forms.CharField(label='HGVS p.')
    gene = forms.CharField()
    exon = forms.CharField(required=False, label='Exon')
    alt_reads = forms.IntegerField(label='Number of reads supporting variant')
    total_reads = forms.IntegerField(label='Total depth')
    in_ntc = forms.BooleanField(required=False, label="Variant seen in NTC?")


    def __init__(self, *args, **kwargs):
        super(NewVariantForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'new-variant-form'
        self.fields['hgvs_g'].widget.attrs['placeholder'] = 'e.g. 7:140453136A>T'
        self.fields['hgvs_c'].widget.attrs['placeholder'] = 'e.g. NM_004333.4:c.1799T>A'
        self.fields['hgvs_p'].widget.attrs['placeholder'] = 'e.g. NP_004324.2:p.(Val600Glu)'
        self.fields['gene'].widget.attrs['placeholder'] = 'e.g. BRAF'
        self.fields['exon'].widget.attrs['placeholder'] = 'e.g. 15 | 18 (for exon 15 of 18)'
        self.helper.form_method = 'POST'
        self.helper.add_input(
            Submit('submit', 'Submit', css_class='btn btn-info w-25')
        )


class SubmitForm(forms.Form):
    """
    """
    NEXT_STEP_CHOICES = (
        ('Complete check', 'Complete check'),
        ('Request extra check', 'Request extra check'),
        ('Fail sample', 'Fail sample'),
    )
    next_step = forms.ChoiceField(choices=NEXT_STEP_CHOICES)
    confirm = forms.BooleanField(required=True, label="Confirm check is complete")


    def __init__(self, *args, **kwargs):
        super(SubmitForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        self.helper.add_input(
            Submit('submit', 'Submit', css_class='btn btn-info w-100')
        )


class SampleCommentForm(forms.Form):
    """
    """
    sample_comment = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False,
        label='General sample comments:'
    )
    patient_demographics = forms.BooleanField(required=False, label="Patient demographics checked")
    pk = forms.CharField(widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        self.comment = kwargs.pop('comment')
        self.info_check = kwargs.pop('info_check')
        self.pk = kwargs.pop('pk')

        super(SampleCommentForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.fields['sample_comment'].initial = self.comment
        self.fields['patient_demographics'].initial = self.info_check
        self.fields['pk'].initial = self.pk
        self.helper.add_input(Submit('submit', 'Update', css_class='btn btn-success'))



class VariantCommentForm(forms.Form):
    """

    """
    variant_comment = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False,
    )
    pk = forms.CharField(widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):

        self.comment = kwargs.pop('comment')
        self.pk = kwargs.pop('pk')

        super(VariantCommentForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.fields['variant_comment'].initial = self.comment
        self.fields['pk'].initial = self.pk
        self.helper.add_input(Submit('submit', 'Update', css_class='btn btn-success'))


class FusionCommentForm(forms.Form):
    """

    """
    hgvs = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 1}),
        required=False,
        label="HGVS"
    )
    fusion_comment = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False,
    )
    pk = forms.CharField(widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):

        self.comment = kwargs.pop('comment')
        self.hgvs = kwargs.pop('hgvs')
        self.pk = kwargs.pop('pk')

        super(FusionCommentForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.fields['fusion_comment'].initial = self.comment
        self.fields['hgvs'].initial = self.hgvs
        self.fields['pk'].initial = self.pk
        self.helper.add_input(Submit('submit', 'Update', css_class='btn btn-success'))


class UpdatePatientName(forms.Form):
    """
    """
    name = forms.CharField()

    def __init__(self, *args, **kwargs):
        super(UpdatePatientName, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.fields['name'].widget.attrs.update({
            'autocomplete': 'off'
        })
        self.helper.form_id = 'update-name-form'
        self.helper.form_method = 'POST'
        self.helper.add_input(
            Submit('submit', 'Submit', css_class='btn btn-info w-25')
        )


class CoverageCheckForm(forms.Form):
    """
    """
    ntc_checked = forms.BooleanField(required=False, label="NTC checked")
    coverage_comment = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
    )
    pk = forms.CharField(widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):

        self.comment = kwargs.pop('comment')
        self.ntc = kwargs.pop('ntc_check')
        self.pk = kwargs.pop('pk')

        super(CoverageCheckForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.fields['coverage_comment'].initial = self.comment
        self.fields['ntc_checked'].initial = self.ntc
        self.fields['pk'].initial = self.pk
        self.helper.add_input(Submit('submit', 'Update', css_class='btn btn-success'))
