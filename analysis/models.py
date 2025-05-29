from django.db import models
from django.contrib.auth.models import User

from auditlog.registry import auditlog
import decimal
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
    ws_id = models.CharField(max_length=50, primary_key=True)
    run = models.ForeignKey('Run', on_delete=models.CASCADE)
    assay = models.CharField(max_length=50)
    diagnostic = models.BooleanField(default=True)
    upload_time = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.ws_id

    def get_status_and_samples(self):
        # get all sample analysis objects
        samples = SampleAnalysis.objects.filter(worksheet = self)

        # get list of all unique statuses and concatenate
        all_status = [ s.get_checks()['current_status'] for s in samples ]
        status = ' | '.join( set(all_status) )
        
        # get all sample IDs
        sample_list = [i.sample.sample_id for i in samples]

        return status, sample_list


class Sample(models.Model):
    """
    An individual sample

    """
    sample_id = models.CharField(max_length=50, primary_key=True)
    sample_name = models.CharField(max_length=200, blank=True, null=True)
    sample_name_check = models.BooleanField(default=False)
    tumour_content = models.IntegerField(null=True, blank=True)
    tumour_content_check = models.BooleanField(default=False)

    def get_worksheets(self):
        # get all worksheets that the sample appears on
        sample_analyses = SampleAnalysis.objects.filter(sample=self)
        worksheets = []
        for s in sample_analyses:
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
    minimum_supporting_reads = models.IntegerField(default=1, blank=True, null=True) # minimum number of reads required to call a variant genuine (GeneRead)
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
    worksheet = models.ForeignKey('Worksheet', on_delete=models.CASCADE)
    sample = models.ForeignKey('Sample', on_delete=models.CASCADE)
    panel = models.ForeignKey('Panel', on_delete=models.CASCADE)
    paperwork_check = models.BooleanField(default=False)
    total_reads = models.IntegerField(blank=True, null=True)
    total_reads_ntc = models.IntegerField(blank=True, null=True)
    genome_build = models.IntegerField(default=37)
    upload_time = models.DateTimeField(blank=True, null=True)


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

    def get_checks(self):
        """
        Get all associated checks and work out the status
        TODO - make this a bit better
        TODO - this is getting called twice when samples page is loaded
        """
        all_checks = Check.objects.filter(analysis = self).order_by('pk')
        igv_checks = all_checks.filter(stage='IGV')

        current_status = 'Complete'
        assigned_to = None
        current_check_object = all_checks.latest('pk')

        for n, c in enumerate(igv_checks):
            if c.status == 'P':
                current_status = f'{c.get_stage_display()} {n+1}'
                assigned_to = c.user
                current_check_object = c

        num_fails = [ c for c in igv_checks if c.status == 'F' ]
        if len(num_fails) == 1:
            current_status = 'Fail - 2nd check required'
        elif len(num_fails) > 1:
            current_status = 'Fail'
                
        # make list of checks initials for LIMS XML
        lims_checks = []
        for c in all_checks:
            if c.user:
                lims_initials = c.user.usersettings.lims_initials
                if lims_initials not in lims_checks:
                    lims_checks.append(lims_initials)

        return {
            'current_status': current_status,
            'assigned_to': assigned_to,
            'current_check_object': current_check_object,
            'all_checks': all_checks,
            'lims_checks': ','.join(lims_checks),
        }


class Check(models.Model):
    """
    Model to store 1st, 2nd check etc

    """
    STAGE_CHOICES = (
        ('IGV', 'IGV check'),
        ('VUS', 'Interpretation check'),
    )
    STATUS_CHOICES = (
        ('P', 'Pending'),
        ('C', 'Complete'),
        ('F', 'Fail'),
    )
    analysis = models.ForeignKey('SampleAnalysis', on_delete=models.CASCADE)
    stage = models.CharField(max_length=3, choices=STAGE_CHOICES) # TODO - this isnt really needed anymore
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
        
    def brca_sufficient_supporting_reads_count(self):
        """
        Flags variants with fewer than the minimum supporting reads 
        BRCA team will not analyse these
        """
        # get variant panel analysis
        variant_panel_analysis_obj = VariantPanelAnalysis.objects.get(variant_instance = self)
        # get minimum supporting reads
        minimum_supporting_reads = variant_panel_analysis_obj.sample_analysis.panel.minimum_supporting_reads
        if self.alt_count >= minimum_supporting_reads:
            return True
        else:
            return False
        
    def brca_above_tumour_content_threshold(self):
        """
        Flags if the VAF is more than 10% of the tumour content
        For germline samples, flags if a variant is above 10%
        """
        tumour_content = self.sample.tumour_content
        try:
            if tumour_content == 0:
                # for germline samples we're setting this threshold at 10%
                tumour_content_threshold = 10
            else:
                tumour_content_threshold = tumour_content / 10
        except TypeError:
            # tumour content not set - don't flag anything
            return 1
        
        vaf = self.vaf()

        if vaf > tumour_content_threshold:
            return True
        else:
            return False
        
    def is_brca_poly(self):
        """
        The BRCA guidelines state BA1 is applied at >0.1% in gnomad, but we don't want to filter on this
        These can't be classed as polys in all assays because most other assays use 1%
        """
        # gnomad score missing in older runs, so we can't exclude
        if self.gnomad_popmax == None:
            return False
        # -1 means that the variant is missing from gnomad
        elif self.gnomad_popmax == -1.00000:
            return False
        elif self.gnomad_popmax < 0.01:
            return False
        else:
            # otherwise, >1% in gnomAD
            return True
    
    @staticmethod
    def load_in_brca_known_pathogenics():
        """
        Load in the BRCA known pathogenic variants from a file
        """
        with open("roi/b37/GeneRead_BRCA/brca_known_pathogenic_variants.txt") as f:
            contents = f.readlines()
            contents = [line.rstrip() for line in contents]
            return contents
    
    def is_brca_deep_intronic(self):
        """
        We're not interested in any variants more than 20bp in to the introns with the exception of
        a single known pathogenic variant
        """
        known_pathogenics = self.load_in_brca_known_pathogenics()
        if self.hgvs_c in known_pathogenics:
            return False
        intronics = re.findall("[-+]\d+", self.hgvs_c)
        if len(intronics) > 1:
            # this shouldn't happen, don't flag to be safe
            return False
        elif len(intronics) == 0:
            return False
        else:
            distance = abs(int(intronics[0]))
            if distance > 20: 
                return True
            else:
                return False


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
    percent_100x = models.IntegerField(blank=True, null=True)
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
    percent_100x = models.IntegerField(blank=True, null=True)
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
