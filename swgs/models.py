import random
import string

from django.db import models
from django.contrib.auth.models import User
from auditlog.registry import auditlog

#####################
### Common Models ###
#####################

class Gene(models.Model):
    """
    Gene
    """
    id = models.AutoField(primary_key=True)
    gene = models.CharField(max_length=20, unique=True)

    def __repr__(self):
        return f"Gene: {self.gene}"
    
    def __str__(self):
        return f"{self.gene}"

class Transcript(models.Model):
    """
    NCBI transcript identifiers
    """
    id = models.AutoField(primary_key=True)
    transcript = models.CharField(max_length=50, unique=True)
    gene = models.ForeignKey("Gene", on_delete=models.CASCADE)

    def __repr__(self):
        return f"Transcript {self.transcript} in gene {self.gene}"
    
    def __str__(self):
        return f"{self.transcript}"

######################
### Analysis Setup ###
######################

class Patient(models.Model):
    """
    An individual patient.
    If NHS number is not available, it is replaced with UNKNOWN[id]
    """
    
    id = models.AutoField(primary_key=True)
    nhs_number = models.CharField(max_length=10, default="UNKNOWN")

    def __str__(self):
        return f"{self.nhs_number}"


class Sample(models.Model):
    """
    An individual sample
    """
    id = models.AutoField(primary_key=True)
    sample_id = models.CharField(max_length=20)

    def __repr__(self):
        return f"Sample {self.sample_id}"
    
    def __str__(self):
        return f"{self.sample_id}"
    
class Panel(models.Model):
    """
    A virtual panel of genes
    """
    id = models.AutoField(primary_key=True)
    panel_name = models.CharField(max_length=100)
    panel_version = models.DecimalField(max_digits=4, decimal_places=1)
    panel_notes = models.TextField(null=True, blank=True)
    panel_approved = models.BooleanField(default=False)
    genes = models.ManyToManyField('Gene', related_name="panels")
    #settings

    class Meta:
        unique_together = ["panel_name", "panel_version"]

    def __repr__(self):
        return f"Panel: {self.panel_name} {self.panel_version}"
    
    def __str__(self):
        return f"{self.panel_name}_{str(self.panel_version)}"
    
    def display_panel_name(self):

        # split on _
        split_panel_name = self.panel_name.split("_")

        # remove germline/somatic if relevant and join with spaces
        if split_panel_name[0] == "germline" or split_panel_name[0] == "somatic":
            joined_panel_name = " ".join(split_panel_name[1:])
        else:
            joined_panel_name = " ".join(split_panel_name)

        # change to title case
        joined_panel_name = joined_panel_name.title()

        # add version
        display_panel_name = f"{joined_panel_name} {self.panel_version}"

        return display_panel_name
    
    def display_somatic_or_germline(self):

        somatic_or_germline = self.panel_name.split("_")[0]

        if somatic_or_germline == "somatic":
            return "Somatic"
        elif somatic_or_germline == "germline":
            return "Germline"
        else:
            return "Unknown"
        
    def get_type(self):
        if "_cnv_" in self.panel_name:
            return "cnv"
        elif "_fusion_" in self.panel_name:
            return "fusion"
        else:
            return "snv"

    def get_gene_names(self):

        gene_names = []

        for gene in self.genes.all():
            gene_names.append(gene.gene)
        
        return gene_names
    
    #TODO fusion panel model
        

