from django.test import TestCase
from .models import *

# Create your tests here.
class TestViews(TestCase):
    pass

class TestModels(TestCase):
    """
    Base class to test the check model functionality - set up some example analyses
    """

    fixtures = ["setup_fixtures.json", "user_groups.json"]

    def setUp(self):
        # setup test variants
        self.var_inst = VariantPanelAnalysis(id=60)  
        self.var, _ = ClassifyVariant.objects.get_or_create(
            gene = "TET2",
            hgvs_c = "NM_001127208.3:c.4139A>G",
            hgvs_p = "NP_001120680.1:p.His1380Arg",
            genomic_coords = "4:105269704A>G",
            genome_build = 38,
        )
        self.guideline_obj = Guideline.objects.get(pk=2)
        self.new_var_obj = AnalysisVariantInstance(
            variant=self.var,
            variant_instance=self.var_inst,
            guideline=self.guideline_obj
        )
        self.check_one = Check(
            classification = self.new_var_obj,
            diagnostic = True
        )

    def test_code_answer(self):
        """
        Test the CodeAnswer model
        """
        # benign code
        b1_code_obj = ClassificationCriteriaCode.objects.get(pk=28)
        # pathogenic code
        pp3_code_obj = ClassificationCriteriaCode.objects.get(pk=14)
        # oncogenic code
        o4_code_obj = ClassificationCriteriaCode.objects.get(pk=31)

        # pathogenic/oncogenic strength object
        path_strength_obj = ClassificationCriteriaStrength.objects.get(pk=3)
        # benign strength object
        benign_strength_obj = ClassificationCriteriaStrength.objects.get(pk=6)

        # test for pending benign code
        pending_benign_code_answer_obj = CodeAnswer(
            code = b1_code_obj,
            check_object = self.check_one
        )
        self.assertEqual(pending_benign_code_answer_obj.get_code(), "B1_PE")
        self.assertEqual(pending_benign_code_answer_obj.get_code_type(), "Benign")
        self.assertEqual(pending_benign_code_answer_obj.pretty_print_code(), "B1")
        self.assertEqual(pending_benign_code_answer_obj.get_score(), "Not Applied")
        self.assertEqual(pending_benign_code_answer_obj.get_string(), "Pending")
        # check benign string when scored
        pending_benign_code_answer_obj.applied_strength = benign_strength_obj
        self.assertEqual(pending_benign_code_answer_obj.get_score(), "-2")

        # test for not applied pathogenic code
        not_applied_pathogenic_code_answer_obj = CodeAnswer(
            code = pp3_code_obj,
            check_object = self.check_one,
            pending = False
        )
        self.assertEqual(not_applied_pathogenic_code_answer_obj.get_code(), "PP3_NA")
        self.assertEqual(not_applied_pathogenic_code_answer_obj.get_code_type(), "Pathogenic")
        self.assertEqual(not_applied_pathogenic_code_answer_obj.get_score(), "Not Applied")
        self.assertEqual(not_applied_pathogenic_code_answer_obj.get_string(), "Not applied")

        # test for applied oncogenic code
        applied_oncogenic_code_answer_obj = CodeAnswer(
            code = o4_code_obj,
            check_object = self.check_one,
            pending = False,
            applied = True,
            applied_strength = path_strength_obj
        )
        self.assertEqual(applied_oncogenic_code_answer_obj.get_code(), "O4_MO")
        self.assertEqual(applied_oncogenic_code_answer_obj.get_code_type(), "Oncogenic")
        self.assertEqual(applied_oncogenic_code_answer_obj.get_score(), "+2")
        self.assertEqual(applied_oncogenic_code_answer_obj.get_string(), "O4 Moderate (+2)")

    def test_check(self):
        """
        unit tests for the Check model
        """
        pass
        #TODO unit tests for Check model

    def test_classify_variant_instance(self):
        """
        unit tests for ClassifyVariantInstance model and children
        AnalysisVariantInstance, SWGSGermlineVariantInstance, SWGSSomaticVariantInstance, ManualVariantInstance
        """
        pass
        #TODO unit tests for ClassifyVariantInstance model
        #TODO unit tests for AnalysisVariantInstance model
        #TODO unit tests for SWGSGermlineVariantInstance model
        #TODO unit tests for SWGSSomaticVariantInstance model
        #TODO unit tests for ManualVariantInstance model

    def test_classify_variant(self):
        """
        unit tests for ClassifyVariant model
        """
        pass
        #TODO unit tests for ClassifyVariant model

    def test_tumour_subtype(self):
        """
        unit tests for TumourSubtype model
        """
        pass
        #TODO unit tests for TumourSubtype model

    def test_classification_criteria_strength(self):
        """
        unit tests for ClassificationCriteriaStrength model
        """
        pass
        #TODO unit tests for ClassificationCriteriaStrength model

    def test_classification_criteria_category(self):
        """
        unit tests for ClassificationCriteriaCategory model
        """
        pass
        #TODO unit tests for ClassificationCriteriaCategory model

    def test_classification_criteria(self):
        """
        unit tests for ClassificationCriteria model
        """
        pass
        #TODO unit tests for ClassificationCriteria model

    def test_category_sort_order(self):
        """
        unit tests for CategorySortOrder model
        """
        pass
        #TODO unit tests for CategorySortOrder model

    def test_final_classification(self):
        """
        unit tests for FinalClassification model
        """
        pass
        #TODO unit tests for FinalClassification model

    def test_guideline(self):
        """
        unit tests for Guideline model
        """
        pass
        #TODO unit tests for guideline model
