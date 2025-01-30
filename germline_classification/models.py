from django.db import models
from django.contrib.auth.models import User
from polymorphic.models import PolymorphicModel

from auditlog.registry import auditlog

from analysis.models import VariantPanelAnalysis
from swgs.models import GermlineVariantInstance

# Add a higher level model which is for a given variant, all of the classifications

class VariantClassification(PolymorphicModel):
    """
    We need to be able to link variant instances from the different apps (SWGS/Analysis)
    Polymorphic model lets us use different models as foreign keys cleanly
    and retains the information about where they're from
    """
    id = models.AutoField(primary_key=True)
    classification = models.ForeignKey("Classification", on_delete=models.CASCADE)

class AnalysisVariantClassification(VariantClassification):
    """
    Variant classifications for samples from the Analysis app
    """
    origin = "Analysis"
    variant_instance = models.ForeignKey(VariantPanelAnalysis, on_delete=models.CASCADE)

    def display_variant_info(self):

        variant = self.variant_instance.variant.variant
        hgvsc = self.variant_instance.hgvs_c
        hgvsp = self.variant_instance.hgvs_p

        return f"{variant} | {hgvsc} | {hgvsp}"

    def display_assay_and_panel(self):

        assay_choices = {
            '1', 'TSO500 DNA',
            '2', 'TSO500 RNA',
            '3', 'TSO500 ctDNA',
            '4', 'GeneRead CRM',
            '5', 'GeneRead BRCA'
        }

        assay = assay_choices[self.variant_instance.sample_analysis.panel.assay]
        panel = self.variant_instance.sample_analysis.panel.panel_name

        return f"{assay} {panel}"

class SWGSVariantClassification(VariantClassification):
    """
    Variant classificaitons for samples from the SWGS app
    """
    origin = "WGS"
    variant_instance = models.ForeignKey(GermlineVariantInstance, on_delete=models.CASCADE)

    def display_variant_info(self):

        variant = self.variant_instance.variant.variant
        hgvsc, hgvsp, gene = self.variant_instance.get_default_hgvs_nomenclature()

        return f"{variant} | {hgvsc} | {hgvsp}"

    def display_assay_and_panel(self):

        assay = "WGS"
        panel = self.variant_instance.patient_analysis.indication.indication

        return f"{assay} {panel}"

class ClassificationCriteriaStrength(models.Model):
    """
    Strengths at which the ACMG/ACGS criteria can be applied at
    """
    id = models.AutoField(primary_key=True)
    strength = models.CharField(max_length=20)
    evidence_points = models.IntegerField()

    class Meta:
        unique_together = ["strength", "evidence_points"]

    def __str__(self):
        return f"{self.strength} {str(self.evidence_points)}"

class ClassificationCriteriaCode(models.Model):
    """
    Codes that can be applied in the ACMG/ACGS criteria
    """
    id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=10, unique=True)
    pathogenic_or_benign = models.CharField(max_length=1)
    description = models.TextField(null=True, blank=True)
    links = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.code