class Indication(models.Model):
    """
    Indication the patient is being tested for e.g. ALL
    Note: Germline panels being tiers 1 and 3 is deliberate because this is what GEL do
    """
    id = models.AutoField(primary_key=True)
    indication = models.CharField(max_length=20)
    version = models.IntegerField(null=True, blank=True)
    indication_pretty_print = models.CharField(max_length=100, null=True, blank=True)
    lims_code = models.CharField(max_length=20, null=True, blank=True)
    # germline SNV panels
    germline_panels_tier_zero = models.ManyToManyField("Panel", related_name="germline_panels_tier_zero", blank=True)
    germline_panels_tier_one = models.ManyToManyField("Panel", related_name="germline_panels_tier_one")
    germline_panels_tier_three = models.ManyToManyField("Panel", related_name="germline_panels_tier_three")
    # somatic SNV panels
    somatic_panels_tier_zero = models.ManyToManyField("Panel", related_name="somatic_panels_tier_zero", blank=True)
    somatic_panels_tier_one = models.ManyToManyField("Panel", related_name="somatic_panels_tier_one")
    somatic_panels_tier_two = models.ManyToManyField("Panel", related_name="somatic_panels_tier_two")
    # germline CNV panels
    germline_cnv_panels_tier_zero = models.ManyToManyField("Panel", related_name="germline_panels_cnv_tier_zero", blank=True)
    germline_cnv_panels_tier_one = models.ManyToManyField("Panel", related_name="germline_panels_cnv_tier_one")
    germline_cnv_panels_tier_three = models.ManyToManyField("Panel", related_name="germline_panels_cnv_tier_three")
    # somatic CNV panels
    somatic_cnv_panels_domain_zero = models.ManyToManyField("Panel", related_name="somatic_panels_cnv_domain_zero", blank=True)
    somatic_cnv_panels_domain_one = models.ManyToManyField("Panel", related_name="somatic_panels_cnv_domain_one")
    somatic_cnv_panels_domain_two = models.ManyToManyField("Panel", related_name="somatic_panels_cnv_domain_two")
    #TODO fusions

    def __repr__(self):
        return f"Indication: {self.indication_pretty_print}"
    
    def __str__(self):
        return f"{self.indication}"
    
    @staticmethod
    def get_genes_and_panels(panel_query):

        genes = []
        panels = []

        for panel in panel_query:
            gene_names = panel.get_gene_names()
            genes += gene_names
            panel_name_and_id = {
                "panel_name": panel.display_panel_name(),
                "panel_id": panel.id
            }
            panels.append(panel_name_and_id)
        
        return {"genes": list(set(genes)), "panels": panels}
    
    def get_all_genes_and_panels(self):

        genes_and_panels_dict = {
            "somatic_tier_zero": self.get_genes_and_panels(self.somatic_panels_tier_zero.all()),
            "somatic_tier_one": self.get_genes_and_panels(self.somatic_panels_tier_one.all()),
            "somatic_tier_two": self.get_genes_and_panels(self.somatic_panels_tier_two.all()),
            "germline_tier_zero": self.get_genes_and_panels(self.germline_panels_tier_zero.all()),
            "germline_tier_one": self.get_genes_and_panels(self.germline_panels_tier_one.all()),
            "germline_tier_three": self.get_genes_and_panels(self.germline_panels_tier_three.all()),
            "germline_cnv_tier_zero": self.get_genes_and_panels(self.germline_cnv_panels_tier_zero.all()),
            "germline_cnv_tier_one": self.get_genes_and_panels(self.germline_cnv_panels_tier_one.all()),
            "germline_cnv_tier_three": self.get_genes_and_panels(self.germline_cnv_panels_tier_three.all()),
            "somatic_cnv_domain_zero": self.get_genes_and_panels(self.somatic_cnv_panels_domain_zero.all()),
            "somatic_cnv_domain_one": self.get_genes_and_panels(self.somatic_cnv_panels_domain_one.all()),
            "somatic_cnv_domain_two": self.get_genes_and_panels(self.somatic_cnv_panels_domain_two.all())
        }

        return genes_and_panels_dict
    
    @staticmethod
    def display_genes(genes_and_panels_dict):
        somatic_tier_two = [
            gene for gene in genes_and_panels_dict["somatic_tier_two"]["genes"] if gene not in genes_and_panels_dict["somatic_tier_one"]["genes"]
        ]
        somatic_cnv_domain_two = [
            gene for gene in genes_and_panels_dict["somatic_cnv_domain_two"]["genes"] if gene not in genes_and_panels_dict["somatic_cnv_domain_one"]["genes"]
        ]
        germline_tier_three = [
            gene for gene in genes_and_panels_dict["germline_tier_three"]["genes"] if gene not in genes_and_panels_dict["germline_tier_one"]["genes"]
        ]
        germline_cnv_tier_three = [
            gene for gene in genes_and_panels_dict["germline_cnv_tier_three"]["genes"] if gene not in genes_and_panels_dict["germline_cnv_tier_one"]["genes"]
        ]
        display_genes_dict = {
            "somatic_tier_one": sorted(genes_and_panels_dict["somatic_tier_one"]["genes"]),
            "somatic_tier_two": sorted(somatic_tier_two),
            "somatic_cnv_domain_one": sorted(genes_and_panels_dict["somatic_cnv_domain_one"]["genes"]),
            "somatic_cnv_domain_two": somatic_cnv_domain_two,
            "germline_tier_one": sorted(genes_and_panels_dict["germline_tier_one"]["genes"]),
            "germline_tier_three": sorted(germline_tier_three),
            "germline_cnv_tier_one": sorted(genes_and_panels_dict["germline_cnv_tier_one"]["genes"]),
            "germline_cnv_tier_three": sorted(germline_cnv_tier_three)
        }

        return display_genes_dict
    

class Run(models.Model):
    """
    NGS Run. Using the Run as the primary key as new LIMS worklists are inconsistent
    """
    id = models.AutoField(primary_key=True)
    run = models.CharField(max_length=50, unique=True)
    worksheet = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return f"{self.run}"

    def get_patient_analysis(self):
        patient_analyses = PatientAnalysis.objects.filter(run=self)
        #patient_analysis_list = []
        #for p in patient_analyses:
            #patient_analysis_list.append(p.id)
        #return patient_analysis_list
        for p in patient_analyses:
            return p.id

