from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone
from django.template.defaultfilters import slugify
from polymorphic.models import PolymorphicModel

import yaml
import os
from collections import OrderedDict
import datetime
import re

from analysis.models import VariantPanelAnalysis
from swgs.models import GermlineVariantInstance, SomaticVariantInstance


class Guideline(models.Model):
    """
    Model to store which guidelines are being used
    """

    SOMATIC_OR_GERMLINE_CHOICES = (
        ("S", "somatic"),
        ("G", "germline")
    )

    guideline = models.CharField(max_length=200, unique=True)
    criteria = models.ManyToManyField("ClassificationCriteria", related_name="guideline")
    sort_order = models.ManyToManyField("ClassificationCriteriaCategory", through="CategorySortOrder")
    somatic_or_germline = models.CharField(max_length=1, choices=SOMATIC_OR_GERMLINE_CHOICES)
    final_classifications = models.ManyToManyField('FinalClassification', related_name="guidelines")
    signed_off_group = models.ForeignKey("auth.Group", on_delete=models.PROTECT, blank=True, null=True, related_name="guideline")

    def __str__(self):
        return self.guideline
    
    def create_final_classification_ordered_dict(self):
        """
        Converts the final classificaiton information in to an ordered dict to work with the check model classification function
        """
        final_classification_dict = OrderedDict()
        for classification in self.final_classifications.all().order_by('minimum_score').values():
            final_classification_dict[classification["final_classification"]] = classification["minimum_score"]
        return final_classification_dict

    def create_final_classification_tuple(self):
        """
        Creates the final classificationn information in to a tuple for the html dropdowns
        """
        final_classification_list = []
        for classification in self.final_classifications.all().order_by('minimum_score').values():
            c = (classification["id"], classification["final_classification"])
            final_classification_list.append(c)
        return tuple(final_classification_list)

    
class FinalClassification(models.Model):
    """
    Final classification options. Minimum score set as -9999 for benign options 
    """
    final_classification = models.CharField(max_length=200)
    minimum_score = models.IntegerField(null=True, blank=True)
    review_period = models.IntegerField()

    class Meta:
        unique_together = ["final_classification", "minimum_score"]

    def __str__(self):
        return self.final_classification


class CategorySortOrder(models.Model):
    """
    Through model to allow for categories of codes to be sorted for each guideline
    """
    guideline = models.ForeignKey("Guideline", on_delete=models.CASCADE)
    category = models.ForeignKey("ClassificationCriteriaCategory", on_delete=models.CASCADE)
    sort_order = models.IntegerField()

    class Meta:
        unique_together = ["guideline", "category"]

    def __str__(self):
        return f"{self.guideline} {self.category} {self.sort_order}"
    
    def get_all_codes_for_category(self):
        all_codes_for_guideline = self.guideline.criteria.all().values("criteria__code__code")


class ClassificationCriteria(models.Model):
    """
    All available combinations of codes and strengths
    """
    id = models.AutoField(primary_key=True)
    code = models.ForeignKey("ClassificationCriteriaCode", on_delete=models.CASCADE, related_name="classification_criteria")
    strength = models.ForeignKey("ClassificationCriteriaStrength", on_delete=models.CASCADE)

    class Meta:
        unique_together = ["code", "strength"]

    def __str__(self):
        return f"{self.code.code}_{self.strength.strength}"
    
    def classify_shorthand(self):
        paired_code = self.code.paired_criteria
        if paired_code is not None:
            paired_criteria = paired_code.code
            if self.code.pathogenic_or_benign == "O" or self.code.pathogenic_or_benign == "P":
                return f"{self.code}_{self.strength.shorthand}|{paired_criteria}_NA"
            elif self.code.pathogenic_or_benign == "B":
                return f"{paired_criteria}_NA|{self.code}_{self.strength.shorthand}"
        else:
            return f"{self.code}_{self.strength.shorthand}"
    
    def pretty_print(self):
        if self.strength.evidence_points > 0:
            evidence_points = f"+{self.strength.evidence_points}"
        else:
            evidence_points = self.strength.evidence_points
        return f"{self.code.code} {self.strength.pretty_print()} ({evidence_points})"