class ClassificationCriteria(models.Model):
    """
    All available combinations of codes and strengths
    """
    id = models.AutoField(primary_key=True)
    code = models.ForeignKey("ClassificationCriteriaCode", on_delete=models.CASCADE)
    strength = models.ForeignKey("ClassificationCriteriaStrength", on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ["code", "strength"]

    def form_display(self):
        return f"{self.code.code}_{self.strength.strength}"

class Classification(models.Model):
    """
    The classification criteria applied for a single variant
    """
    id = models.AutoField(primary_key=True)
    criteria_applied = models.ManyToManyField("ClassificationCriteria", related_name="criteria_applied")
    user = models.ForeignKey('auth.User', on_delete=models.PROTECT, blank=True, null=True)
    signoff_time = models.DateTimeField(blank=True, null=True)
    complete = models.BooleanField(default=False)
    diagnostic = models.BooleanField(default=False)

    def get_codes_strengths_and_scores_applied(self):
        """
        Get lists of pathogenic and benign codes for downstream wrangling
        """

        all_criteria_applied = self.criteria_applied.all()
        pathogenic_criteria = []
        benign_criteria = []
        for criterion in all_criteria_applied:
            c = {
                "code": criterion.code.code,
                "strength": criterion.strength.strength,
                "score": criterion.strength.evidence_points
            }
            if criterion.code.pathogenic_or_benign == "P":
                pathogenic_criteria.append(c)
            else:
                benign_criteria.append(c)
        
        return pathogenic_criteria, benign_criteria
    
    @staticmethod
    def get_all_codes(pathogenic_criteria, benign_criteria):
        all_codes = []
        for criterion in pathogenic_criteria:
            all_codes.append(criterion["code"])
        for criterion in benign_criteria:
            all_codes.append(criterion["code"])
        return all_codes
    
    @staticmethod
    def code_incompatibility_warnings(all_codes):
        warnings = []

        if "PVS1" in all_codes:
            if any(["PM1", "PM4", "PP2", "PP3"]) in all_codes:
                warning = "WARNING: PVS1 should not be applied with PM1, PM4, PP2 or PP3"
                warnings.append(warning)
            
        if "PS1" in all_codes:
            if "PM4" in all_codes:
                warning = "WARNING: PS1 should not be applied with PM4"
                warnings.append(warning)
        
        if any(["PS2", "PM6"]) in all_codes:
            if "PP4" in all_codes:
                warning = """INFO: If PS2/PM6 is applied, the specificity of that patient's phenotype to the relevant disorder, should be captured using
                            an increased strength of PS2/PM6, rather than applying a separate and additional line of evidence within PP4."""
        
        if "PM1" in all_codes:
            if any(["PM5", "PP2"]) in all_codes:
                warning = """INFO: Do not use the same evidence to code PM1 and PM5 or PP2, but the two codes can be used together if each
                            supported by independent evidence."""
                warnings.append(warning)
        
        if "PM4" in all_codes:
            if "PVS1" in all_codes:
                warning = "PM4 should not be applied with PVS1"
                warnings.append(warning)
        
        if "PM5" in all_codes:
            if "PM1" in all_codes:
                warning = """Do not use the same evidence to apply PM1 and PM5, but the two codes can be used together if each supported
                            by independent evidence."""
                warnings.append(warning)
        
        if len(warnings) == 0:
            return False, []
        else:
            return True, warnings

    
    @staticmethod
    def format_criteria_acgs_2020(pathogenic_criteria, benign_criteria):
        strength_dict = {
            "benign": {"standalone": 0,
                       "strong": 0,
                       "moderate": 0,
                       "supporting": 0,
                       "total": 0},
            "pathogenic" : {"very_strong": 0,
                            "strong": 0,
                            "moderate": 0,
                            "supporting": 0,
                            "total": 0},
        }

        for criterion in pathogenic_criteria:
            strength_dict["pathogenic"]["total"] += 1
            strength_dict["pathogenic"][criterion["strength"]] += 1
        
        for criterion in benign_criteria:
            strength_dict["benign"]["total"] += 1
            strength_dict["benign"][criterion["strength"]] += 1

        return strength_dict

    @staticmethod
    def classify_acgs_2020(strength_dict):
        """
        Calculate the final classification using the ACGS 2020 guidelines
        """
        # if there's a mix of pathogenic and benign, set as VUS (scientists can override)
        if strength_dict["pathogenic"]["total"] > 0 and strength_dict["benign"]["total"] > 0:
            return "VUS"
        
        # handle pathogenic variants
        if strength_dict["pathogenic"]["very_strong"] >= 1 and \
            (
                strength_dict["pathogenic"]["strong"] >= 1 or \
                strength_dict["pathogenic"]["moderate"] >= 1 or \
                strength_dict["pathogenic"]["supporting"] >= 2
            ):
            return "pathogenic"
        
        if strength_dict["pathogenic"]["strong"] >= 3:
            return "pathogenic"
        
        if strength_dict["pathogenic"]["strong"] >=2 and \
            (
                strength_dict["pathogenic"]["moderate"] >= 1 or \
                strength_dict["pathogenic"]["supporting"] >= 2
            ):
            return "pathogenic"
        
        if strength_dict["pathogenic"]["strong"] and \
            (
                strength_dict["pathogenic"]["moderate"] >= 3 or \
                (
                    strength_dict["pathogenic"]["moderate"] >= 2 and \
                    strength_dict["pathogenic"]["supporting"] >= 2
                ) or \
                (
                    strength_dict["pathogenic"]["moderate"] >= 1 and \
                    strength_dict["pathogenic"]["supporting"] >= 4
                )
            ):
            return "pathogenic"
        
        if strength_dict["pathogenic"]["strong"] >= 2:
            return "likely_pathogenic"
        
        if strength_dict["pathogenic"]["strong"] == 1 and \
            (
                strength_dict["pathogenic"]["moderate"] >= 1 or \
                strength_dict["pathogenic"]["supporting"] >= 2
            ):
            return "likely_pathogenic"
    
        if strength_dict["pathogenic"]["moderate"] >= 3 or \
            (
                strength_dict["pathogenic"]["moderate"] >= 2 and \
                strength_dict["pathogenic"]["supporting"] >= 2
            ) or \
            (
                strength_dict["pathogenic"]["moderate"] == 1 and \
                strength_dict["pathogenic"]["supporting"] >= 4
            ):
            return "likely_pathogenic"
        
        # handle benign variants
        if strength_dict["benign"]["standalone"] == 1:
            return "benign"
        
        if strength_dict["benign"]["strong"] >= 2:
            return "benign"
        
        if strength_dict["benign"]["strong"] == 1 and \
            strength_dict["benign"]["supporting"] >= 1:
            return "likely_benign"
        
        if strength_dict["benign"]["supporting"] >= 2:
            return "likely_benign"
        
        # everything else is a VUS
        return "VUS"
            

    @staticmethod
    def get_total_score(pathogenic_criteria, benign_criteria):
        # add the two lists togther
        all_criteria = pathogenic_criteria + benign_criteria
        total_score = 0
        for criterion in all_criteria:
            total_score += criterion["score"]
        return total_score
    
    @staticmethod
    def classify_acgs_2024(total_score: int):
        """
        Calculate the final classification using the ACGS 2024 guidelines
        https://www.acgs.uk.com/media/12533/uk-practice-guidelines-for-variant-classification-v12-2024.pdf
        """
        if total_score >= 10:
            classification = "pathogenic"
        elif total_score >= 6:
            classification = "likely_pathogenic"
        elif total_score >= 4:
            classification = "vus_hot"
        elif total_score >= 2:
            classification = "vus_warm"
        elif total_score >= 0:
            classification = "vus_cold"
        elif total_score >= -6:
            classification = "likely_benign"
        else:
            classification = "benign"
        return classification
    
    def perform_classification(self):
        """
        Performs classification according to the ACGS 2024 guidelines
        """
        pathogenic_codes, benign_codes = self.get_codes_strengths_and_scores_applied()
        total_score = self.get_total_score(pathogenic_codes, benign_codes)
        classification = self.classify_acgs_2024(total_score)
        classification = classification.replace("_", " ")
        return classification.title(), total_score