class PatientAnalysis(models.Model):
    """
    A single analysis of a given patient
    """
    id = models.AutoField(primary_key=True)
    patient = models.ForeignKey('Patient', on_delete=models.CASCADE)
    tumour_sample = models.ForeignKey('Sample', on_delete=models.CASCADE, related_name='tumour_sample')
    germline_sample = models.ForeignKey('Sample', on_delete=models.CASCADE, null=True, related_name='germline_sample')
    indication = models.ForeignKey('Indication', on_delete=models.CASCADE)
    run = models.ForeignKey('Run', on_delete=models.CASCADE)
    # QC
    somatic_vaf_distribution = models.ForeignKey('QCSomaticVAFDistribution', on_delete=models.CASCADE)
    tumour_in_normal_contamination = models.ForeignKey('QCTumourInNormalContamination', on_delete=models.CASCADE)
    germline_cnv_quality = models.ForeignKey('QCGermlineCNVQuality', on_delete=models.CASCADE)
    low_quality_tumour_sample = models.ForeignKey('QCLowQualityTumourSample', on_delete=models.CASCADE)
    tumour_ntc_contamination = models.ForeignKey('QCNTCContamination', on_delete=models.CASCADE, related_name='tumour_ntc_contamination')
    germline_ntc_contamination = models.ForeignKey('QCNTCContamination', on_delete=models.CASCADE, related_name='germline_ntc_contamination')
    relatedness = models.ForeignKey('QCRelatedness', on_delete=models.CASCADE)
    tumour_purity = models.ForeignKey('QCTumourPurity', on_delete=models.CASCADE)
    #TODO add a QC metric on tumour purity

    def __str__(self):
        return f"{self.run}_{self.tumour_sample}_{self.germline_sample}"
    
    def create_patient_analysis_info_dict(self):

        patient_analysis_info_dict = {
            "patient_identifier": self.patient.nhs_number,
            "run": self.run.run,
            "worksheet": self.run.worksheet,
            "tumour_sample": self.tumour_sample.sample_id,
            "germline_sample": self.germline_sample.sample_id,
            "indication": self.indication.indication,
            "indication_id": self.indication.id
        }

        return patient_analysis_info_dict
    
    def create_qc_dict(self):

        patient_analysis_qc_dict = {
            "somatic_vaf_distribution": {
                "display_name": "Somatic VAF Distribution",
                "status": self.somatic_vaf_distribution.status,
                "message": self.somatic_vaf_distribution.message,
                "tooltip": "A high proportion of low frequency variants can indicate poor tumour quality"
            },
            "tumour_in_normal_contamination": {
                "display_name": "Tumour In Normal Contamination (TINC)",
                "status": self.tumour_in_normal_contamination.status,
                "message": self.tumour_in_normal_contamination.message,
                "tooltip": "Tumour in normal contamination impacts sensitivity - contact bioinformatics for WARN or FAIL"
            },
            "germline_cnv_quality": {
                "display_name": "Germline CNV Quality",
                "status": self.germline_cnv_quality.status,
                "message": self.germline_cnv_quality.message,
                "tooltip": "If germline CNVs are low quality, this may impact sensitivity of germline CNV calling, and precision of somatic CNV calling (potential for more false positives)"
            },
            "low_quality_tumour_sample_qc": {
                "display_name": "Tumour Sample Quality",
                "status": self.low_quality_tumour_sample.status,
                "message": self.low_quality_tumour_sample.message,
                "tooltip": "This considers several metrics which GEL have found are indicative of poor quality samples in their SWGS service"
            },
            "tumour_ntc_contamination": {
                "display_name": "Tumour Sample NTC Contamination",
                "status": self.tumour_ntc_contamination.status,
                "message": self.tumour_ntc_contamination.message,
                "tooltip": "High NTC contamination indicates either DNA in the NTC or low reads in the tumour sample"
            },
            "germline_ntc_contamination": {
                "display_name": "Germline Sample NTC Contamination",
                "status": self.germline_ntc_contamination.status,
                "message": self.germline_ntc_contamination.message,
                "tooltip": "High NTC contamination indicates either DNA in the NTC or low reads in the germline sample"
            },
            "relatedness": {
                "display_name": "Matched Sample ID Check",
                "status": self.relatedness.status,
                "message": self.relatedness.message,
                "tooltip": "This metric checks the germline and somatic samples are from the same individual. If this metric has failed DO NOT PROCEED with analysis"
            },
            "tumour_purity": {
                "display_name": "Estimated Tumour Purity",
                "status": self.tumour_purity.status,
                "message": self.tumour_purity.message,
                "tooltip": "This metric estimates the tumour purity from the NGS data. Low purity samples may have reduced sensitvity to low level variants."
            }
        }

        return patient_analysis_qc_dict

class MDTNotes(models.Model):
    """
    Notes on MDTs. Links to a patient so informaiton from multiple analyses is pulled through
    """
    id = models.AutoField(primary_key=True)
    patient = models.ForeignKey('Patient', on_delete=models.CASCADE)
    notes = models.TextField()
    date = models.DateField()


#################
### QC Models ###
#################

QC_CHOICES = (
    ("P", "Pass"),
    ("W", "Warn"),
    ("F", "Fail")
)

class AbstractQCCheck(models.Model):
    """
    Base class for QC checks - cannot be instantiated
    """
    id = models.AutoField(primary_key=True)
    status = models.CharField(max_length=1, choices=QC_CHOICES)
    #TODO sort message out so there's not loads of data replication
    message = models.TextField(max_length=1000)

    class Meta:
        abstract = True

class QCSomaticVAFDistribution(AbstractQCCheck):
    """
    QC check for somatic VAF distribution
    """
    low_vaf_proportion = models.DecimalField(max_digits=7, decimal_places=6)

    class Meta:
        unique_together = ["status", "message", "low_vaf_proportion"]

