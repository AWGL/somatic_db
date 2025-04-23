from django.contrib import admin
from polymorphic.admin import PolymorphicParentModelAdmin, PolymorphicChildModelAdmin, PolymorphicChildModelFilter
from .models import *


@admin.register(Guideline)
class GuidelineAdmin(admin.ModelAdmin):
    search_fields = ["guideline"]
    filter_horizontal = ["criteria", "final_classifications"]

@admin.register(ClassificationCriteria)
class ClassificationCriteriaAdmin(admin.ModelAdmin):
    search_fields = ["code", "strength"]

@admin.register(ClassificationCriteriaCode)
class ClassificationCriteriaCodeAdmin(admin.ModelAdmin):
    search_fields = ["code"]
    list_display = ["code", "pathogenic_or_benign", "category", "paired_criteria"]

@admin.register(ClassificationCriteriaStrength)
class ClassificationCriteriaStrengthAdmin(admin.ModelAdmin):
    search_fields = ["strength"]
    list_display = ["strength", "shorthand", "evidence_points"]

@admin.register(ClassificationCriteriaCategory)
class ClassificationCriteriaCategoryAdmin(admin.ModelAdmin):
    search_fields = ["category"]

@admin.register(TumourSubtype)
class CategorySortOrderAdmin(admin.ModelAdmin):
    search_fields = ["name"]

@admin.register(CategorySortOrder)
class CategorySortOrderAdmin(admin.ModelAdmin):
    search_fields = ["guideline", "category"]

@admin.register(ClassifyVariant)
class ClassifyVariantAdmin(admin.ModelAdmin):
    search_fields = ["gene", "hgvs_c", "hgvs_p", "genomic_coords", "genome_build"]

@admin.register(ClassifyVariantInstance)
class ClassifyVariantInstanceAdmin(PolymorphicParentModelAdmin):
    base_model = ClassifyVariantInstance
    child_models = (AnalysisVariantInstance, SWGSGermlineVariantInstance, SWGSSomaticVaraintInstance, ManualVariantInstance)
    list_filter = (PolymorphicChildModelFilter,)

class ClassifyVariantInstanceChildAdmin(PolymorphicChildModelAdmin):
    base_model = ClassifyVariantInstance

@admin.register(AnalysisVariantInstance)
class AnalysisVariantInstanceAdmin(ClassifyVariantInstanceChildAdmin):
    base_model = AnalysisVariantInstance

@admin.register(SWGSGermlineVariantInstance)
class SWGSGermlineVariantInstanceAdmin(ClassifyVariantInstanceChildAdmin):
    base_model = SWGSGermlineVariantInstance

@admin.register(SWGSSomaticVaraintInstance)
class SWGSSomaticVariantInstanceAdmin(ClassifyVariantInstanceChildAdmin):
    base_model = SWGSSomaticVaraintInstance

@admin.register(ManualVariantInstance)
class ManualVariantInstanceAdmin(ClassifyVariantInstanceChildAdmin):
    base_model = ManualVariantInstance

@admin.register(Check)
class CheckAdmin(admin.ModelAdmin):
    search_fields = ["classification"]

@admin.register(CodeAnswer)
class CodeAnswerAdmin(admin.ModelAdmin):
    search_fields = ["code", "check_object"]

@admin.register(FinalClassification)
class FinalClassificationAdmin(admin.ModelAdmin):
    search_fields = ["final_classification"]
    list_display = ["final_classification", "minimum_score", "review_period"]