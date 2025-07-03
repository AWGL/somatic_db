from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import *


"""
Add each model to the Django admin page. 
Fields that can be searched by are defined in the search_fields variable
Fields displayed on the admin page are defined in the list_display variable

"""

# add user settings field to user admin page
class UserSettingsInline(admin.StackedInline):
    model = UserSettings
    can_delete = False
    verbose_name_plural = 'User Settings'


class UserAdmin(BaseUserAdmin):
    inlines = [UserSettingsInline]

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


class RunAdmin(admin.ModelAdmin):
    search_fields = ['run_id']

admin.site.register(Run, RunAdmin)


class WorksheetAdmin(admin.ModelAdmin):
    list_display = ('ws_id', 'run', 'assay')
    search_fields = ['ws_id', 'run__run_id', 'assay']

admin.site.register(Worksheet, WorksheetAdmin)


class SampleAdmin(admin.ModelAdmin):
    list_display = ('sample_id', 'sample_name', 'tumour_content')
    search_fields = ['sample_id', 'sample_name', 'tumour_content']

admin.site.register(Sample, SampleAdmin)


class PanelAdmin(admin.ModelAdmin):
    list_display = ('id', 'panel_name', 'pretty_print', 'version', 'live', 'genome_build', 'assay', 'show_snvs', 'show_fusions',)
    search_fields = ['id', 'panel_name', 'pretty_print', 'version', 'live', 'genome_build', 'assay', 'show_snvs', 'show_fusions',]

admin.site.register(Panel, PanelAdmin)


class SampleAnalysisAdmin(admin.ModelAdmin):
    list_display = ('id', 'worksheet', 'sample', 'get_panel')
    search_fields = ['id', 'worksheet__ws_id', 'sample__sample_id', 'panel__panel_name']

    # get panel name rather than panel ID
    def get_panel(self, obj):
        return obj.panel.panel_name
    get_panel.short_description = 'Panel'
    get_panel.admin_order_field = 'panel__panel_name'

admin.site.register(SampleAnalysis, SampleAnalysisAdmin)


class CheckAdmin(admin.ModelAdmin):
    list_display = ('id', 'analysis', 'status', 'user')
    search_fields = ['id', 'analysis__id', 'user__username']
    # can't search by status because of choice field

admin.site.register(Check, CheckAdmin)


class VariantAdmin(admin.ModelAdmin):
    list_display = ('id', 'variant', 'genome_build')
    search_fields = ['id', 'variant', 'genome_build']

admin.site.register(Variant, VariantAdmin)


class VariantInstanceAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_sample', 'get_var', 'gene', 'hgvs_c', 'hgvs_p', 'vaf', 'final_decision')
    # cant search by vaf as its a class function
    # can't search by final decision because of choice field
    search_fields = ['id', 'sample__sample_id', 'variant__variant', 'gene', 'hgvs_c', 'hgvs_p',]

    # get sample name rather than sample ID
    def get_sample(self, obj):
        return obj.sample.sample_id
    get_sample.short_description = 'Sample'
    get_sample.admin_order_field = 'sample__sample_id'

    # get variant rather than variant ID
    def get_var(self, obj):
        return obj.variant.variant
    get_var.short_description = 'variant'
    get_var.admin_order_field = 'variant__variant'

admin.site.register(VariantInstance, VariantInstanceAdmin)


class VariantPanelAnalysisAdmin(admin.ModelAdmin):
    list_display = ('id', 'sample_analysis', 'variant_instance')
    search_fields = ['id', 'sample_analysis__id', 'variant_instance__id']

admin.site.register(VariantPanelAnalysis, VariantPanelAnalysisAdmin)


class VariantCheckAdmin(admin.ModelAdmin):
    list_display = ('id', 'variant_analysis', 'check_object', 'decision')
    search_fields = ['id', 'variant_analysis__id', 'check_object__id',]
    # can't search by decision because of choice field

admin.site.register(VariantCheck, VariantCheckAdmin)


class VariantListAdmin(admin.ModelAdmin):
    list_display = ('name', 'list_type', 'genome_build', 'assay')
    search_fields = ['name',]
    # can't search by list_type because of choice field

admin.site.register(VariantList, VariantListAdmin )


class VariantToVariantListAdmin(admin.ModelAdmin):
    list_display = ('id', 'variant_list', 'variant', 'fusion', 'classification', 'vaf_cutoff')
    search_fields = ['id', 'variant_list__name', 'variant__genomic_37', 'classification']

admin.site.register(VariantToVariantList, VariantToVariantListAdmin)


class GeneAdmin(admin.ModelAdmin):
    search_fields = ['gene']

admin.site.register(Gene, GeneAdmin)


class GeneCoverageAnalysisAdmin(admin.ModelAdmin):
    list_display = ('id', 'sample', 'gene', 'av_coverage', 'percent_100x', 'percent_135x', 'percent_270x', 'percent_500x', 'percent_1000x')
    search_fields = ['id', 'sample__id', 'gene__gene', 'av_coverage', 'percent_100x', 'percent_135x', 'percent_270x', 'percent_500x', 'percent_1000x']

admin.site.register(GeneCoverageAnalysis, GeneCoverageAnalysisAdmin )


class RegionCoverageAnalysisAdmin(admin.ModelAdmin):
    list_display = ('id', 'gene', 'hgvs_c', 'genomic', 'average_coverage', 'percent_100x', 'percent_135x', 'percent_270x', 'percent_500x', 'percent_1000x')
    search_fields = ['id', 'gene__id', 'hgvs_c', 'average_coverage', 'percent_100x', 'percent_135x', 'percent_270x', 'percent_500x', 'percent_1000x']
    # cant search by genomic as its a class function

admin.site.register(RegionCoverageAnalysis, RegionCoverageAnalysisAdmin)


class GapAnalysisAdmin(admin.ModelAdmin):
    list_display = ('id', 'gene', 'hgvs_c', 'genomic')
    search_fields = ['id', 'gene__id', 'hgvs_c']
    # cant search by genomic as its a class function

admin.site.register(GapsAnalysis, GapAnalysisAdmin)


class FusionAdmin(admin.ModelAdmin):
    list_display = ('id', 'fusion_genes', 'left_breakpoint', 'right_breakpoint')
    search_fields = ['id', 'fusion_genes', 'left_breakpoint', 'right_breakpoint']

admin.site.register(Fusion, FusionAdmin)


class FusionAnalysisAdmin(admin.ModelAdmin):
    list_display = ('id', 'sample', 'fusion_genes', 'hgvs', 'fusion_supporting_reads', 'ref_reads_1', 'ref_reads_2', 'final_decision')
    search_fields = ['id', 'sample__id', 'fusion_genes__id', 'hgvs', 'fusion_supporting_reads', 'ref_reads_1', 'ref_reads_2',]
    # can't search by final decision because of choice field

admin.site.register(FusionAnalysis, FusionAnalysisAdmin)


class FusionCheckAdmin(admin.ModelAdmin):
    list_display = ('id', 'fusion_analysis', 'check_object', 'decision')
    search_fields = ['id', 'fusion_analysis__id', 'check_object__id',]
    # can't search by decision because of choice field

admin.site.register(FusionCheck, FusionCheckAdmin)


class FusionPanelAnalysisAdmin(admin.ModelAdmin):
    list_display = ('id', 'sample_analysis', 'fusion_instance')
    search_fields = ['id', 'sample_analysis__id', 'fusion_instance__id']

admin.site.register(FusionPanelAnalysis, FusionPanelAnalysisAdmin)