class QCTumourInNormalContamination(AbstractQCCheck):
    """
    QC check for TINC
    """
    #TODO add fields when we've decided on script use

    class Meta:
        unique_together = ["status", "message"]

class QCGermlineCNVQuality(AbstractQCCheck):
    """
    QC check for germline CNV quality
    """
    passing_cnv_count = models.IntegerField()
    passing_fraction = models.DecimalField(max_digits=7, decimal_places=6)
    log_loss_gain = models.DecimalField(max_digits=7, decimal_places=5)

    class Meta:
        unique_together = ["passing_cnv_count", "passing_fraction", "log_loss_gain"]

class QCLowQualityTumourSample(AbstractQCCheck):
    """
    QC check for low quality tumour sample QC
    """
    unevenness_of_coverage = models.DecimalField(max_digits=7, decimal_places=4)
    median_fragment_length = models.DecimalField(max_digits=7, decimal_places=1)
    at_drop = models.DecimalField(max_digits=7, decimal_places=4)
    cg_drop = models.DecimalField(max_digits=7, decimal_places=4)

    class Meta:
        unique_together = ["status", "message", "unevenness_of_coverage", "median_fragment_length", "at_drop", "cg_drop"]

class QCNTCContamination(AbstractQCCheck):
    """
    QC check for NTC contamination
    """
    ntc_contamination = models.DecimalField(max_digits=7, decimal_places=6)

    class Meta:
        unique_together = ["status", "message", "ntc_contamination"]

class QCRelatedness(AbstractQCCheck):
    relatedness = models.DecimalField(max_digits=4, decimal_places=3)

    class Meta:
        unique_together = ["status", "message", "relatedness"]

class QCTumourPurity(AbstractQCCheck):
    tumour_purity = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        unique_together = ["status", "message", "tumour_purity"]

################
### Coverage ###
################

class GeneCoverage(models.Model):
    """
    Coverage information for a given gene
    """
    id = models.AutoField(primary_key=True)
    gene = models.ForeignKey("Gene", on_delete=models.CASCADE)
    is_germline = models.BooleanField()
    mean_coverage = models.DecimalField(max_digits=7, decimal_places=1)
    # threshold coverage

################
### Variants ###
################

class GenomeBuild(models.Model):
    """
    Genome Builds
    """
    id = models.AutoField(primary_key=True)
    genome_build = models.CharField(unique=True, max_length=10)

    def __str__(self):
        return f"{self.genome_build}"

class Variant(models.Model):
    """
    An individual SNP/small indel
    """
    #TODO find a way to default to b38
    id = models.AutoField(primary_key=True)
    variant = models.CharField(max_length=200, unique=True)
    genome_build = models.ForeignKey("GenomeBuild", on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.variant}"
    
    def split_variant(self):
        chrom = self.variant.split(":")[0]
        pos = self.variant.split(":")[1]
        ref = self.variant.split(":")[2].split(">")[0]
        alt = self.variant.split(":")[2].split(">")[1]
        return chrom, pos, ref, alt

class VEPAnnotationsConsequence(models.Model):
    """
    The variant consequences used by VEP, described here:
    https://www.ensembl.org/info/genome/variation/prediction/predicted_data.html
    """
    id = models.AutoField(primary_key=True)
    consequence = models.CharField(max_length=50, unique=True)
    impact = models.ForeignKey("VEPAnnotationsImpact", on_delete=models.CASCADE)

    def format_display_term(self):
        return self.consequence.replace("_"," ")

class VEPAnnotationsImpact(models.Model):
    """
    The impact levels for the different VEP consequences, described here:
    https://www.ensembl.org/info/genome/variation/prediction/predicted_data.html
    """
    id = models.AutoField(primary_key=True)
    impact = models.CharField(max_length=20, unique=True)

class VEPAnnotationsExistingVariation(models.Model):
    """
    Existing Variations (e.g. rsids) as annotated by VEP
    """
    id = models.AutoField(primary_key=True)
    existing_variation = models.CharField(max_length=50, unique=True)

    # TODO methods to link out e.g. to dbsnp

class VEPAnnotationsPubmed(models.Model):
    """
    Pubmed IDs sourced from VEP
    """
    id = models.AutoField(primary_key=True)
    pubmed_id = models.CharField(max_length=10, unique=True)

    def format_pubmed_link(self):
        # create a link for the pubmed ID
        return f"https://pubmed.ncbi.nlm.nih.gov/{self.pubmed_id}/"

class VEPAnnotationsClinvar(models.Model):
    """
    Clinvar
    """
    #TODO add clnvarstat
    CLINVAR_CHOICES = (
        ("B", "Benign"),
        ("BLB", "Benign/Likely benign"),
        ("LB", "Likely benign"),
        ("U", "Uncertain significance"),
        ("LP", "Likely pathogenic"),
        ("PLP", "Pathogenic/Likely pathogenic"),
        ("P", "Pathogenic"),
        ("C", "Conflicting classifications of pathogenicity"),
        ("O", "Other")
    )
    #TODO change this to just clinsig and have it be a choice field
    id = models.AutoField(primary_key=True)
    clinvar_id = models.CharField(max_length=20, unique=True)
    clinvar_clinsig = models.CharField(max_length=3, choices=CLINVAR_CHOICES)

    def format_clinvar_link(self):
        return f"https://www.ncbi.nlm.nih.gov/clinvar/{self.clinvar_id}/"
    