class ClassificationCriteriaCategory(models.Model):
    """
    Categories that the codes belong to - used to group codes for display
    """
    category = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.category}"
    
    def pretty_print(self):
        return self.category.title().replace("_", " ")


class ClassificationCriteriaCode(models.Model):
    """
    Codes that can be applied
    """
    code = models.CharField(max_length=10, unique=True)
    pathogenic_or_benign = models.CharField(max_length=1)
    description = models.TextField(null=True, blank=True)
    links = models.TextField(null=True, blank=True)
    annotations = models.CharField(max_length=50, null=True, blank=True)
    category = models.ForeignKey("ClassificationCriteriaCategory", on_delete=models.CASCADE)
    paired_criteria = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.code


class ClassificationCriteriaStrength(models.Model):
    """
    Strengths at which the criteria can be applied at
    """
    strength = models.CharField(max_length=20)
    shorthand = models.CharField(max_length=2)
    evidence_points = models.IntegerField()

    class Meta:
        unique_together = ["strength", "evidence_points"]

    def __str__(self):
        return f"{self.strength} {str(self.evidence_points)}"

    def pretty_print(self):
        return self.strength.title().replace("_", " ")


class TumourSubtype(models.Model):
    """
    """
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name

class ClassifyVariant(models.Model):
    """
    A given variant for a given transcript
    This is some duplication of information that's stored elsewhere but will make this app easier to work with
    We can populate based on existing models to continue data integrity
    """
    gene = models.CharField(max_length=200)
    hgvs_c = models.CharField(max_length=200, unique=True)
    hgvs_p = models.CharField(max_length=200, null=True, blank=True)
    genomic_coords = models.CharField(max_length=200)
    genome_build = models.IntegerField()

    def __str__(self):
        return self.hgvs_c

    def get_variant_info(self):
        """ get variant specific variables """
        variant_info = {
            "genomic": self.genomic_coords,
            "build": self.genome_build,
            "hgvs_c": self.hgvs_c,
            "hgvs_p": self.hgvs_p,
            "gene": self.gene,
            "gnomad": self.create_gnomad_link(),
        }
        return variant_info

    def create_gnomad_link(self):
        """ link to the Gnomad webpage """
        genome_build = self.genome_build

        # stored as chrom:posref>alt, needs to be chrom-pos-ref-alt
        var = self.genomic_coords
        var = var.replace(":", "-")
        var = var.replace(">", "-")
        var = re.split('(\d+)', var)
        var.insert(-1, "-")
        var = "".join(var)

        # format link specific to genome build
        if genome_build == 37:
            return f'https://gnomad.broadinstitute.org/variant/{var}?dataset=gnomad_r2_1'
        elif genome_build == 38:
            return f'https://gnomad.broadinstitute.org/variant/{var}?dataset=gnomad_r3'
        else:
            raise ValueError('Genome build should be either 37 or 38')


