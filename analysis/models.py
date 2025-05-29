from django.contrib.auth.models import User
from django.db import models, transaction
from django.template.loader import render_to_string
from django.utils import timezone

from auditlog.registry import auditlog

import decimal
import json
import re


class UserSettings(models.Model):
    """
    Extend the user model for specific settings

    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    lims_initials = models.CharField(max_length=10)


class Run(models.Model):
    """
    A sequencing run

    """
    run_id = models.CharField(max_length=50, primary_key=True)

    def __str__(self):
        return self.run_id


class Worksheet(models.Model):
    """
    An NGS worksheet, sometimes 1 run == 1 worksheet, sometimes there are multiple ws per run

    """
    QC_CHOICES = (
        ('-', 'Pending'),
        ('P', 'AutoQC run pass'),
        ('F', 'AutoQC run fail'),
    )
    ws_id = models.CharField(max_length=50, primary_key=True)
    run = models.ForeignKey('Run', on_delete=models.CASCADE)
    assay = models.CharField(max_length=50)
    diagnostic = models.BooleanField(default=True)
    upload_time = models.DateTimeField(blank=True, null=True)
    signed_off = models.BooleanField(default=False) # will need to swap to true for migrations
    signed_off_time = models.DateTimeField(blank=True, null=True)
    signed_off_user = models.ForeignKey('auth.User', on_delete=models.PROTECT, blank=True, null=True)
    auto_qc_pass_fail = models.CharField(max_length=1, choices=QC_CHOICES, default='-') # will need to change to P for migrations
    auto_qc_pk = models.IntegerField(blank=True, null=True, unique=True)

    def __str__(self):
        return self.ws_id

    def qc_signoff(self, signed_off, signed_off_time, signed_off_user, pass_fail, auto_qc_pk):
        """ signoff worksheet QC """
        self.signed_off = signed_off
        self.signed_off_time = signed_off_time
        self.signed_off_user = signed_off_user
        self.auto_qc_pass_fail = pass_fail
        self.auto_qc_pk = auto_qc_pk
        self.save()

    def reset_qc_signoff(self):
        """ reset worksheet QC """
        self.qc_signoff(False, None, None, '-', None)

    def get_status(self):
        """ get overall worksheet status """
        if self.auto_qc_pass_fail == '-':
            return 'Bioinformatics QC'
        if self.auto_qc_pass_fail == 'F':
            return 'Fail'
        samples = SampleAnalysis.objects.filter(worksheet = self)
        for s in samples:
            if s.sample_pass_fail == '-':
                return 'IGV checking'
        return 'Complete'

    def get_samples(self):
        """ get all sample analysis objects """
        samples = SampleAnalysis.objects.filter(worksheet = self)
        sample_list = [i.sample.sample_id for i in samples]
        return sample_list


class Sample(models.Model):
    """
    An individual sample

    """
    sample_id = models.CharField(max_length=50, primary_key=True)

    def get_worksheets(self):
        """ get all worksheets that the sample appears on """
        sample_analyses = SampleAnalysis.objects.filter(sample=self)
        worksheets = []
        for s in sample_analyses:
            if s.worksheet.signed_off:
                if s.worksheet not in worksheets:
                    worksheets.append(s.worksheet)
        return worksheets


def make_bedfile_path(instance, filename):
    """
    Function to generate filepath when adding bed file to Panel model below
    """
    filepath = '/'.join([
        'roi',
        f'b{instance.genome_build}',
        instance.get_assay_display().replace(' ', '_'),
        f'{instance.panel_name}_variants_b{instance.genome_build}_v{instance.version}.bed'
    ])
    return filepath


class Panel(models.Model):
    """
    A virtual panel. 
    Contains all the information needed to apply a panel and display the required types of variants

    """
    ASSAY_CHOICES = (
        ('1', 'TSO500 DNA'),
        ('2', 'TSO500 RNA'),
        ('3', 'TSO500 ctDNA'),
        ('4', 'GeneRead CRM'),
        ('5', 'GeneRead BRCA'),
    )
    panel_name = models.CharField(max_length=50)
    pretty_print = models.CharField(max_length=100)
    version = models.IntegerField()
    live = models.BooleanField()
    assay = models.CharField(max_length=1, choices=ASSAY_CHOICES)
    genome_build = models.IntegerField(default=37)
    lims_test_code = models.CharField(max_length=30)

    # snv settings
    show_snvs = models.BooleanField()
    show_myeloid_gaps_summary = models.BooleanField(default=False)
    depth_cutoffs = models.CharField(max_length=50, blank=True, null=True) # either 135,270, 500 or 1000, comma seperated, no spaces
    vaf_cutoff = models.DecimalField(decimal_places=5, max_digits=10, blank=True, null=True) # formatted as e.g. 1.4%, not 0.014
    manual_review_required = models.BooleanField(default=False)
    manual_review_desc = models.CharField(max_length=200, blank=True, null=True) # pipe seperated, no spaces
    bed_file = models.FileField(upload_to=make_bedfile_path, blank=True, null=True)
    report_snv_vaf = models.BooleanField(default=False)

    # fusion settings
    show_fusions = models.BooleanField()
    show_fusion_coverage = models.BooleanField()
    fusion_genes = models.CharField(max_length=100, blank=True, null=True) # comma seperated, no spaces
    splice_genes = models.CharField(max_length=100, blank=True, null=True) # comma seperated, no spaces
    show_fusion_vaf = models.BooleanField()

    class Meta:
        unique_together = ('panel_name', 'version', 'assay', 'genome_build')

    def __str__(self):
        return f'{self.pretty_print} (v{self.version})'


class SampleAnalysis(models.Model):
    """
    An analysis of a sample, if there are multiple analyses (e.g. multiple panels), 
    then there will be multiple sample analysis objects

    """
    QC_CHOICES = (
        ('-', 'Pending'),
        ('C', 'Complete'),
        ('F', 'Analysis fail'),
        ('Q', 'Bioinformatics QC fail'),
    )
    worksheet = models.ForeignKey('Worksheet', on_delete=models.CASCADE)
    sample = models.ForeignKey('Sample', on_delete=models.CASCADE)
    panel = models.ForeignKey('Panel', on_delete=models.CASCADE)
    paperwork_check = models.BooleanField(default=False)
    total_reads = models.IntegerField(blank=True, null=True)
    total_reads_ntc = models.IntegerField(blank=True, null=True)
    genome_build = models.IntegerField(default=37)
    upload_time = models.DateTimeField(blank=True, null=True)
    sample_pass_fail = models.CharField(max_length=1, default='-', choices=QC_CHOICES)

    def percent_reads_ntc(self):
        """
        Calculate percent NTC from the total reads in the sample and NTC
        """
        if self.total_reads == None or self.total_reads_ntc == None:
            perc_ntc = None
        elif self.total_reads == 0:
            perc_ntc = 100
        elif self.total_reads_ntc == 0:
            perc_ntc = 0
        else:
            perc_ntc_full = decimal.Decimal(self.total_reads_ntc / self.total_reads) * 100
            perc_ntc = perc_ntc_full.quantize(decimal.Decimal('.01'), rounding = decimal.ROUND_UP)
        return perc_ntc

    def all_checks(self):
        return Check.objects.filter(analysis=self).order_by('pk')

    def current_check(self):
        all_checks_reversed = self.all_checks().order_by('-pk')
        return all_checks_reversed[0]

    def previous_check(self):
        all_checks_reversed = self.all_checks().order_by('-pk')
        if len(all_checks_reversed) > 1:
            return all_checks_reversed[1]
        else:
            return None

    def concatenate_lims_initials(self):
        lims_checks = []
        for c in self.all_checks():
            if c.user:
                lims_initials = c.user.usersettings.lims_initials
                if lims_initials not in lims_checks:
                    lims_checks.append(lims_initials)
        return ','.join(lims_checks)

    def get_status(self):
        """return current status of sample"""
        # sample_pass_fail is set when analysis is complete, so use that value if its set
        if self.worksheet.auto_qc_pass_fail == 'F':
            return 'Bioinformatics QC fail'
        # will display pretty printed version from qc_choices tuples
        elif self.sample_pass_fail != '-':
            return self.get_sample_pass_fail_display()
        # if worksheet pass/fail isnt set then sample is still in bioinformatics QC
        elif self.worksheet.auto_qc_pass_fail == '-':
            num_checks = Check.objects.filter(analysis = self).count()
            return f'Bioinformatics QC {num_checks}'
        # otherwise the status is IGV checking, use total num checks to get the check number
        else:
            num_checks = Check.objects.filter(analysis = self).count()
            return f'IGV check {num_checks}'

    def get_checks(self):
        """ get all associated checks and work out the status """
        return {
            'assigned_to': self.current_check().user,
            'current_check_object': self.current_check(),
            'previous_check_object': self.previous_check(),
            'all_checks': self.all_checks(),
            'lims_checks': self.concatenate_lims_initials(),
        }

    def all_panel_snvs(self):
        return VariantPanelAnalysis.objects.filter(sample_analysis=self).order_by('pk')

    def all_panel_fusions(self):
        return FusionPanelAnalysis.objects.filter(sample_analysis=self)

    def has_two_checks(self, variant_type):
        """ make sure each variant/ fusion has at least 2 checks """
        # load variant objects
        if variant_type == "SNV":
            all_vars = self.all_panel_snvs()
        elif variant_type == "Fusion":
            all_vars = self.all_panel_fusions()
        else:
            raise ValueError("Variant type should be either SNV or Fusion")

        # loop through each variant and peform checks, add any errors to list to return at the end
        error_list = []
        for v in all_vars:
            all_var_checks = v.get_all_checks()
            all_var_checks_excluding_na = all_var_checks.exclude(decision='N')

            # must be at least 2 variant checks
            if all_var_checks.count() < 2:
                if variant_type == "SNV":
                    error_list.append(v.variant_instance.variant.variant)
                elif variant_type == "Fusion":
                    error_list.append(v.fusion_instance.fusion_genes.fusion_genes)
            # if both checks are 'not analysed' then thats fine
            elif all_var_checks_excluding_na.count() == 0:
                pass

            # where theres a mixture of analysed/not analysed, there must be at least 2 checks after excluding any 'not analysed'
            elif all_var_checks_excluding_na.count() < 2:
                if variant_type == "SNV":
                    error_list.append(v.variant_instance.variant.variant)
                elif variant_type == "Fusion":
                    error_list.append(v.fusion_instance.fusion_genes.fusion_genes)

        # throw error if any variants fail checks
        if len(error_list) > 0:
            pass_fail = False
            if variant_type == "SNV":
                message = 'Not all SNV/ indels have been checked at least twice: ' + ', '.join(error_list)
            elif variant_type == "Fusion":
                message = 'Not all fusions have been checked at least twice: ' + ', '.join(error_list)
        else:
            pass_fail = True
            message = ''

        return pass_fail, message

    def checks_agree(self, variant_type):
        """ make sure last 2 checks for each variant agree """
        # load variant objects
        if variant_type == "SNV":
            all_vars = self.all_panel_snvs()
        elif variant_type == "Fusion":
            all_vars = self.all_panel_fusions()
        else:
            raise ValueError("Variant type should be either SNV or Fusion")

        # loop through each variant and peform checks, add any errors to list to return at the end
        error_list = []
        for v in all_vars:
            all_var_checks_excluding_na = v.get_all_checks().exclude(decision='N').order_by('-pk')
            if all_var_checks_excluding_na.count() >= 2:

                last_two = [c.decision for c in all_var_checks_excluding_na][0:2]
                if len(set(last_two)) != 1:
                    if variant_type == "SNV":
                        error_list.append(v.variant_instance.variant.variant)
                    elif variant_type == "Fusion":
                        error_list.append(v.fusion_instance.fusion_genes.fusion_genes)

        # throw error if any variants fail checks
        if len(error_list) > 0:
            pass_fail = False
            if variant_type == "SNV":
                message = "Last checkers don't agree for SNV/ indels: " + ", ".join(error_list)
            elif variant_type == "Fusion":
                message = "Last checkers don't agree for fusions: " + ", ".join(error_list)
        else:
            pass_fail = True
            message = ''

        return pass_fail, message

    def finalise_checks(self, selection):
        """ verify if a sample analysis can be closed """

        error_list = []
        all_checks = self.get_checks()

        # at least two checks required
        if len(all_checks['all_checks']) < 2:
            error_list.append("There haven't been at least two checks for this sample")

        # only check these if the above checks are okay
        else:

            # pass/fail of last two checks agrees
            previous_pass_fail = all_checks['previous_check_object'].get_status_display()
            if (selection == 'next_step_pass') and (previous_pass_fail != 'Complete'):
                error_list.append("Overall pass/ fail of previous two checks doesn't match")
            elif (selection == 'next_step_fail') and (previous_pass_fail != 'Analysis fail'):
                error_list.append("Overall pass/ fail of previous two checks doesn't match")

            # only run variant checks when analysis is a pass
            if selection == 'next_step_pass':
                # at least two variant checks for each snv
                status, err = self.has_two_checks("SNV")
                if status == False:
                    error_list.append(err)

                # lastest two snv checks agree
                status, err = self.checks_agree("SNV")
                if status == False:
                    error_list.append(err)

                # at least two checks for each fusion
                status, err = self.has_two_checks("Fusion")
                if status == False:
                    error_list.append(err)

                # lastest two fusion checks agree
                status, err = self.checks_agree("Fusion")
                if status == False:
                    error_list.append(err)

        # select template based on whether there were any errors
        if len(error_list) == 0:
            pass_fail = True
            template = f'analysis/forms/ajax_finalise_form_check_3_pass.html'
        else:
            pass_fail = False
            template = f'analysis/forms/ajax_finalise_form_check_3_fail.html'

        # render HTML for AJAX form
        html = render_to_string(template, {'errors': error_list})

        return pass_fail, html

    @transaction.atomic
    def finalise(self, pass_fail):
        """ closes a case and sets final decision for all snvs/fusions """
        # skip this if a QC fail
        if pass_fail != 'Q':
            # calculate final decison for all snvs and commit to database
            if self.panel.show_snvs:
                for v in self.all_panel_snvs():
                    final_decision = v.calculate_final_decision(pass_fail)
                    v.variant_instance.final_decision = final_decision
                    v.variant_instance.save()

            # calculate final decison for all fusions and commit to database
            if self.panel.show_fusions:
                for v in self.all_panel_fusions():
                    final_decision = v.calculate_final_decision(pass_fail)
                    v.fusion_instance.final_decision = final_decision
                    v.fusion_instance.save()

        # sample pass/fail
        self.sample_pass_fail = pass_fail
        self.save()

        return True

    @transaction.atomic
    def make_next_check(self):
        """ sets up the next check and associated variant checks """
        # add new check object
        new_check_obj = Check(
            analysis=self,
            status='-',
        )
        new_check_obj.save()

        # make check objects for all variants
        if self.panel.show_snvs:
            for v in self.all_panel_snvs():
                new_variant_check = VariantCheck(
                    variant_analysis = v,
                    check_object = new_check_obj,
                )
                new_variant_check.save()

        # make check objects for all fusions
        if self.panel.show_fusions:
            for f in self.all_panel_fusions():
                new_variant_check = FusionCheck(
                    fusion_analysis = f,
                    check_object = new_check_obj,
                )
                new_variant_check.save()

        return True


class Check(models.Model):
    """
    Model to store 1st, 2nd check etc

    """
    STATUS_CHOICES = (
        ('-', 'Pending'),
        ('C', 'Complete'),
        ('F', 'Analysis fail'),
        ('Q', 'Bioinformatics QC fail'),
    )
    analysis = models.ForeignKey('SampleAnalysis', on_delete=models.CASCADE)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES)
    user = models.ForeignKey('auth.User', on_delete=models.PROTECT, blank=True, null=True)
    coverage_ntc_check = models.BooleanField(default=False)
    coverage_comment = models.CharField(max_length=500, blank=True)
    coverage_comment_updated = models.DateTimeField(blank=True, null=True)
    patient_info_check = models.BooleanField(default=False)
    manual_review_check = models.BooleanField(default=False)
    overall_comment = models.CharField(max_length=2000, blank=True)
    overall_comment_updated = models.DateTimeField(blank=True, null=True)
    signoff_time = models.DateTimeField(blank=True, null=True)

    def get_snv_checks(self):
        return VariantCheck.objects.filter(check_object = self)

    def check_snvs_pending(self):
        return self.get_snv_checks().filter(decision = '-').exists()

    def get_fusion_checks(self):
        return FusionCheck.objects.filter(check_object = self)

    def check_fusions_pending(self):
        return self.get_fusion_checks().filter(decision = '-').exists()

    @transaction.atomic
    def close(self, pass_fail, signoff_user):
        """ close current check """
        self.user = signoff_user
        self.signoff_time = timezone.now()
        self.status = pass_fail
        self.save()
        return True

    def demographics_checks(self):
        """ verify demographics checks have been performed and return object for AJAX """
        error_list = []
        # check for errors - demogrpahics check done, NTC check done
        if self.patient_info_check == False:
            error_list.append("The patient demographics for this sample haven't been checked")

        # select template based on whether there were any errors
        if len(error_list) == 0:
            pass_fail = True
            template = f'analysis/forms/ajax_finalise_form_check_1_pass.html'
        else:
            pass_fail = False
            template = f'analysis/forms/ajax_finalise_form_check_1_fail.html'

        # render HTML for AJAX form
        html = render_to_string(template, {'errors': error_list})

        # package data and return as JSON object
        data = json.dumps({
            'pass': pass_fail,
            'html': html,
        })

        return data

    def data_checks(self):
        """ verify data checks have been performed and return object for AJAX """

        error_list = []

        # all assays except RNA
        if self.analysis.panel.assay != '2':
            if self.coverage_ntc_check == False:
                error_list.append("The NTC coverage hasn't been checked for this sample")

        # manual variant review if required
        if self.analysis.panel.manual_review_required:
            if self.manual_review_check == False:
                error_list.append("Manual search for variants in IGV hasn't been completed (top of 'SNVs & indels' tab)")

        # checks for SNVs
        if self.analysis.panel.show_snvs:
            # no variants on pending
            if self.check_snvs_pending():
                error_list.append("Did not finalise check - not all SNVs have been checked")

        # checks for fusions
        if self.analysis.panel.show_fusions:
            if self.check_fusions_pending():
                error_list.append("Did not finalise check - not all fusions have been checked")

        # select template based on whether there were any errors
        if len(error_list) == 0:
            pass_fail = True
            template = f'analysis/forms/ajax_finalise_form_check_2_pass.html'
        else:
            pass_fail = False
            template = f'analysis/forms/ajax_finalise_form_check_2_fail.html'

        # render HTML for AJAX form
        html = render_to_string(template, {'errors': error_list})

        return pass_fail, html

    def finalise_checks(self, selection):
        """ verify and finalise a sample check """
        error_list = []
        if selection == 'demographics':
            data = self.demographics_checks()

        elif 'next_step_' in selection:
            if selection == 'next_step_pass':
                pass_fail_check_2, html_check_2 = self.data_checks()
            elif selection == 'next_step_fail':
                pass_fail_check_2 = True
                html_check_2 = render_to_string(f'analysis/forms/ajax_finalise_form_check_2_pass.html', {'errors': []})

            pass_fail_check_3, html_check_3 = self.analysis.finalise_checks(selection)
            data = json.dumps({
                'pass_check_2': pass_fail_check_2,
                'html_check_2': html_check_2,
                'pass_check_3': pass_fail_check_3,
                'html_check_3': html_check_3,
            })

        return data

    @transaction.atomic
    def finalise(self, pass_fail, next_step, signoff_user):
        """ signoff current step and either close case or make next check """
        sample_analysis_obj = self.analysis
        if next_step == 'finalise':
            sample_analysis_obj.finalise(pass_fail)
            self.close(pass_fail, signoff_user)

        elif next_step == 'extra_check':
            self.close(pass_fail, signoff_user)
            sample_analysis_obj.make_next_check()


class Variant(models.Model):
    """
    Variant info that always stays the same

    """
    variant = models.CharField(max_length=200)
    genome_build = models.IntegerField(default=37)
    
    class Meta:
        unique_together = ('variant','genome_build')


class VariantInstance(models.Model):
    """
    Sample specific information about a variant
    Make one of these for all variants within sample, regardless of panel

    """
    DECISION_CHOICES = (
        ('-', 'Pending'),
        ('G', 'Genuine'),
        ('A', 'Artefact'),
        ('P', 'Poly'),
        ('M', 'Miscalled'),
        ('N', 'Not analysed'),
        ('F', 'Failed call'),
    )
    sample = models.ForeignKey('Sample', on_delete=models.CASCADE)
    variant = models.ForeignKey('Variant', on_delete=models.CASCADE)
    gene = models.CharField(max_length=50)
    exon = models.CharField(max_length=50)
    hgvs_c = models.CharField(max_length=200)
    hgvs_p = models.CharField(max_length=200)
    total_count = models.IntegerField()
    alt_count = models.IntegerField()
    in_ntc = models.BooleanField()
    total_count_ntc = models.IntegerField(blank=True, null=True)
    alt_count_ntc = models.IntegerField(blank=True, null=True)
    gnomad_popmax = models.DecimalField(decimal_places=5, max_digits=10, blank=True, null=True)
    manual_upload = models.BooleanField(default=False)
    final_decision = models.CharField(max_length=1, default='-', choices=DECISION_CHOICES)

    def vaf(self):
        """ calculate VAF of variant from total and alt read counts """
        vaf = decimal.Decimal(self.alt_count / self.total_count) * 100
        vaf_rounded = vaf.quantize(decimal.Decimal('.01'), rounding=decimal.ROUND_DOWN)

        return vaf_rounded

    def vaf_ntc(self):
        """ calculate VAF of NTC variant if its seen in NTC, otherwise return None """
        if self.in_ntc:
            vaf = decimal.Decimal(self.alt_count_ntc / self.total_count_ntc) * 100
            vaf_rounded = vaf.quantize(decimal.Decimal('.01'), rounding=decimal.ROUND_DOWN)
            return vaf_rounded
        else:
            return None

    def gnomad_display(self):
        """ format the Gnoamd popmax AF into human readable text """
        # gnomad score missing in older runs
        if self.gnomad_popmax == None:
            return ''
        # -1 means that the variant is missing from gnomad
        elif self.gnomad_popmax == -1.00000:
            return 'Not found'
        # otherwise, format the value as a percentage, round up to prevent very low AFs appearing as 0
        else:
            gnomad_popmax = decimal.Decimal(self.gnomad_popmax * 100)
            popmax_rounded = gnomad_popmax.quantize(decimal.Decimal('.01'), rounding=decimal.ROUND_UP)
            return f'{popmax_rounded}%'

    def gnomad_link(self):
        """ link to the Gnomad webpage """
        genome_build = self.variant.genome_build

        # gnomad variant format has changed
        # stored as chrom:posref>alt
        # needs to be chrom-pos-ref-alt
        var = self.variant.variant
        var = var.replace(":", "-")
        var = var.replace(">", "-")
        var = re.split('(\d+)',var)
        var.insert(-1, "-")
        var = "".join(var)

        # format link specific to genome build
        if genome_build == 37:
            return f'https://gnomad.broadinstitute.org/variant/{var}?dataset=gnomad_r2_1'
        elif genome_build == 38:
            return f'https://gnomad.broadinstitute.org/variant/{var}?dataset=gnomad_r3'
        else:
            raise ValueError('Genome build should be either 37 or 38')


class VariantPanelAnalysis(models.Model):
    """
    Link instances of variants to a panel analysis

    """
    sample_analysis = models.ForeignKey('SampleAnalysis', on_delete=models.CASCADE)
    variant_instance = models.ForeignKey('VariantInstance', on_delete=models.CASCADE)

    def get_current_check(self):
        return VariantCheck.objects.filter(variant_analysis=self).latest('pk')

    def get_all_checks(self):
        return VariantCheck.objects.filter(variant_analysis=self).order_by('pk')

    def calculate_final_decision(self, pass_fail):
        all_checks = self.get_all_checks().exclude(decision='N')
        # if whole sample analysis failed then set as not analysed
        if pass_fail == 'F':
            return 'N'
        # if list is empty then it would have consisted of just not analysed, so set as not analysed
        elif all_checks.count() == 0:
            return 'N'
        else:
            return all_checks.last().decision


class VariantCheck(models.Model):
    """
    Record the genuine/ artefact check for a variant analysis

    """
    DECISION_CHOICES = (
        ('-', 'Pending'),
        ('G', 'Genuine'),
        ('A', 'Artefact'),
        ('P', 'Poly'),
        ('M', 'Miscalled'),
        ('N', 'Not analysed'),
        ('F', 'Failed call'),
    )
    variant_analysis = models.ForeignKey('VariantPanelAnalysis', on_delete=models.CASCADE)
    check_object = models.ForeignKey('Check', on_delete=models.CASCADE)
    decision = models.CharField(max_length=1, default='-', choices=DECISION_CHOICES)
    comment = models.CharField(max_length=500, blank=True, null=True)
    comment_updated = models.DateTimeField(blank=True, null=True)


class VariantList(models.Model):
    """
    A list of known variants. e.g. a poly list or previously classified list

    """
    TYPE_CHOICES = (
        ('P', 'SNV Poly'),
        ('K', 'Known'),
        ('A', 'SNV Artefact'),
        ('F', 'Fusion Artefact')
    )
    name = models.CharField(max_length=50, primary_key=True)
    list_type = models.CharField(max_length=1, choices=TYPE_CHOICES)
    genome_build = models.IntegerField(default=37)
    assay = models.CharField(blank=True, max_length=1, choices=Panel.ASSAY_CHOICES)

    def header(self):
        if self.genome_build == 37:
            build_css = 'info'
        elif self.genome_build == 38:
            build_css = 'success'
        return f'{self.get_assay_display()} {self.get_list_type_display()} list <span class="badge badge-{build_css}">GRCh{self.genome_build}</span>'


class VariantToVariantList(models.Model):
    """
    Link variants to variant lists

    """
    variant_list = models.ForeignKey('VariantList', on_delete=models.CASCADE)
    variant = models.ForeignKey('Variant', on_delete=models.CASCADE, blank=True, null=True)
    fusion = models.ForeignKey('Fusion', on_delete=models.CASCADE, blank=True, null=True)
    classification = models.CharField(max_length=50, blank=True, null=True)
    vaf_cutoff = models.DecimalField(decimal_places=5, max_digits=10, default=0.0)
    upload_user = models.ForeignKey('auth.User', on_delete=models.PROTECT, blank=True, null=True, related_name='upload_user')
    upload_time = models.DateTimeField(blank=True, null=True)
    upload_comment = models.CharField(max_length=500, blank=True, null=True)
    check_user = models.ForeignKey('auth.User', on_delete=models.PROTECT, blank=True, null=True,  related_name='check_user')
    check_time = models.DateTimeField(blank=True, null=True)
    check_comment = models.CharField(max_length=500, blank=True, null=True)

    def signed_off(self):
        """
        Check that there is a user assigned for both upload and check

        """
        if self.upload_user == None or self.check_user == None:
            return False
        else:
            return True


class Gene(models.Model):
    """
    A gene

    """
    gene = models.CharField(max_length=50, primary_key=True)


class GeneCoverageAnalysis(models.Model):
    """
    Average coverage metrics across a gene 

    """
    sample = models.ForeignKey('SampleAnalysis', on_delete=models.CASCADE)
    gene = models.ForeignKey('Gene', on_delete=models.CASCADE)
    av_coverage = models.IntegerField()
    percent_135x = models.IntegerField(blank=True, null=True)
    percent_270x = models.IntegerField(blank=True, null=True)
    percent_500x = models.IntegerField(blank=True, null=True)
    percent_1000x = models.IntegerField(blank=True, null=True)
    av_ntc_coverage = models.IntegerField()
    percent_ntc = models.IntegerField()


class RegionCoverageAnalysis(models.Model):
    """
    Coverage metrics across a specific region

    """
    HOTSPOT_CHOICES = (
        ('H', 'Hotspot'),
        ('G', 'Genescreen'),
    )
    gene = models.ForeignKey('GeneCoverageAnalysis', on_delete=models.CASCADE)
    hgvs_c = models.CharField(max_length=200)
    chr_start = models.CharField(max_length=50)
    pos_start = models.IntegerField()
    chr_end = models.CharField(max_length=50)
    pos_end = models.IntegerField()
    hotspot = models.CharField(max_length=1, choices=HOTSPOT_CHOICES)
    average_coverage = models.IntegerField()
    percent_135x = models.IntegerField(blank=True, null=True)
    percent_270x = models.IntegerField(blank=True, null=True)
    percent_500x = models.IntegerField(blank=True, null=True)
    percent_1000x = models.IntegerField(blank=True, null=True)
    ntc_coverage = models.IntegerField()
    percent_ntc = models.IntegerField()

    def genomic(self):
        return f'{self.chr_start}:{self.pos_start}_{self.chr_end}:{self.pos_end}'


class GapsAnalysis(models.Model):
    """
    Gaps that fall within specific region

    """
    gene = models.ForeignKey('GeneCoverageAnalysis', on_delete=models.CASCADE)
    hgvs_c = models.CharField(max_length=200)
    chr_start = models.CharField(max_length=50)
    pos_start = models.IntegerField()
    chr_end = models.CharField(max_length=50)
    pos_end = models.IntegerField()
    coverage_cutoff = models.IntegerField()
    percent_cosmic = models.DecimalField(decimal_places=2, max_digits=5, blank=True, null=True)
    counts_cosmic = models.IntegerField(blank=True, null=True)

    def genomic(self):
        return f'{self.chr_start}:{self.pos_start}_{self.chr_end}:{self.pos_end}'


class Fusion(models.Model):
    """
    A fusion
    """
    fusion_genes = models.CharField(max_length=50)
    left_breakpoint = models.CharField(max_length=50)
    right_breakpoint = models.CharField(max_length=50)
    genome_build = models.IntegerField(default=37)


class FusionAnalysis(models.Model):
    """
    A specfic analysis of a fusion
    """
    DECISION_CHOICES = (
        ('-', 'Pending'),
        ('G', 'Genuine'),
        ('A', 'Artefact'),
        ('P', 'Poly'),
        ('M', 'Miscalled'),
        ('N', 'Not analysed'),
        ('F', 'Failed call'),
    )
    sample = models.ForeignKey('SampleAnalysis', on_delete=models.CASCADE)
    fusion_genes = models.ForeignKey('Fusion', on_delete=models.CASCADE)
    hgvs = models.CharField(max_length=400, blank=True)
    fusion_supporting_reads = models.IntegerField()
    ref_reads_1 = models.IntegerField()
    ref_reads_2 = models.IntegerField(blank=True, null=True) # will be blank if splice variant
    split_reads = models.IntegerField(blank=True, null=True)
    spanning_reads = models.IntegerField(blank=True, null=True)
    fusion_caller = models.CharField(max_length=50)
    fusion_score = models.CharField(max_length=50, blank=True, null=True)
    in_ntc = models.BooleanField(default=False)
    final_decision = models.CharField(max_length=1, default='-', choices=DECISION_CHOICES)
    manual_upload=models.BooleanField(default=False)

    def vaf(self):
        """
        calculate VAF of variant from total and alt read counts
        VAF is always displayed to two decimal places

        """
        total_reads = self.fusion_supporting_reads + self.ref_reads_1
        vaf = decimal.Decimal(self.fusion_supporting_reads / total_reads) * 100
        vaf_rounded = vaf.quantize(decimal.Decimal('.01'), rounding = decimal.ROUND_DOWN)

        return vaf_rounded


class FusionCheck(models.Model):
    """
    Record the genuine/ artefact check for a fusion analysis

    """
    DECISION_CHOICES = (
        ('-', 'Pending'),
        ('G', 'Genuine'),
        ('A', 'Artefact'),
        ('P', 'Poly'),
        ('M', 'Miscalled'),
        ('N', 'Not analysed'),
        ('F', 'Failed call'),
    )
    fusion_analysis = models.ForeignKey('FusionPanelAnalysis', on_delete=models.CASCADE)
    check_object = models.ForeignKey('Check', on_delete=models.CASCADE)
    decision = models.CharField(max_length=1, default='-', choices=DECISION_CHOICES)
    comment = models.CharField(max_length=2000, blank=True, null=True)
    comment_updated = models.DateTimeField(blank=True, null=True)


class FusionPanelAnalysis(models.Model):
    """
    Link instances of variants to a panel analysis

    """
    sample_analysis = models.ForeignKey('SampleAnalysis', on_delete=models.CASCADE)
    fusion_instance = models.ForeignKey('FusionAnalysis', on_delete=models.CASCADE)

    def get_current_check(self):
        return FusionCheck.objects.filter(fusion_analysis=self).latest('pk')

    def get_all_checks(self):
        return FusionCheck.objects.filter(fusion_analysis=self).order_by('pk')

    def calculate_final_decision(self, pass_fail):
        all_checks = self.get_all_checks().exclude(decision='N')
        # if whole sample analysis failed then set as not analysed
        if pass_fail == 'F':
            return 'N'
        # if list is empty then it would have consisted of just not analysed, so set as not analysed
        if all_checks.count() == 0:
            return 'N'
        else:
            return all_checks.last().decision


auditlog.register(Run)
auditlog.register(Worksheet)
auditlog.register(Sample)
auditlog.register(Panel)
auditlog.register(SampleAnalysis)
auditlog.register(Check)
auditlog.register(Variant)
auditlog.register(VariantInstance)
auditlog.register(VariantPanelAnalysis)
auditlog.register(VariantCheck)
auditlog.register(VariantList)
auditlog.register(VariantToVariantList)
auditlog.register(Gene)
auditlog.register(GeneCoverageAnalysis)
auditlog.register(RegionCoverageAnalysis)
auditlog.register(GapsAnalysis)
auditlog.register(Fusion)
auditlog.register(FusionAnalysis)
auditlog.register(FusionCheck)
auditlog.register(FusionPanelAnalysis)