class VEPAnnotationsCancerHotspots(models.Model):
    """
    Cancer hotspots information for a given somatic variant
    """
    id = models.AutoField(primary_key=True)
    cancer_hotspot = models.CharField(max_length=20, unique=True)

    def format_cancer_hotspots_link(self):
        # you currently can't go to the website for a specific variant, return the main link
        return "https://www.cancerhotspots.org/#/home"

class AbstractVEPAnnotations(models.Model):
    """
    Contains VEP annotation fields common to germline and somatic vep annotations
    VEP annotations are described here:
    https://www.ensembl.org/info/docs/tools/vep/vep_formats.html
    """
    id = models.AutoField(primary_key=True)
    consequence = models.ManyToManyField("VEPAnnotationsConsequence")
    transcript = models.ForeignKey("Transcript", on_delete=models.CASCADE)
    exon = models.CharField(max_length=20, null=True, blank=True)
    intron = models.CharField(max_length=10, null=True, blank=True)
    hgvsc = models.CharField(max_length=100, null=True, blank=True)
    hgvsp = models.CharField(max_length=100, null=True, blank=True)
    existing_variation = models.ManyToManyField("VEPAnnotationsExistingVariation")
    pubmed_id = models.ManyToManyField("VEPAnnotationsPubmed")

    class Meta:
        abstract = True

class GermlineVEPAnnotations(AbstractVEPAnnotations):
    """
    Adds germline-specific annotations (Clinvar)
    """
    #clinvar = models.ManyToManyField("VEPAnnotationsClinvar")

    #TODO unique together

class SomaticVEPAnnotations(AbstractVEPAnnotations):
    """
    Adds somatic-specific annotations (Cancer hotspots)
    """
    #cancer_hotspots = models.ForeignKey("VEPAnnotationsCancerHotspots", on_delete=models.CASCADE)

    #TODO unique_together

    

class AbstractVariantInstance(models.Model):
    """
    Abstract class for variant instance. 
    Stores the fields common to 
     - germline and somatic instances
     - SNVs, CNVs and SVs
     - checks
    """
    OUTCOME_CHOICES = (
        ('G', 'Genuine'),
        ('A', 'Artefact'),
        ('N', 'Not Analysed')
    )

    STATUS_CHOICES = (
        ('P','Pending'),
        ('C','Complete'),
    )
    
    id = models.AutoField(primary_key=True)
    patient_analysis = models.ForeignKey("PatientAnalysis", on_delete=models.CASCADE)
    gnomad_popmax_af = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    gnomad_nhomalt = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='P')
    decision = models.CharField(max_length=1, choices=OUTCOME_CHOICES, null=True, blank=True)
    
    class Meta:
        abstract = True
    
    @staticmethod
    def get_worst_modifier_from_vep_annotations(vep_annotations):
        impacts = []
        for vep_annotation in vep_annotations:
            consequences = vep_annotation.consequence.all()
            for consequence in consequences:
                impacts.append(consequence.impact.impact)
        impacts = list(set(impacts))
        if "HIGH" in impacts:
            return "HIGH"
        elif "MEDIUM" in impacts:
            return "MEDIUM"
        elif "LOW" in impacts:
            return "LOW"
        else:
            return "MODIFIER"
        
class AbstractSnvInstance(AbstractVariantInstance):
    """
    Abstract base class for SNVs and small indels
    """

    variant = models.ForeignKey("Variant", on_delete=models.CASCADE)
    ad = models.CharField(max_length=10)
    af = models.DecimalField(max_digits=7, decimal_places=6)
    dp = models.IntegerField()
    qual = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    max_splice_ai = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)

    class Meta:
        abstract = True

    @staticmethod
    def get_chrom_and_pos(variant_id):
        chrom = variant_id.split(":")[0]
        pos = int(variant_id.split(":")[1])
        return chrom, pos