class ClassifyVariantInstance(PolymorphicModel):
    """
    Top level model for variant instance to account for all the SVD apps and manual variants added directly to classify
    """
    variant = models.ForeignKey("ClassifyVariant", on_delete=models.CASCADE)
    guideline = models.ForeignKey("Guideline", on_delete=models.CASCADE)
    tumour_subtype = models.ForeignKey("TumourSubtype", on_delete=models.CASCADE, null=True, blank=True)
    final_class = models.ForeignKey("FinalClassification", on_delete=models.CASCADE, null=True, blank=True)
    final_score = models.IntegerField(blank=True, null=True)
    final_class_overridden = models.BooleanField(default=False)
    complete_date = models.DateTimeField(blank=True, null=True)
    full_classification = models.BooleanField(default=False)
    reused_classification = models.ForeignKey('self', on_delete=models.PROTECT, null=True, blank=True, related_name="original_classification")

    class Meta:
        get_latest_by = ["complete_date"]

    def __str__(self):
        return f"{self.variant.gene} {self.variant.hgvs_c} (#{self.pk})"

    def is_complete(self):
        if self.complete_date is None:
            return False
        else:
            return True

    def get_all_checks(self):
        return Check.objects.filter(classification=self).order_by("pk")

    def get_previous_checks(self):
        return self.get_all_checks().order_by("-pk")[1:]

    def get_latest_check(self):
        return self.get_all_checks().order_by("-pk")[0]

    def get_status(self):
        if self.get_latest_check().check_complete:
            return "Complete"
        else:
            num_checks = self.get_all_checks().count()
            return f"Check {num_checks}"

    def get_classification_info(self):
        current_check_obj = self.get_latest_check()
        classification_info = {
            "classification_obj": self,
            "current_check": current_check_obj,
            "guidelines": self.guideline.guideline,
            "somatic_or_germline": self.guideline.somatic_or_germline,
            "all_checks": self.get_all_checks(),
            "reused": self.original_classification.reverse().exists(),
        }

        # only pull this info if user selected full classification, otherwise code objects wont exist and it'll error
        if self.full_classification and self.get_latest_check().previous_classifications_check:
            current_score, current_class = current_check_obj.update_classification()
            classification_info["codes_by_category"] = self.get_codes_by_category()
            classification_info["current_score"] = current_score
            classification_info["final_class_overridden"] = current_check_obj.final_class_overridden
            if current_check_obj.final_class_overridden:
                classification_info["current_class"] = current_check_obj.final_class
            else:
                classification_info["current_class"] = current_class
        return classification_info

    def get_dropdown_options(self, code_list):
        """get all dropdown options for a list of codes"""

        # we're only expecting up to 2 paired codes
        if len(code_list) > 2:
            raise ValueError("max number of combined codes is 2")

        # create pending and not applied options
        dropdown_options = [
            {"value": "|".join([f"{c}_PE" for c in code_list]), "text": "Pending"},
            {"value": "|".join([f"{c}_NA" for c in code_list]), "text": "Not applied"},
        ]

        for code in code_list:
            all_strengths = self.guideline.criteria.filter(code__code=code)
            for strength in all_strengths:
                value = strength.classify_shorthand()
                text = strength.pretty_print()
                dropdown_options.append(
                    {"value": value, "text": text}
                )

        return dropdown_options

    def get_dropdown_value(self, code_list):
        latest_code_objects = self.get_latest_check().get_code_answers()
        l = []
        for c in code_list:
            l.append(latest_code_objects.get(code__code=c).get_code())
        return "|".join(l)

    def get_codes_by_category(self):
        """ordered list of codes for displaying template"""
        # TODO simplify

        order_info = self.get_order_info()
        code_info = self.get_code_info()

        latest_code_objects = self.get_latest_check().get_code_answers()
        all_check_objects = self.get_all_checks()

        output_dict = {}
        for section, codes in order_info.items():
            output_dict[section] = {
                "slug": slugify(section),
                "codes": {},
                "applied_codes": [],
                "complete": True,
            }
            for code in codes:
                code_list = code.split("_")

                # loop through each code and extract info
                code_details = []
                annotations = []

                for c in code_list:
                    # get applied codes
                    code_object = latest_code_objects.get(code__code=c)

                    # add detailed code description to dict
                    code_details.append({c: code_info[c]})
                    annotations += code_info[c]["annotations"]

                    # get info on what codes have been applied
                    if code_object.applied:
                        output_dict[section]["applied_codes"].append(
                            f"{c}_{code_object.applied_strength.shorthand}"
                        )
                    if code_object.pending:
                        output_dict[section]["complete"] = False

                all_checks = []
                if len(code_list) == 1:
                    # all checks for dropdown
                    for c in all_check_objects:
                        check_code_objects = c.get_code_answers()
                        all_checks.append(
                            check_code_objects.get(code__code=code_list[0]).get_string()
                        )

                else:
                    code_1, code_2 = code_list
                    # all checks
                    for c in all_check_objects:
                        check_code_objects = c.get_code_answers()
                        code_1_display = check_code_objects.get(
                            code__code=code_1
                        ).get_string()
                        code_2_display = check_code_objects.get(
                            code__code=code_2
                        ).get_string()

                        if code_1_display == code_2_display:
                            all_checks.append(code_1_display)
                        else:
                            if code_1_display == "Not applied":
                                all_checks.append(code_2_display)

                            elif code_2_display == "Not applied":
                                all_checks.append(code_1_display)

                # remove duplicates (template doesnt like sets so convert back to list)
                annotations = list(set(annotations))
                # add all to final dict
                output_dict[section]["codes"][code] = {
                    "list": code_list,
                    "details": code_details,
                    "dropdown": self.get_dropdown_options(code_list),
                    "value": self.get_dropdown_value(code_list),
                    "annotations": annotations,
                    "all_checks": all_checks,
                }
        return output_dict

    def get_order_info(self):
        """Get the ordered list of codes dictionary for the ajax"""

        order_info = {}

        sort_order_query = self.guideline.sort_order.all().order_by("categorysortorder__sort_order")
        
        for sort_order in sort_order_query:
            pretty_print = sort_order.pretty_print()
            code_list = []
            codes = ClassificationCriteriaCode.objects.filter(
                Q(category=sort_order) &
                Q(classification_criteria__guideline=self.guideline)
            ).distinct()

            for code in codes:
                if code.paired_criteria is not None:
                    # some germline codes are multiple pathogenic options
                    if code.pathogenic_or_benign == "P" and code.paired_criteria.pathogenic_or_benign == "P":
                        codes_for_string = [code.code, code.paired_criteria.code]
                        codes_for_string.sort()
                        code_string = f"{codes_for_string[0]}_{codes_for_string[1]}"
                    elif code.pathogenic_or_benign == "O" or code.pathogenic_or_benign == "P":
                        code_string = f"{code.code}_{code.paired_criteria.code}"
                    elif code.pathogenic_or_benign == "B":
                        code_string = f"{code.paired_criteria.code}_{code.code}"
                else:
                    code_string = code.code
                code_list.append(code_string)

            code_list = list(set(code_list))
            code_list.sort()
            order_info[pretty_print] = code_list

        return order_info
    
    def get_code_info(self):
        """Get the code information dictionary for the ajax"""

        type_dict = {
            "O": "oncogenic",
            "P": "pathogenic",
            "B": "benign"
        }

        codes_dict = {}
        codes = self.guideline.criteria.all()
        for code in codes:

            code_name = code.code.code
            type = type_dict[code.code.pathogenic_or_benign]
            category = code.code.category.category
            options = code.strength.shorthand
            description = code.code.description
            annotations = [code.code.annotations]

            try:
                codes_dict[code_name]["options"].append(options)
            except KeyError:
                codes_dict[code_name] = {
                    "type": type,
                    "category": category,
                    "options": [options],
                    "description": description,
                    "annotations": annotations
                }
            
        return codes_dict

    def get_all_previous_classifications(self):
        return ClassifyVariantInstance.objects.filter(variant=self.variant, guideline=self.guideline).order_by("-pk")

    def get_most_recent_full_classification(self):
        try:
            # get the most recent classification where the complete_date is not empty and tumour type matches
            most_recent = self.get_all_previous_classifications().filter(
                full_classification=True,
                tumour_subtype=self.tumour_subtype,
            ).latest()

            # return none if the only response is the current object
            if most_recent == self:
                return None, False

            # check if a review is needed (every 6 months for VUS, 2 years otherwise)
            if most_recent.final_class:
                review_period = most_recent.final_class.review_period
                review_period_diff = datetime.timedelta(days=review_period*365/12)
            else:
                return None, False

            # TODO maybe a warning if multiple pending classifications for same variant?

            # work out if date is longer than review period
            time_diff = timezone.now() - most_recent.complete_date
            needs_review = time_diff > review_period_diff

            return most_recent, needs_review

        # return none if no previous completed classifications (pending ones wont be included)
        except ClassifyVariantInstance.DoesNotExist:
            return None, False

    def get_previous_classification_choices(self):
        """
        get options for the previous classifiation tab dropdown,
        will only let you use previous if there is one
        """
        previous_classification, needs_review = self.get_most_recent_full_classification()
        if self.get_all_checks().count() > 1:
            if self.full_classification:
                return (("new", "Perform full classification"),)
            else:
                return (("previous", "Use previous classification"),)

        if previous_classification and needs_review == False:
            return (
                ("previous", "Use previous classification"),
                ("new", "Perform full classification"),
            )
        else:
            return (("new", "Perform full classification"),)

    def make_new_check(self):
        new_check = Check.objects.create(classification=self)

    def reopen_analysis(self, user):
        previous_check = self.get_latest_check()
        if user != previous_check.user:
            return False, f"Only {previous_check.user} can reopen this case"
        else:
            self.final_class = None
            self.final_score = None
            self.final_class_overridden = False
            self.complete_date = None
            previous_check.reopen_check()
            self.save()
            return True, None

    @transaction.atomic
    def signoff_check(self, current_check, next_step):
        """complete a whole check"""
        # extra check - close of current check and make a new one
        if next_step == "extra_check":
            updated, err = current_check.complete_check()
            if not updated:
                return False, err
            else:
                self.make_new_check()
                return True, None

        # send back - delete current check if its not the first check
        if next_step == "send_back":
            previous_checks = self.get_previous_checks()
            if previous_checks.exists():
                previous_checks[0].reopen_check()
                current_check.delete()
                return True, None
            else:
                return False, "Cannot send back, this is the first check"

        # complete - close check and analysis if checks pass
        if next_step == "complete":
            # check current check is passable 
            current_check_complete, err = current_check.pre_completion_validation()
            if not current_check_complete:
                return False, err

            # whole analysis checks
            all_checks = self.get_all_checks()
            last_two = all_checks.order_by("-pk")[0:2]
            last_two_checkers = set([c.user.username for c in last_two])
            last_two_results = set([c.final_class.final_classification for c in last_two])
            last_two_scores = set([c.final_score for c in last_two])

            # two diagnostic checks
            if all_checks.count() < 2:
                return False, "Cannot complete analysis, two checks required"
            # two diagnostic checks after training cases
            elif all_checks.filter(diagnostic=True).count() < 2:
                return False, "Cannot complete analysis, some of the checks are training checks"
            # last two checkers were same person # TODO remove comments when testing done
            #elif len(last_two_checkers) == 1:
            #    return False, "Cannot complete analysis, last two checkers are the same analyst"
            # two classifciations agree
            elif len(last_two_results) > 1:
                return False, "Cannot complete analysis, overall classification from last two checkers dont agree"
            # two scores agree
            elif len(last_two_scores) > 1:
                return False, "Cannot complete analysis, scores from last two checkers dont agree"
            # save results to classification obj if all checks pass
            else:
                current_check.complete_check()
                self.final_class = current_check.final_class
                self.final_score = current_check.final_score
                self.final_class_overridden = current_check.final_class_overridden
                self.complete_date = timezone.now()
                self.save()
                return True, None


