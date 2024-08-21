from django.contrib import admin

from .models import *

"""
Add SWGS models to the Django admin page
Fields that can be searched by are defined in the search_fields variable
Fields displayed on the admin page are defined in the list_display variable
"""

class PanelInLine(admin.TabularInline):
    model = Panel.genes.through

class GeneAdmin(admin.ModelAdmin):
    list_display = ["gene"]
    search_fields = ["gene"]
    inlines = [PanelInLine]

admin.site.register(Gene, GeneAdmin)

class TranscriptAdmin(admin.ModelAdmin):
    list_display = ["transcript", "gene"]
    search_fields = ["transcript", "gene"]

admin.site.register(Transcript, TranscriptAdmin)

class PatientAdmin(admin.ModelAdmin):
    list_display = ["nhs_number"]
    search_fields = ["nhs_number"]

admin.site.register(Patient, PatientAdmin)

class SampleAdmin(admin.ModelAdmin):
    list_display = ["sample_id"]
    search_fields = ["sample_id"]

admin.site.register(Sample, SampleAdmin)

class IndicationAdmin(admin.ModelAdmin):
    filter_horizontal = ["germline_panels_tier_zero", "germline_panels_tier_one", "germline_panels_tier_three"]
    list_display = ["indication", "indication_pretty_print", "lims_code"]
    search_fields = ["indication", "indication_pretty_print", "lims_code"]

admin.site.register(Indication, IndicationAdmin)

class PanelAdmin(admin.ModelAdmin):
    list_display = ["panel_name", "panel_version", "panel_approved"]
    search_fields = ["panel_name"]

admin.site.register(Panel, PanelAdmin)

class RunAdmin (admin.ModelAdmin):
    list_display = ["run", "worksheet"]
    search_fields = ["run", "worksheet"]

admin.site.register(Run, RunAdmin)

class PatientAnalysisAdmin(admin.ModelAdmin):
    list_display = ["patient", "get_tumour_sample", "get_germline_sample", "get_indication", "get_run"]
    search_fields = ["patient", "tumour_sample", "germline_sample", "run"]

    def get_tumour_sample(self, obj):
        return obj.tumour_sample.sample_id
    get_tumour_sample.short_description = "Tumour Sample"
    get_tumour_sample.admin_order_field = "tumour_sample__sample_id"

    def get_germline_sample(self, obj):
        return obj.germline_sample.sample_id
    get_germline_sample.short_description = "Germline Sample"
    get_germline_sample.admin_order_field = "germline_sample__sample_id"
    
    def get_indication(self, obj):
        return obj.indication.indication
    get_indication.short_description = "Indication"
    get_indication.admin_order_field = "indication__indication"

    def get_run(self, obj):
        return obj.run.run
    get_run.short_description = "Run"
    get_run.admin_order_field = "run__run"

admin.site.register(PatientAnalysis, PatientAnalysisAdmin)

class QCSomaticVAFDistributionAdmin(admin.ModelAdmin):
    list_display = ["id", "status", "low_vaf_proportion"]
    search_fields = ["status"]

admin.site.register(QCSomaticVAFDistribution, QCSomaticVAFDistributionAdmin)

class QCTumourInNormalContaminationAdmin(admin.ModelAdmin):
    list_display = ["id", "status"]
    search_fields = ["status"]

admin.site.register(QCTumourInNormalContamination, QCTumourInNormalContaminationAdmin)

class QCGermlineCNVQualityAdmin(admin.ModelAdmin):
    list_display = ["id", "status", "passing_cnv_count", "passing_fraction", "log_loss_gain"]
    search_fields = ["status"]

admin.site.register(QCGermlineCNVQuality, QCGermlineCNVQualityAdmin)

class QCNTCContaminationAdmin(admin.ModelAdmin):
    list_display = ["id", "status", "ntc_contamination"]
    search_fields = ["status"]

admin.site.register(QCNTCContamination, QCNTCContaminationAdmin)

class GenomeBuildAdmin(admin.ModelAdmin):
    list_display = ["genome_build"]
    search_fields = ["genome_build"]

admin.site.register(GenomeBuild, GenomeBuildAdmin)

class VariantAdmin(admin.ModelAdmin):
    list_display = ["variant", "genome_build"]
    search_fields = ["variant"]

admin.site.register(Variant, VariantAdmin)

class GermlineVariantInstanceAdmin(admin.ModelAdmin):
    filter_horizontal = ["vep_annotations"]
    list_display = ["id", "get_variant", "patient_analysis", "af"]
    search_fields = ["id", "variant", "patient_analysis"]

    def get_variant(self, obj):
        return obj.variant.variant

admin.site.register(GermlineVariantInstance, GermlineVariantInstanceAdmin)

class SomaticVariantInstanceAdmin(admin.ModelAdmin):
    filter_horizontal = ["vep_annotations"]
    list_display = ["variant", "patient_analysis", "ad", "af"]
    search_fields = ["variant", "patient_analysis"]

admin.site.register(SomaticVariantInstance, SomaticVariantInstanceAdmin)

class VEPAnnotationsConsequenceAdmin(admin.ModelAdmin):
    list_display = ["consequence", "get_impact"]
    search_fields = ["consequence"]

    def get_impact(self, obj):
        return obj.impact.impact

admin.site.register(VEPAnnotationsConsequence, VEPAnnotationsConsequenceAdmin)

class VEPAnnotationsImpactAdmin(admin.ModelAdmin):
    list_display = ["impact"]
    search_fields = ["impact"]

admin.site.register(VEPAnnotationsImpact, VEPAnnotationsImpactAdmin)

class VEPAnnotationsExistingVariationAdmin(admin.ModelAdmin):
    list_display = ["existing_variation"]
    search_fields = ["existing_variation"]

admin.site.register(VEPAnnotationsExistingVariation, VEPAnnotationsExistingVariationAdmin)

class VEPAnnotationsPubmedAdmin(admin.ModelAdmin):
    list_display = ["pubmed_id"]
    search_fields = ["pubmed_id"]

admin.site.register(VEPAnnotationsPubmed, VEPAnnotationsPubmedAdmin)

class VEPAnnotationsClinvarAdmin(admin.ModelAdmin):
    list_display = ["clinvar_id", "clinvar_clinsig"]
    search_fields = ["clinvar_id"]

admin.site.register(VEPAnnotationsClinvar, VEPAnnotationsClinvarAdmin)

class GermlineVEPAnnotationsAdmin(admin.ModelAdmin):
    filter_horizontal = ["pubmed_id", "existing_variation", "consequence"]
    list_display = ["id", "hgvsc", "hgvsp", "exon", "intron"]
    search_fields = ["id", "hgvsc", "hgvsp"]

admin.site.register(GermlineVEPAnnotations, GermlineVEPAnnotationsAdmin)

class SomaticVEPAnnotationsAdmin(admin.ModelAdmin):
    filter_horizontal = ["pubmed_id", "existing_variation", "consequence"]
    list_display = ["hgvsc", "hgvsp", "exon", "intron"]
    search_fields = ["hgvsc", "hgvsp"]

admin.site.register(SomaticVEPAnnotations, SomaticVEPAnnotationsAdmin)

#TODO add the rest of the models and neaten up all the displays etc.