class GermlineVariantInstance(AbstractSnvInstance):
    """
    Germline SNV or small indel
    """
    vep_annotations = models.ManyToManyField("GermlineVEPAnnotations")

    def display_in_tier_zero(self):
        variant_gene = self.vep_annotations.first().transcript.gene
        associated_panels = variant_gene.panels.all()
        # if any of the associated panels are in a tier 0 panel, display
        for panel in associated_panels:
            if panel in self.patient_analysis.indication.germline_panels_tier_zero.all():
                return True
        return False

    def display_in_tier_one(self):
        """
        Returns a Boolean for if a panel should be displayed in Tier 1
        """
        variant_gene = self.vep_annotations.first().transcript.gene
        associated_panels = variant_gene.panels.all()
        # if any of the associated panels are in a tier 1 panel, display
        for panel in associated_panels:
            if panel in self.patient_analysis.indication.germline_panels_tier_one.all():
                return True
        return False
        
    def display_in_tier_three(self):
        variant_gene = self.vep_annotations.first().transcript.gene
        associated_panels = variant_gene.panels.all()
        # if any of the associated panels are in a tier 3 panel, display
        for panel in associated_panels:
            if panel in self.patient_analysis.indication.germline_panels_tier_three.all():
                return True
        return False
    
    def force_display(self):
        """
        A potentially informative MNV could be split to multiple SNVs during annotation and we could lose information
        Function force-includes variants called +-2 bp (potentially same codon) irrespective of other filtering criteria outside of gene
        """
        # get the 2 closest variants to this one
        id_lower_limit = self.id - 1
        id_upper_limit = self.id + 1
        close_variants = GermlineVariantInstance.objects.filter(patient_analysis=self.patient_analysis, id__range=[id_lower_limit, id_upper_limit])

        # if we get an empty list there are no other variants, return False (but also this is weird)
        if len(close_variants) == 0:
            return False
        
        else:
            # get chrom and pos for this variant
            chrom, pos = self.get_chrom_and_pos(self.variant.variant)

            for variant in close_variants:
                close_chrom, close_pos = self.get_chrom_and_pos(variant.variant.variant)

                # if the variant is within 2bp, compare the consequences
                if chrom == close_chrom and abs(pos - close_pos) in [1, 2]:
                    if self.get_worst_modifier_from_vep_annotations(self.vep_annotations.all()) != "MODIFIER" or variant.get_worst_modifier_from_vep_annotations(variant.vep_annotations.all()) != "MODIFIER":
                        return True
            
            # otherwise the nearest variants are > 2bp away
            return False
        
    def get_all_checks(self):
        """
        Get all checks carried out on the variant for displaying
        """

        checks = []

        all_checks = GermlineIGVCheck.objects.filter(variant_instance__id = self.id).order_by('check_date')

        for check in all_checks:

            check_dict = {
                'decision': check.get_decision_display(),
                'user': check.user.username
            } 

            checks.append(check_dict)

        return checks
    
    def update_status(self):
        """
        Update status if last two checks are matching
        """

        all_checks = GermlineIGVCheck.objects.filter(variant_instance__id = self.id).order_by('-check_date')

        #if only one check, don't do anything, otherwise if the last two match, update status
        if len(all_checks) > 1:
            
            if all_checks[0].decision == all_checks[1].decision and all_checks[0].user != all_checks[1].user:

                #Don't want to complete if the decision is not analysed
                if all_checks[0].decision != "N":
                
                    self.decision = all_checks[0].decision
                    self.status = "C"
                    self.save()        

class SomaticVariantInstance(AbstractSnvInstance):
    """
    Somatic SNV or small indel
    """
    vep_annotations = models.ManyToManyField("SomaticVEPAnnotations")

    def display_in_tier_zero(self):
        variant_gene = self.vep_annotations.first().transcript.gene
        associated_panels = variant_gene.panels.all()
        # if any of the associated panels are in a tier 0 panel, display
        for panel in associated_panels:
            if panel in self.patient_analysis.indication.somatic_panels_tier_zero.all():
                return True
        return False

    def display_in_tier_one(self):
        """
        Returns a Boolean for if a panel should be displayed in Tier 1
        """
        variant_gene = self.vep_annotations.first().transcript.gene
        associated_panels = variant_gene.panels.all()
        # if any of the associated panels are in a tier 1 panel, display
        for panel in associated_panels:
            if panel in self.patient_analysis.indication.somatic_panels_tier_one.all():
                return True
        return False
        
    def display_in_tier_two(self):
        variant_gene = self.vep_annotations.first().transcript.gene
        associated_panels = variant_gene.panels.all()
        # if any of the associated panels are in a tier 2 panel, display
        for panel in associated_panels:
            if panel in self.patient_analysis.indication.somatic_panels_tier_two.all():
                return True
        return False
    
    def force_display(self):
        """
        A potentially informative MNV could be split to multiple SNVs during annotation and we could lose information
        Function force-includes variants called +-2 bp (potentially same codon) irrespective of other filtering criteria outside of gene
        """
        # get the 2 closest variants to this one
        id_lower_limit = self.id - 1
        id_upper_limit = self.id + 1
        close_variants = SomaticVariantInstance.objects.filter(patient_analysis=self.patient_analysis, id__range=[id_lower_limit, id_upper_limit])

        # if we get an empty list there are no other variants, return False (but also this is weird)
        if len(close_variants) == 0:
            return False
        
        else:
            # get chrom and pos for this variant
            chrom, pos = self.get_chrom_and_pos(self.variant.variant)
            for variant in close_variants:
                close_chrom, close_pos = self.get_chrom_and_pos(variant.variant.variant)

                # if the variant is within 2bp, force display should be true
                if chrom == close_chrom and abs(pos - close_pos) in [1, 2]:
                    if self.get_worst_modifier_from_vep_annotations(self.vep_annotations.all()) != "MODIFIER" or variant.get_worst_modifier_from_vep_annotations(variant.vep_annotations.all()) != "MODIFIER":
                        return True
            
            # otherwise the nearest variants are > 2bp away
            return False
        
    def get_all_checks(self):
        """
        Get all checks carried out on the variant for displaying
        """

        checks = []

        all_checks = SomaticIGVCheck.objects.filter(variant_instance__id = self.id).order_by('check_date')

        for check in all_checks:

            check_dict = {
                'decision': check.get_decision_display(),
                'user': check.user.username
            } 

            checks.append(check_dict)

        return checks

    def update_status(self):
        """
        Update status if last two checks are matching
        """

        all_checks = SomaticIGVCheck.objects.filter(variant_instance__id = self.id).order_by('-check_date')

        #if only one check, don't do anything, otherwise if the last two match and are by different users, update status
        if len(all_checks) > 1:
            
            if all_checks[0].decision == all_checks[1].decision and all_checks[0].user != all_checks[1].user:

                #Don't want to complete if the decision is not analysed
                if all_checks[0].decision != "N":
                
                    self.decision = all_checks[0].decision
                    self.status = "C"
                    self.save() 