class AnalysisVariantInstance(ClassifyVariantInstance):
    """
    Links out to the analysis app (TSO500, ctDNA, CRM, BRCA)
    """
    variant_instance = models.ForeignKey(VariantPanelAnalysis, on_delete=models.CASCADE)

    def get_sample_info(self):
        sample_info = {
            "sample_id": self.variant_instance.sample_analysis.sample.sample_id,
            "worksheet_id": self.variant_instance.sample_analysis.worksheet.ws_id,
            "svd_panel": self.variant_instance.sample_analysis.panel,
            "specific_tumour_type": "TODO",
        }
        return sample_info


class SWGSGermlineVariantInstance(ClassifyVariantInstance):
    """
    Germline variants from the SWGS app
    """
    variant_instance = models.ForeignKey(GermlineVariantInstance, on_delete=models.CASCADE)

    def get_sample_info(self):
        # TODO - these will need coding relative to SWGS app
        sample_info = {
            "sample_id": "TODO",
            "worksheet_id": "TODO",
            "svd_panel": "TODO",
            "specific_tumour_type": "TODO",
        }
        return sample_info


class SWGSSomaticVaraintInstance(ClassifyVariantInstance):
    """
    Somatic variants from the SWGS app
    """
    variant_instance = models.ForeignKey(SomaticVariantInstance, on_delete=models.CASCADE)

    def get_sample_info(self):
        # TODO - these will need coding relative to SWGS app
        sample_info = {
            "sample_id": "TODO",
            "worksheet_id": "TODO",
            "svd_panel": "TODO",
            "specific_tumour_type": "TODO",
        }
        return sample_info


