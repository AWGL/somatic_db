from auditlog.registry import auditlog
from django.db import models

import decimal


# Create your models here.
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

    def __str__(self):
        return self.ws_id

    def get_status(self):
        samples = SampleAnalysis.objects.filter(worksheet = self)
        l = [ s.get_checks()['current_status'] for s in samples ]
        return ' | '.join( set(l) )


class Sample(models.Model):
    """
    An individual sample

    """
    TYPE_CHOICES = (
        ('DNA', 'DNA'),
        ('RNA', 'RNA'),
    )
    sample_id = models.CharField(max_length=50, primary_key=True)
    sample_name = models.CharField(max_length=200, blank=True, null=True)
    sample_name_check=models.BooleanField(default=False)
    sample_type = models.CharField(max_length=3, choices=TYPE_CHOICES)


class Panel(models.Model):
    """
    A virtual panel
    TODO - add enough info to kick off a reanalysis from within the db
    e.g. path to BED, ?panel version number

    """
    TYPE_CHOICES = (
        ('DNA', 'DNA'),
        ('RNA', 'RNA'),
    )
    panel_name = models.CharField(max_length=50)
    dna_or_rna = models.CharField(max_length=3, choices=TYPE_CHOICES)


class SampleAnalysis(models.Model):
    """
    An analysis of a sample, if there are multiple analyses (e.g. multiple panels), 
    then there will be multiple sample analysis objects

    """
    worksheet = models.ForeignKey('Worksheet', on_delete=models.CASCADE)
    sample = models.ForeignKey('Sample', on_delete=models.CASCADE)
    panel = models.ForeignKey('Panel', on_delete=models.CASCADE)
    total_reads = models.IntegerField(blank=True, null=True)
    total_reads_ntc= models.IntegerField(blank=True, null=True)
    percent_reads_ntc= models.CharField(max_length=200, blank=True, null=True)

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
                
        return {
            'current_status': current_status,
            'assigned_to': assigned_to,
            'current_check_object': current_check_object,
            'all_checks': all_checks,
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
    stage = models.CharField(max_length=3, choices=STAGE_CHOICES)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES)
    user = models.ForeignKey('auth.User', on_delete=models.PROTECT, blank=True, null=True)
    coverage_ntc_check = models.BooleanField(default=False)
    coverage_comment = models.CharField(max_length=500, blank=True)
    coverage_comment_updated = models.DateTimeField(blank=True, null=True)
    patient_info_check = models.BooleanField(default=False)
    overall_comment = models.CharField(max_length=500, blank=True)
    overall_comment_updated = models.DateTimeField(blank=True, null=True)
    signoff_time = models.DateTimeField(blank=True, null=True)


class Variant(models.Model):
    """
    Variant info that always stays the same

    """
    genomic_37 = models.CharField(max_length=200, unique=True)
    genomic_38 = models.CharField(max_length=200, blank=True, null=True)


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
    manual_upload = models.BooleanField(default=False)
    final_decision = models.CharField(max_length=1, default='-', choices=DECISION_CHOICES)

    def vaf(self):
        """
        calculate VAF of variant from total and alt read counts
        VAF is always displayed to two decimal places

        """
        vaf = decimal.Decimal(self.alt_count / self.total_count) * 100
        vaf_rounded = vaf.quantize(decimal.Decimal('.01'), rounding = decimal.ROUND_DOWN)

        return vaf_rounded

    def vaf_ntc(self):
        """
        calculate VAF of NTC variant if its seen in NTC, otherwise return None
        VAF is always displayed to two decimal places

        """
        if self.in_ntc:
            vaf = decimal.Decimal(self.alt_count_ntc / self.total_count_ntc) * 100
            vaf_rounded = vaf.quantize(decimal.Decimal('.01'), rounding = decimal.ROUND_DOWN)
            return vaf_rounded
        else:
            return None


class VariantPanelAnalysis(models.Model):
    """
    Link instances of variants to a panel analysis

    """
    sample_analysis = models.ForeignKey('SampleAnalysis', on_delete=models.CASCADE)
    variant_instance = models.ForeignKey('VariantInstance', on_delete=models.CASCADE)

    def get_current_check(self):
        return VariantCheck.objects.filter(variant_analysis=self).latest('pk')


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
        ('P', 'Poly'),
        ('K', 'Known'),
        ('A', 'Artefact'),
    )
    name = models.CharField(max_length=50, primary_key=True)
    list_type = models.CharField(max_length=1, choices=TYPE_CHOICES)


class VariantToVariantList(models.Model):
    """
    Link variants to variant lists

    """
    variant_list = models.ForeignKey('VariantList', on_delete=models.CASCADE)
    variant = models.ForeignKey('Variant', on_delete=models.CASCADE)
    classification = models.CharField(max_length=50, blank=True, null=True)


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
    percent_270x = models.IntegerField()
    percent_135x = models.IntegerField()
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
    percent_270x = models.IntegerField()
    percent_135x = models.IntegerField()
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
    percent_cosmic = models.IntegerField(blank=True, null=True)

    def genomic(self):
        return f'{self.chr_start}:{self.pos_start}_{self.chr_end}:{self.pos_end}'


class Fusion(models.Model):
    """

    """
    fusion_genes = models.CharField(max_length=50)
    left_breakpoint = models.CharField(max_length=50)
    right_breakpoint = models.CharField(max_length=50)


class FusionAnalysis(models.Model):
    """

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
    comment = models.CharField(max_length=500, blank=True, null=True)
    comment_updated = models.DateTimeField(blank=True, null=True)


class FusionPanelAnalysis(models.Model):
    """
    Link instances of variants to a panel analysis

    """
    sample_analysis = models.ForeignKey('SampleAnalysis', on_delete=models.CASCADE)
    fusion_instance = models.ForeignKey('FusionAnalysis', on_delete=models.CASCADE)

    def get_current_check(self):
        return FusionCheck.objects.filter(fusion_analysis=self).latest('pk')


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