class CnvSvType(models.Model):
    """
    Types of CNV and SV
    """
    id = models.AutoField(primary_key=True)
    type = models.CharField(max_length=50, unique=True)

class CnvSv(models.Model):
    """
    An individual CNV or SV (including individual breakpoints)
    """

    id = models.AutoField(primary_key=True)
    variant = models.CharField(max_length=200)
    genome_build = models.ForeignKey("GenomeBuild", on_delete=models.CASCADE)
    type = models.ForeignKey("CnvSvType", on_delete=models.CASCADE)
    svlen = models.IntegerField(null=True, blank=True)
    genes = models.ManyToManyField("Gene", related_name="cnv_sv")
    caller = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        unique_together = ["variant", "svlen"]

    def __str__(self):
        return f"{self.variant}"
    
    def get_all_genes(self):
        all_genes = self.genes.all()
        all_genes = [gene.gene for gene in all_genes]
        all_genes.sort()
        return list(set(all_genes))
    
class AbstractCnvInstance(AbstractVariantInstance):
    """
    Shared fields for germline and somatic CNVs
    """
    cnv = models.ForeignKey("CnvSv", on_delete=models.CASCADE)
    gt = models.CharField(max_length=10)
    cn = models.IntegerField()
    maf = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    ncn = models.IntegerField(null=True, blank=True)

    def display_genotype(self):
        return self.gt
    
    def display_in_panel_genes(self, tier_or_domain):
        cnv_genes = self.cnv.get_all_genes()
        all_genes_and_panels = self.patient_analysis.indication.get_all_genes_and_panels()
        genes_of_interest = all_genes_and_panels[tier_or_domain]["genes"]
        genes_in_panel = [gene for gene in cnv_genes if gene in genes_of_interest]
        return list(set(genes_in_panel))

class GermlineCnvInstance(AbstractCnvInstance):
    """
    Model for germline CNVs
    """
    vep_annotations = models.ManyToManyField("GermlineVEPAnnotations")

    def display_in_tier_zero(self):
        variant_genes = self.cnv.get_all_genes()
        all_genes_and_panels = self.patient_analysis.indication.get_all_genes_and_panels()
        indication_genes = all_genes_and_panels["germline_cnv_tier_zero"]["genes"]
        if any(gene in variant_genes for gene in indication_genes):
            return True
        else:
            return False

    def display_in_tier_one(self):
        """
        Returns a Boolean for if a panel should be displayed in Tier 1
        """
        variant_genes = self.cnv.get_all_genes()
        all_genes_and_panels = self.patient_analysis.indication.get_all_genes_and_panels()
        indication_genes = all_genes_and_panels["germline_cnv_tier_one"]["genes"]
        if any(gene in variant_genes for gene in indication_genes):
            return True
        else:
            return False
        
    def display_in_tier_three(self):
        variant_genes = self.cnv.get_all_genes()
        all_genes_and_panels = self.patient_analysis.indication.get_all_genes_and_panels()
        indication_genes = all_genes_and_panels["germline_cnv_tier_three"]["genes"]
        if any(gene in variant_genes for gene in indication_genes):
            return True
        else:
            return False

        #for testing 
        #return True

class SomaticCnvInstance(AbstractCnvInstance):
    """
    Model for somatic CNVs
    """
    vep_annotations = models.ManyToManyField("SomaticVEPAnnotations")

    def display_in_domain_zero(self):
        variant_genes = self.cnv.get_all_genes()
        all_genes_and_panels = self.patient_analysis.indication.get_all_genes_and_panels()
        indication_genes = all_genes_and_panels["somatic_cnv_domain_zero"]["genes"]
        if any(gene in variant_genes for gene in indication_genes):
            return True
        else:
            return False

    def display_in_domain_one(self):
        """
        Returns a Boolean for if a panel should be displayed in Tier 1
        """
        variant_genes = self.cnv.get_all_genes()
        all_genes_and_panels = self.patient_analysis.indication.get_all_genes_and_panels()
        indication_genes = all_genes_and_panels["somatic_cnv_domain_one"]["genes"]
        if any(gene in variant_genes for gene in indication_genes):
            return True
        else:
            return False
        
    def display_in_domain_two(self):
        variant_genes = self.cnv.get_all_genes()
        all_genes_and_panels = self.patient_analysis.indication.get_all_genes_and_panels()
        indication_genes = all_genes_and_panels["somatic_cnv_domain_two"]["genes"]
        if any(gene in variant_genes for gene in indication_genes):
            return True
        else:
            return False
    