class ManualVariantInstance(ClassifyVariantInstance):
    """
    Variants added manually directly to classify
    """
    pass


class Check(models.Model):
    """
    A check of a classification
    """
    classification = models.ForeignKey("ClassifyVariantInstance", on_delete=models.CASCADE)
    info_check = models.BooleanField(default=False)
    previous_classifications_check = models.BooleanField(default=False)
    classification_check = models.BooleanField(default=False)
    check_complete = models.BooleanField(default=False)
    diagnostic = models.BooleanField(null=True)
    signoff_time = models.DateTimeField(blank=True, null=True)
    user = models.ForeignKey("auth.User", on_delete=models.PROTECT, blank=True, null=True, related_name="classification_checker")
    final_class = models.ForeignKey("FinalClassification", on_delete=models.CASCADE, null=True, blank=True)
    final_score = models.IntegerField(blank=True, null=True)
    final_class_overridden = models.BooleanField(default=False)

    def get_code_answers(self):
        """get all classification codes for the current check"""
        return CodeAnswer.objects.filter(check_object=self)

    def update_classification(self):
        """calculate the current score and classification"""
        score_counter = 0
        codes = self.get_code_answers()
        for c in codes:
            if c.applied:
                score_counter += c.applied_strength.evidence_points

        # work out class from score counter
        class_dict = self.classification.guideline.create_final_classification_ordered_dict()
        # loop through in order until the score no longer meets the threshold
        classification = "Benign"
        for c, score in class_dict.items():
            if score_counter >= score:
                classification = c

        return score_counter, classification

    @transaction.atomic
    def update_codes(self, selections):
        """update each code answer and then work out overall score/ class"""

        # load all code answer objects & loop through each selection
        code_objects = self.get_code_answers()
        for s in selections:

            # get specific code & type
            c, value = s.split("_")
            code_obj = code_objects.get(code__code=c)

            # if check pending, set pending to true
            if value == "PE":
                pending = True
                applied = False
                strength = None

            # if code not applied, set pending & applied to false
            elif value == "NA":
                pending = False
                applied = False
                strength = None

            # if code applied, save to models
            else:
                pending = False
                applied = True
                criteria_strength_obj = ClassificationCriteria.objects.get(code=code_obj.code, strength__shorthand=value)
                strength = criteria_strength_obj.strength

            # save values to database
            code_obj.pending = pending
            code_obj.applied = applied
            code_obj.applied_strength = strength
            code_obj.save()

        return True

    @transaction.atomic
    def complete_info_tab(self):
        self.info_check = True
        self.save()

    @transaction.atomic
    def complete_previous_class_tab(self, reuse_classification_obj):
        """ complete step in check obj and load up codes linked to check """
        self.previous_classifications_check = True
        if reuse_classification_obj:
            self.classification_check = True
            self.classification.reused_classification = reuse_classification_obj
            self.final_class = reuse_classification_obj.final_class #.final_classification
            self.final_score = reuse_classification_obj.final_score
            self.classification.save()
        else:
            #self.full_classification = True
            self.classification.full_classification = True
            self.classification.save()
            self.create_code_answers()
        self.save()

    @transaction.atomic
    def complete_classification_tab(self, override):
        """complete classification tab and same final class into to check model"""
        final_score, final_class = self.update_classification()
        final_class_obj = self.classification.guideline.final_classifications.filter(final_classification=final_class)[0]
        # if final classification isnt overridden
        if override != "No":
            self.final_class_overridden = True
            override_final_class_obj = self.classification.guideline.final_classifications.filter(pk=override)[0]
            self.final_class = override_final_class_obj
        else:
            self.final_class = final_class_obj
        self.classification_check = True
        self.final_score = final_score
        self.save()

    def pre_completion_validation(self):
        if self.info_check == False:
            return False, "Please complete the Variant details tab"
        elif self.previous_classifications_check == False:
            return False, "Please complete the Previous classifications tab"
        elif self.classification_check == False:
            return False, "Please complete the Classification tab"
        else:
            return True, None

    @transaction.atomic
    def complete_check(self):
        passed_checks, err = self.pre_completion_validation()
        if not passed_checks:
            return False, err
        else:
            self.check_complete = True
            self.signoff_time = timezone.now()
            self.save()
            return True, None

    @transaction.atomic
    def reopen_info_tab(self):
        """reset variant tab, also resets other two tabs"""
        self.info_check = False
        self.reopen_previous_class_tab()

    @transaction.atomic
    def reopen_previous_class_tab(self):
        """reset previous classifications and classify tabs"""
        self.previous_classifications_check = False
        self.classification.reused_classification = None
        self.classification.full_classification = False
        self.classification.save()
        self.final_class_overridden = False # reset to False if needed
        self.reopen_classification_tab()
        self.delete_code_answers()

    @transaction.atomic
    def reopen_classification_tab(self):
        """reset the classifications tab"""
        self.classification_check = False
        self.final_score = None
        self.final_class = None
        self.final_class_overridden = False # reset to False if needed
        self.save()

    @transaction.atomic
    def reopen_check(self):
        """reopen a completed check"""
        self.check_complete = False
        self.diagnostic = None
        self.signoff_time = None
        self.save()

    @transaction.atomic
    def create_code_answers(self):
        """make a set of code answers against the current check"""
        all_codes_query = self.classification.guideline.criteria.all()
        all_codes = [code.code.code for code in all_codes_query]
        all_codes = list(set(all_codes))

        for code in all_codes:
            code_obj = ClassificationCriteriaCode.objects.get(code=code)
            CodeAnswer.objects.create(code=code_obj, check_object=self)

    @transaction.atomic
    def delete_code_answers(self):
        """remove the set of code answers for the current check"""
        codes = self.get_code_answers()
        for c in codes:
            c.delete()


