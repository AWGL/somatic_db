from django.test import TestCase
from .models import *
from analysis.models import SampleAnalysis, Sample

# Create your tests here.
class TestViews(TestCase):
    pass

class TestModels(TestCase):
    """
    Base class to test the check model functionality - set up some example analyses
    """

    fixtures = ["setup_fixtures.json", "user_groups.json"]

    def setUp(self):
        #TODO work on this needs a more comprehensive test database

        # setup test variants
        self.sample_analysis_inst = SampleAnalysis.objects.create(id=60)
        self.analysis_inst = VariantPanelAnalysis.objects.create(id=60)
        self.var, _ = ClassifyVariant.objects.get_or_create(
            gene = "TET2",
            hgvs_c = "NM_001127208.3:c.4139A>G",
            hgvs_p = "NP_001120680.1:p.His1380Arg",
            genomic_coords = "4:105269704A>G",
            genome_build = 38,
        )
        self.guideline_obj = Guideline.objects.get(pk=2)
        self.new_var_obj = AnalysisVariantInstance.objects.create(
            variant=self.var,
            variant_instance=self.var_inst,
            guideline=self.guideline_obj
        )
        self.check_one = Check.objects.create(
            classification = self.new_var_obj,
            diagnostic = True
        )

        # benign code
        self.b1_code_obj = ClassificationCriteriaCode.objects.get(pk=28)
        # pathogenic code
        self.pp3_code_obj = ClassificationCriteriaCode.objects.get(pk=14)
        # oncogenic code
        self.o4_code_obj = ClassificationCriteriaCode.objects.get(pk=31)
        # oncogenic code
        self.o9_code_obj = ClassificationCriteriaCode.objects.get(pk=39)

        # pathogenic/oncogenic strength object
        self.path_strength_obj = ClassificationCriteriaStrength.objects.get(pk=3)
        # benign strength object
        self.benign_strength_obj = ClassificationCriteriaStrength.objects.get(pk=6)
        # pathogenic/oncogenic strength object
        self.path_strength_obj_2 = ClassificationCriteriaStrength.objects.get(pk=1)

        # Code Answers
        self.pending_benign_code_answer_obj = CodeAnswer.objects.create(
            code = self.b1_code_obj,
            check_object = self.check_one
        )

        self.not_applied_pathogenic_code_answer_obj = CodeAnswer.objects.create(
            code = self.pp3_code_obj,
            check_object = self.check_one,
            pending = False
        )

        self.applied_oncogenic_code_answer_obj = CodeAnswer.objects.create(
            code = self.o4_code_obj,
            check_object = self.check_one,
            pending = False,
            applied = True,
            applied_strength = self.path_strength_obj
        )

        self.applied_oncogenic_code_answer_obj_2 = CodeAnswer.objects.create(
            code = self.o9_code_obj,
            check_object = self.check_one,
            pending = False,
            applied = True,
            applied_strength = self.path_strength_obj_2
        )

    def test_code_answer(self):
        """
        Test the CodeAnswer model
        """

        # test for pending benign code
        self.assertEqual(self.pending_benign_code_answer_obj.get_code(), "B1_PE")
        self.assertEqual(self.pending_benign_code_answer_obj.get_code_type(), "Benign")
        self.assertEqual(self.pending_benign_code_answer_obj.pretty_print_code(), "B1")
        self.assertEqual(self.pending_benign_code_answer_obj.get_score(), "Not Applied")
        self.assertEqual(self.pending_benign_code_answer_obj.get_string(), "Pending")
        
        # check benign string when scored
        self.pending_benign_code_answer_obj.applied_strength = self.benign_strength_obj
        self.assertEqual(self.pending_benign_code_answer_obj.get_score(), "-2")

        # test for not applied pathogenic code
        self.assertEqual(self.not_applied_pathogenic_code_answer_obj.get_code(), "PP3_NA")
        self.assertEqual(self.not_applied_pathogenic_code_answer_obj.get_code_type(), "Pathogenic")
        self.assertEqual(self.not_applied_pathogenic_code_answer_obj.get_score(), "Not Applied")
        self.assertEqual(self.not_applied_pathogenic_code_answer_obj.get_string(), "Not applied")

        # test for applied oncogenic code
        self.assertEqual(self.applied_oncogenic_code_answer_obj.get_code(), "O4_MO")
        self.assertEqual(self.applied_oncogenic_code_answer_obj.get_code_type(), "Oncogenic")
        self.assertEqual(self.applied_oncogenic_code_answer_obj.get_score(), "+2")
        self.assertEqual(self.applied_oncogenic_code_answer_obj.get_string(), "O4 Moderate (+2)")

    def test_check(self):
        """
        unit tests for the Check model
        """
        
        # get code answers doesn't need testing - standard django query

        # update_classification - expecting oncogenic
        score_counter, classification = self.check_one.update_classification()
        self.assertEqual(score_counter, 10)
        self.assertEqual(classification, "Oncogenic")

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
        # check variant info dict
        expected_variant_info = {
            "genomic": "4:105269704A>G",
            "build": 38,
            "hgvs_c": "NM_001127208.3:c.4139A>G",
            "hgvs_p": "NP_001120680.1:p.His1380Arg",
            "gene": "TET2",
            "gnomad": "https://gnomad.broadinstitute.org/variant/4-105269704-A-G?dataset=gnomad_r3"
        }
        self.assertEqual(self.var.get_variant_info(), expected_variant_info)

        # check gnomAD link
        self.assertEqual(self.var.create_gnomad_link(), "https://gnomad.broadinstitute.org/variant/4-105269704-A-G?dataset=gnomad_r3")
        
        # check gnomAD link 37
        self.var.genome_build = 37
        self.assertEqual(self.var.create_gnomad_link(), "https://gnomad.broadinstitute.org/variant/4-105269704-A-G?dataset=gnomad_r2_1")
        
        # check gnomAD link incorrect build
        self.var.genome_build = 19
        with self.assertRaises(ValueError):
            self.var.create_gnomad_link()

    def test_classification_criteria_strength(self):
        """
        unit tests for ClassificationCriteriaStrength model
        """
        # Very strong object
        classification_criteria_strength_obj = ClassificationCriteriaStrength.objects.get(pk=1)
        self.assertEqual(classification_criteria_strength_obj.pretty_print(), "Very Strong")

    def test_classification_criteria_category(self):
        """
        unit tests for ClassificationCriteriaCategory model
        """
        classification_criteria_category_obj = ClassificationCriteriaCategory(
            category = "A_mixed_CASE_stRing"
        )
        self.assertEqual(classification_criteria_category_obj.pretty_print(), "A Mixed Case String")

    def test_classification_criteria(self):
        """
        unit tests for ClassificationCriteria model
        """
        # paired benign code
        paired_benign_obj = ClassificationCriteria.objects.get(pk=90)
        self.assertEqual(paired_benign_obj.classify_shorthand(), "O10_NA|B7_MO")
        self.assertEqual(paired_benign_obj.pretty_print(), "B7 Moderate (-2)")

        # unpaired oncogenic object
        unpaired_oncogenic_obj = ClassificationCriteria.objects.get(pk=73)
        self.assertEqual(unpaired_oncogenic_obj.classify_shorthand(), "O7_MO")
        self.assertEqual(unpaired_oncogenic_obj.pretty_print(), "O7 Moderate (+2)")

        # paired pathogenic object
        paired_pathogenic_obj = ClassificationCriteria.objects.get(pk=29)
        self.assertEqual(paired_pathogenic_obj.classify_shorthand(), "PM6_ST|PS2_NA")
        self.assertEqual(paired_pathogenic_obj.pretty_print(), "PM6 Strong (+4)")


    def test_guideline(self):
        """
        unit tests for Guideline model
        """
        pass
        #TODO unit tests for guideline model