class AbstractSvInstance(AbstractVariantInstance):
    """
    Shared fields for germline and somatic SVs
    """
    sv = models.ForeignKey("CnvSv", on_delete=models.CASCADE)
    pr = models.CharField(max_length=50, null=True, blank=True)
    sr = models.CharField(max_length=50, null=True, blank=True)
    vf = models.CharField(max_length=50, null=True, blank=True)
    imprecise = models.BooleanField(default=False)
    somatic_score = models.IntegerField(null=True, blank=True)

    def display_in_panel_genes(self, tier_or_domain):
        sv_genes = self.sv.get_all_genes()
        all_genes_and_panels = self.patient_analysis.indication.get_all_genes_and_panels()
        genes_of_interest = all_genes_and_panels[tier_or_domain]["genes"]
        genes_in_panel = [gene for gene in sv_genes if gene in genes_of_interest]
        return list(set(genes_in_panel))

class GermlineSvInstance(AbstractSvInstance):
    """
    Model for germline SVs
    """
    vep_annotations = models.ManyToManyField("GermlineVEPAnnotations")

    def display_in_tier_zero(self):
        variant_genes = self.sv.get_all_genes()
        all_genes_and_panels = self.patient_analysis.indication.get_all_genes_and_panels()
        indication_genes = all_genes_and_panels["germline_cnv_tier_zero"]["genes"]
        if any(gene in variant_genes for gene in indication_genes):
            return True
        else:
            return False

    def display_in_tier_one(self):
        """
        Returns a Boolean for if a panel should be displayed in Tier 1
        """
        variant_genes = self.sv.get_all_genes()
        all_genes_and_panels = self.patient_analysis.indication.get_all_genes_and_panels()
        indication_genes = all_genes_and_panels["germline_cnv_tier_one"]["genes"]
        if any(gene in variant_genes for gene in indication_genes):
            return True
        else:
            return False
        
    def display_in_tier_three(self):
        variant_genes = self.sv.get_all_genes()
        all_genes_and_panels = self.patient_analysis.indication.get_all_genes_and_panels()
        indication_genes = all_genes_and_panels["germline_cnv_tier_three"]["genes"]
        if any(gene in variant_genes for gene in indication_genes):
            return True
        else:
            return False

class SomaticSvInstance(AbstractSvInstance):
    """
    Model for somatic SVs
    """
    vep_annotations = models.ManyToManyField("SomaticVEPAnnotations")

    def display_in_domain_zero(self):
        variant_genes = self.sv.get_all_genes()
        all_genes_and_panels = self.patient_analysis.indication.get_all_genes_and_panels()
        indication_genes = all_genes_and_panels["somatic_cnv_domain_zero"]["genes"]
        if any(gene in variant_genes for gene in indication_genes):
            return True
        else:
            return False

    def display_in_domain_one(self):
        """
        Returns a Boolean for if a panel should be displayed in Tier 1
        """
        variant_genes = self.sv.get_all_genes()
        all_genes_and_panels = self.patient_analysis.indication.get_all_genes_and_panels()
        indication_genes = all_genes_and_panels["somatic_cnv_domain_one"]["genes"]
        if any(gene in variant_genes for gene in indication_genes):
            return True
        else:
            return False
        
    def display_in_domain_two(self):
        variant_genes = self.sv.get_all_genes()
        all_genes_and_panels = self.patient_analysis.indication.get_all_genes_and_panels()
        indication_genes = all_genes_and_panels["somatic_cnv_domain_two"]["genes"]
        if any(gene in variant_genes for gene in indication_genes):
            return True
        else:
            return False

class Fusion(models.Model):
    """
    A gene fusion (2 breakpoints)
    """
    id = models.AutoField(primary_key=True)
    fusion_name = models.CharField(max_length=200)
    breakpoint1 = models.ForeignKey("CnvSv", on_delete=models.CASCADE, related_name="breakpoint1")
    breakpoint2 = models.ForeignKey("CnvSv", on_delete=models.CASCADE, related_name="breakpoint2")

    class Meta:
        unique_together = ["breakpoint1", "breakpoint2"]

class FusionInstance(models.Model):
    """
    A fusion instance for the somatic sample only
    """
    id = models.AutoField(primary_key=True)
    fusion = models.ForeignKey("Fusion", on_delete=models.CASCADE)


##############
### Checks ###
##############

class AbstractVariantChecks(models.Model):
    """
    Abstract class for variant checks. Stores the fields common to all checks
    """

    OUTCOME_CHOICES = (
        ('G', 'Genuine'),
        ('A', 'Artefact'),
        ('N', 'Not Analysed'),
    )

    decision = models.CharField(max_length=1, choices = OUTCOME_CHOICES, blank=True, null=True)
    user = models.ForeignKey('auth.User', on_delete=models.PROTECT, blank=True, null=True)
    check_date = models.DateTimeField(blank=True, null=True)
        
    class Meta:
        abstract = True

class GermlineIGVCheck(AbstractVariantChecks):
    """
    IGV checks for germline variants
    """
    
    variant_instance = models.ForeignKey(GermlineVariantInstance, on_delete=models.CASCADE)

class SomaticIGVCheck(AbstractVariantChecks):
    """
    IGV checks for somatic variants
    """

    variant_instance = models.ForeignKey(SomaticVariantInstance, on_delete=models.CASCADE)