class CodeAnswer(models.Model):
    """
    A check of an individual code

    """
    code = models.ForeignKey("ClassificationCriteriaCode", on_delete=models.CASCADE)
    check_object = models.ForeignKey("Check", on_delete=models.CASCADE)
    pending = models.BooleanField(default=True)
    applied = models.BooleanField(default=False)
    applied_strength = models.ForeignKey("ClassificationCriteriaStrength", on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.get_code()}"

    def get_code(self):
        if self.pending:
            return f"{self.code.code}_PE"
        elif self.applied:
            return f"{self.code.code}_{self.applied_strength.shorthand}"
        else:
            return f"{self.code.code}_NA"

    def get_code_type(self):
        if self.code.pathogenic_or_benign == "B":
            return "Benign"
        elif self.code.pathogenic_or_benign == "O":
            return "Oncogenic"
        elif self.code.pathogenic_or_benign == "P":
            return "Pathogenic"

    def pretty_print_code(self):
        return self.code.code

    def get_score(self):
        if self.code.pathogenic_or_benign == "B":
            return f"{self.applied_strength.evidence_points}"
        elif self.code.pathogenic_or_benign == "O" or "P":
            return f"+{self.applied_strength.evidence_points}"

    def get_string(self):
        if self.pending:
            return "Pending"
        elif self.applied:
            return f"{self.code} {self.applied_strength.pretty_print()} ({self.get_score()})"
        else:
            return "Not applied"
