from django.test import TestCase
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User
from .models import *
from analysis.models import SampleAnalysis, Panel, VariantInstance
from .test_data import expected_results
from unittest import mock

# Create your tests here.
class TestViews(TestCase):
    #TODO views unit tests
    pass

class TestModels(TestCase):
    """
    Base class to test the check model functionality - set up some example analyses
    """

    # include fixtures from classify and analysis to builld base models
    fixtures = ["setup_fixtures.json", "user_groups.json", 
                "analysis/fixtures/dna_test_1.json"]
    
    maxDiff = None

    def setUp(self):
        self.user_one = User.objects.create_user(
            username = "userone",
            email = "userone@user.com"
        )
        self.user_two = User.objects.create_user(
            username = "usertwo",
            email = "usertwo@user.com"
        )
        # setup test variants
        panel_obj = Panel.objects.get(panel_name="Tumour", assay='1', genome_build=37, live=True)
        sample_obj = SampleAnalysis.objects.get(sample_id='dna_test_1', panel=panel_obj)
        variant_obj = VariantInstance.objects.get(pk=1)
        self.var, _ = ClassifyVariant.objects.get_or_create(
            gene = "TET2",
            hgvs_c = "NM_001127208.3:c.4139A>G",
            hgvs_p = "NP_001120680.1:p.His1380Arg",
            genomic_coords = "4:105269704A>G",
            genome_build = 38,
        )
        self.analysis_inst = VariantPanelAnalysis.objects.create(
            id=60, sample_analysis=sample_obj, variant_instance=variant_obj)
        self.guideline_obj = Guideline.objects.get(pk=2)
        self.new_var_obj = AnalysisVariantInstance.objects.create(
            variant=self.var,
            variant_instance=self.analysis_inst,
            guideline=self.guideline_obj
        )
        self.check_one = Check.objects.create(
            classification = self.new_var_obj,
            diagnostic = True,
            user = self.user_one
        )
        self.check_two = Check.objects.create(
            classification = self.new_var_obj,
            user = self.user_two
        )

        self.classification_one_obj = FinalClassification.objects.get(pk=1)
        self.classification_two_obj = FinalClassification.objects.get(pk=2)

        # benign code
        self.b1_code_obj = ClassificationCriteriaCode.objects.get(pk=28)
        # pathogenic code
        self.pp3_code_obj = ClassificationCriteriaCode.objects.get(pk=14)
        # oncogenic code
        self.o4_code_obj = ClassificationCriteriaCode.objects.get(pk=31)
        # oncogenic code
        self.o9_code_obj = ClassificationCriteriaCode.objects.get(pk=39)
        # oncogenic code
        self.o2_code_obj = ClassificationCriteriaCode.objects.get(pk=29)
        # oncogenic code
        self.o3_code_obj = ClassificationCriteriaCode.objects.get(pk=27)

        # pathogenic/oncogenic strength object
        self.path_strength_obj = ClassificationCriteriaStrength.objects.get(pk=3)
        # benign strength object
        self.benign_strength_obj = ClassificationCriteriaStrength.objects.get(pk=6)
        # pathogenic/oncogenic strength object
        self.path_strength_obj_2 = ClassificationCriteriaStrength.objects.get(pk=1)

        # code answers
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

        self.pending_oncogenic_code_answer_obj_1 = CodeAnswer.objects.create(
            code = self.o2_code_obj,
            check_object = self.check_one
        )

        self.pending_oncogenic_code_answer_obj_2 = CodeAnswer.objects.create(
            code = self.o3_code_obj,
            check_object = self.check_one
        )

        # reuse classification object
        tumour_subtype_obj = TumourSubtype.objects.create(name="Lung")
        final_classification_obj, _ = FinalClassification.objects.get_or_create(
            final_classification = "Oncogenic",
            minimum_score = 10,
            review_period = 24
        )
        self.reuse_classification_obj = AnalysisVariantInstance.objects.create(
            variant = self.var,
            guideline = self.guideline_obj,
            tumour_subtype = tumour_subtype_obj,
            final_class = final_classification_obj,
            final_score = 12,
            variant_instance=self.analysis_inst
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

    def test_check_update_classification(self):
        """
        unit tests for the Check model
        """
        
        # get code answers doesn't need testing - standard django query

        # test update_classification - expecting oncogenic
        score_counter, classification = self.check_one.update_classification()
        self.assertEqual(score_counter, 10)
        self.assertEqual(classification, "Oncogenic")

    def test_check_update_codes(self):
        """
        unit tests for the Check model
        """

        # this function takes a list of criteria in the form CRITERIA_STRENGTH where the strength
        # is the shorthand
        # starting point: O4 and O9 applied. Change O9, apply O2 and have O3 as pending
        selections = ["O4_MO", "O9_NA", "O2_MO", "O3_PE"]
        self.assertTrue(self.check_one.update_codes(selections))
        
        # no change expected for O4
        o4_code_obj = CodeAnswer.objects.get(pk=3)
        self.assertEqual(o4_code_obj.code.code, "O4")
        self.assertFalse(o4_code_obj.pending)
        self.assertTrue(o4_code_obj.applied)
        self.assertEqual(o4_code_obj.applied_strength.evidence_points, 2)

        # O9 set to not applied
        o9_code_obj = CodeAnswer.objects.get(pk=4)
        self.assertEqual(o9_code_obj.code.code, "O9")
        self.assertFalse(o9_code_obj.pending)
        self.assertFalse(o9_code_obj.applied)
        self.assertIsNone(o9_code_obj.applied_strength)

        # O2 applied at moderate
        o2_code_obj = CodeAnswer.objects.get(pk=5)
        self.assertEqual(o2_code_obj.code.code, "O2")
        self.assertFalse(o2_code_obj.pending)
        self.assertTrue(o2_code_obj.applied)
        self.assertEqual(o2_code_obj.applied_strength.evidence_points, 2)

        # O3 is pending
        o3_code_obj = CodeAnswer.objects.get(pk=6)
        self.assertEqual(o3_code_obj.code.code, "O3")
        self.assertTrue(o3_code_obj.pending)
        self.assertFalse(o3_code_obj.applied)
        self.assertIsNone(o3_code_obj.applied_strength)

    def test_check_update_codes(self):
        """
        unit tests for the Check model
        """
        # test complete_info_tab
        self.assertFalse(self.check_one.info_check)
        self.check_one.complete_info_tab()
        self.assertTrue(self.check_one.info_check)

    def test_check_complete_previous_class_tab_reuse_classification(self):
        """
        unit tests for the Check model
        """
        self.check_one.complete_previous_class_tab(self.reuse_classification_obj)
        self.assertTrue(self.check_one.previous_classifications_check)
        self.assertTrue(self.check_one.classification_check)
        self.assertEqual(self.check_one.classification.reused_classification, self.reuse_classification_obj)
        self.assertEqual(self.check_one.final_class.final_classification, "Oncogenic")
        self.assertEqual(self.check_one.final_score, 12)

    def test_check_complete_previous_class_tab_new_classification(self):
        """
        unit tests for the Check model
        """
        self.check_one.complete_previous_class_tab(None)
        self.assertTrue(self.check_one.classification.full_classification)

    def test_check_complete_classification_tab_override(self):
        """
        unit tests for the Check model
        """
        self.check_one.complete_classification_tab(override=1)
        self.assertTrue(self.check_one.final_class_overridden)
        self.assertEqual(self.check_one.final_class.final_classification, "Benign")
        self.assertTrue(self.check_one.classification_check)
        self.assertEqual(self.check_one.final_score, 10)

    def test_check_complete_classification_tab_no_override(self):
        """
        unit tests for the Check model
        """
        self.check_one.complete_classification_tab(override="No")
        self.assertFalse(self.check_one.final_class_overridden)
        self.assertEqual(self.check_one.final_class.final_classification, "Oncogenic")
        self.assertTrue(self.check_one.classification_check)
        self.assertEqual(self.check_one.final_score, 10)

    def test_check_pre_completion_validation(self):
        """
        unit tests for the Check model
        """
        
        # initially everything is false - info check not completed
        check, message = self.check_one.pre_completion_validation()
        self.assertFalse(check)
        self.assertEqual(message, "Please complete the Variant details tab")

        # previous classifications tab not completed
        self.check_one.info_check = True
        check, message = self.check_one.pre_completion_validation()
        self.assertFalse(check)
        self.assertEqual(message, "Please complete the Previous classifications tab")

        # classifications tab not completed
        self.check_one.previous_classifications_check = True
        check, message = self.check_one.pre_completion_validation()
        self.assertFalse(check)
        self.assertEqual(message, "Please complete the Classification tab")

        # everything is checked
        self.check_one.classification_check = True
        check, message = self.check_one.pre_completion_validation()
        self.assertTrue(check)
        self.assertIsNone(message)

    def test_check_complete_check_passed_check(self):
        """
        unit tests for the Check model
        """
        # ensure validation passes
        self.check_one.info_check = True
        self.check_one.previous_classifications_check = True
        self.check_one.classification_check = True

        check, message = self.check_one.complete_check()
        self.assertTrue(self.check_one.check_complete)
        self.assertIsInstance(self.check_one.signoff_time, datetime.datetime)
        self.assertTrue(check)
        self.assertIsNone(message)

    def test_check_complete_check_failed_check(self):
        """
        unit tests for the Check model
        """
        check, message = self.check_one.complete_check()
        self.assertFalse(self.check_one.check_complete)
        self.assertIsNone(self.check_one.signoff_time, datetime.datetime)
        self.assertFalse(check)
        self.assertEqual(message, "Please complete the Variant details tab")

    def test_check_reopen_info_tab(self):
        """
        unit tests for the Check model
        """
        self.check_one.info_check = True
        self.check_one.reopen_info_tab()
        self.assertFalse(self.check_one.info_check)

    def test_check_reopen_previous_class_tab(self):
        """
        unit tests for the Check model
        """
        self.check_one.info_check = True
        self.check_one.previous_classifications_check = True
        self.check_one.reopen_previous_class_tab()
        self.assertFalse(self.check_one.previous_classifications_check)
        self.assertIsNone(self.check_one.classification.reused_classification)
        self.assertFalse(self.check_one.classification.full_classification)
        self.assertFalse(self.check_one.final_class_overridden)
        all_code_answers = self.check_one.get_code_answers()
        code_answer_count = 0
        for code in all_code_answers:
            code_answer_count += 1
        self.assertEqual(code_answer_count, 0)

    def test_check_reopen_classification_tab(self):
        """
        unit tests for the Check model
        """
        self.check_one.complete_classification_tab(override="No")
        self.check_one.reopen_classification_tab()
        self.assertFalse(self.check_one.classification_check)
        self.assertIsNone(self.check_one.final_score)
        self.assertIsNone(self.check_one.final_class)
        self.assertFalse(self.check_one.final_class_overridden)

    def test_check_reopen_check(self):
        """
        unit tests for the Check model
        """
        # successfully close the check
        self.check_one.info_check = True
        self.check_one.previous_classifications_check = True
        self.check_one.classification_check = True
        check, message = self.check_one.complete_check()

        # reopen the check
        self.check_one.reopen_check()
        self.assertFalse(self.check_one.check_complete)
        self.assertIsNone(self.check_one.diagnostic)
        self.assertIsNone(self.check_one.signoff_time)

    def test_check_create_code_answers(self):
        """
        unit tests for the Check model
        """
        self.check_two.create_code_answers()
        all_code_answers = self.check_two.get_code_answers()
        code_answer_count = 0
        for code in all_code_answers:
            code_answer_count += 1
        # SVIG case - expecting 16 options
        self.assertEqual(code_answer_count, 16)

    def test_check_delete_code_answers(self):
        """
        unit tests for the Check model
        """
        self.check_one.delete_code_answers()
        all_code_answers = self.check_one.get_code_answers()
        code_answer_count = 0
        for code in all_code_answers:
            code_answer_count += 1
        self.assertEqual(code_answer_count, 0)

    def test_classify_variant_instance_is_complete(self):
        self.assertFalse(self.new_var_obj.is_complete())
        self.new_var_obj.complete_date = timezone.now()
        self.assertTrue(self.new_var_obj.is_complete())

    def test_classify_variant_instance_get_all_checks(self):
        all_checks = self.new_var_obj.get_all_checks()
        total_checks = 0
        for check in all_checks:
            total_checks += 1
        self.assertEqual(total_checks, 2)

    def test_classify_variant_instance_get_previous_checks(self):
        previous_checks = self.new_var_obj.get_previous_checks()
        self.assertEqual(previous_checks[0], self.check_one)

    def test_classify_variant_instance_get_latest_check(self):
        latest_check = self.new_var_obj.get_latest_check()
        self.assertEqual(latest_check, self.check_two)

    def test_classify_variant_instance_get_status(self):
        # checks not complete
        self.check_two.check_complete = False
        self.assertEqual(self.new_var_obj.get_status(), "Check 2")
        # complete 2nd check
        # ensure validation passes
        self.check_two.info_check = True
        self.check_two.previous_classifications_check = True
        self.check_two.classification_check = True
        check, message = self.check_two.complete_check()
        self.assertEqual(self.new_var_obj.get_status(), "Complete")

    def test_classify_variant_instance_get_classification_info_reuse_classification(self):
        self.new_var_obj.full_classification = False
        expected_info = {
            "classification_obj": self.new_var_obj,
            "current_check": self.check_two,
            "guidelines": "svig_2024",
            "somatic_or_germline": "S",
            "reused": False
        }
        info = self.new_var_obj.get_classification_info()
        # remove the queryset from the comparison - we know this function works from earlier tests
        del info["all_checks"]
        self.assertEqual(info, expected_info)

    def test_classify_variant_instance_get_classification_info_full_classification(self):
        #TODO make this test work
        # ensure validation passes
        # delete code answers from the setup, will test making them from scratch
        self.check_one.delete_code_answers()
        self.check_one.info_check = True
        self.check_one.previous_classifications_check = True
        self.check_one.classification_check = True
        self.check_one.create_code_answers()
        check, message = self.check_one.complete_check()
        self.check_one.save()

        self.check_two.info_check = True
        self.check_two.previous_classifications_check = True
        self.check_two.create_code_answers()
        self.check_two.save()

        self.new_var_obj.full_classification = True

        expected_info = {
            "classification_obj": self.new_var_obj,
            "current_check": self.check_two,
            "guidelines": "svig_2024",
            "somatic_or_germline": "S",
            "reused": False,
            "current_score": 0,
            "final_class_overridden": False,
            "current_class": "VUS"
        }
        info = self.new_var_obj.get_classification_info()
        # remove the querysets from the comparison - we know this function works from earlier tests
        del info["all_checks"]
        del info["codes_by_category"]
        self.assertEqual(info, expected_info)

        # check with manual override
        self.check_two.final_class_overridden = True
        self.check_two.final_class = FinalClassification.objects.get(pk=1)
        self.check_two.save()
        expected_info["final_class_overridden"] = True
        expected_info["current_class"] = FinalClassification.objects.get(pk=1)
        info = self.new_var_obj.get_classification_info()
        # remove the querysets from the comparison - we know this function works from earlier tests
        del info["all_checks"]
        del info["codes_by_category"]
        self.assertEqual(info, expected_info)

    def test_classify_variant_instance_get_dropdown_options(self):

        # check that a list of more than 2 paired codes raises an error
        code_list = ["PP3", "PP4", "BP6"]
        with self.assertRaises(ValueError):
            self.new_var_obj.get_dropdown_options(code_list)

        code_list = ["O10", "B7"]
        expected_dropdown_options = [
            {"value": "O10_PE|B7_PE", "text": "Pending"},
            {"value": "O10_NA|B7_NA", "text": "Not applied"},
            {"value": "O10_MO|B7_NA", "text": "O10 Moderate (+2)"},
            {"value": "O10_SU|B7_NA", "text": "O10 Supporting (+1)"},
            {"value": "O10_NA|B7_SU", "text": "B7 Supporting (-1)"},
            {"value": "O10_NA|B7_MO", "text": "B7 Moderate (-2)"}
        ]
        self.assertEqual(self.new_var_obj.get_dropdown_options(code_list), expected_dropdown_options)

    def test_classify_variant_instance_get_dropdown_value(self):
        # we need CodeAnswer objects for each code for this function to work
        self.check_two.create_code_answers()
        code_list = ["O10", "B7"]
        expected_dropdown_value = "O10_PE|B7_PE"
        self.assertEqual(self.new_var_obj.get_dropdown_value(code_list), expected_dropdown_value)
        
    def test_classify_variant_instance_get_codes_by_category(self):
        #TODO Erik this is doing ajax things
        pass

    def test_classify_variant_instance_get_order_info(self):
        #TODO Erik this is doing ajax things
        pass

    def test_classify_variant_instance_get_code_info(self):
        # Expected code info based on SVIG 2024
        self.assertEqual(self.new_var_obj.get_code_info(), expected_results.expected_codes_dict)

    # mock timezone now for time difference
    # @mock.patch(
    #         "timezone.now", 
    #         return_value=datetime(2025, 6, 30, tzinfo=timezone.utc),
    #         autospec=True
    #         )
    def test_classify_variant_instance_get_most_recent_full_classification(self):
        pass
        #TODO
        # test no previous completed classifications

        # test only response is current object

        # test previous classification but review is needed

        # test previous classification and review is not needed

    def test_classify_variant_instance_get_previous_classification_choices(self):
        pass
        #TODO
        # test within-classification full classification

        # test within-classification previous classification

        # test between classifications both options

        # test between classifications full classification only

    def test_classify_variant_instance_update_tumour_type(self):
        self.assertIsNone(self.new_var_obj.tumour_subtype)
        self.new_var_obj.update_tumour_type(1)
        self.assertEqual(self.new_var_obj.tumour_subtype.name, "Lung")

    def test_classify_variant_instance_make_new_check(self):
        # there's currently only 2 checks
        with self.assertRaises(ObjectDoesNotExist):
            Check.objects.get(pk=3)
        self.new_var_obj.make_new_check()
        self.assertIsInstance(Check.objects.get(pk=3), Check)

    def test_classify_variant_instance_reopen_analysis(self):
        # test with expected user
        status, message = self.new_var_obj.reopen_analysis(self.user_two)
        self.assertTrue(status)
        self.assertIsNone(message)
        self.assertIsNone(self.new_var_obj.final_class)
        self.assertIsNone(self.new_var_obj.final_score)
        self.assertFalse(self.new_var_obj.final_class_overridden)
        self.assertIsNone(self.new_var_obj.complete_date)
        # test with incorrect user
        status, message = self.new_var_obj.reopen_analysis("KEVIN")
        self.assertFalse(status)
        self.assertEqual("Only usertwo can reopen this case", message)

    def test_classify_variant_instance_signoff_check_extra_check(self):
        # extra check, possible to close check
        self.check_one.info_check = True
        self.check_one.previous_classifications_check = True
        self.check_one.classification_check = True
        self.check_one.complete_check()
        status, message = self.new_var_obj.signoff_check(self.check_one, "extra_check")
        self.assertTrue(status)
        self.assertIsNone(message)

    def test_classify_variant_instance_signoff_check_extra_check_cannot_close(self):
        # extra check, not possible to close check
        status, message = self.new_var_obj.signoff_check(self.check_two, "extra_check")
        self.assertFalse(status)
    
    def test_classify_variant_instance_signoff_check_send_back(self):
        # send back, possible to send back
        status, message = self.new_var_obj.signoff_check(self.check_two, "send_back")
        self.assertTrue(status)
        self.assertIsNone(message)

    def test_classify_variant_instance_signoff_check_send_back_cannot_send_back(self):
        # send back, not possible to send back
        self.check_two.delete()
        status, message = self.new_var_obj.signoff_check(self.check_one, "send_back")
        self.assertFalse(status)
        self.assertEqual(message, "Cannot send back, this is the first check")

    def test_classify_variant_instance_signoff_check_current_check_not_passable(self):
        # complete analysis, current check not passable
        status, message = self.new_var_obj.signoff_check(self.check_two, "complete")
        self.assertFalse(status)

    def test_classify_variant_instance_signoff_check_fewer_than_two_checks(self):
        self.check_one.info_check = True
        self.check_one.previous_classifications_check = True
        self.check_one.classification_check = True
        self.check_one.final_class = self.classification_one_obj
        self.check_one.complete_check()
        self.check_two.delete()
        # complete anaysis, fewer than two checks
        status, message = self.new_var_obj.signoff_check(self.check_one, "complete")
        self.assertFalse(status)
        self.assertEqual(message, "Cannot complete analysis, two checks required")

    def test_classify_variant_instance_signoff_check_fewer_than_two_diagnostic_checks(self):
        self.check_one.info_check = True
        self.check_one.previous_classifications_check = True
        self.check_one.classification_check = True
        self.check_one.diagnostic = True
        self.check_one.final_class = self.classification_one_obj
        self.check_one.complete_check()
        self.check_two.info_check = True
        self.check_two.previous_classifications_check = True
        self.check_two.classification_check = True
        self.check_two.diagnostic = False
        self.check_two.final_class = self.classification_one_obj
        self.check_two.complete_check()
        # complete analysis, fewer than two diagnostic checks
        status, message = self.new_var_obj.signoff_check(self.check_two, "complete")
        self.assertFalse(status)
        self.assertEqual(message, "Cannot complete analysis, some of the checks are training checks")

    def test_classify_variant_instance_signoff_check_classifications_disagree(self):
        self.check_one.info_check = True
        self.check_one.previous_classifications_check = True
        self.check_one.classification_check = True
        self.check_one.diagnostic = True
        self.check_one.final_class = self.classification_one_obj
        self.check_one.final_score = 10
        self.check_one.complete_check()
        self.check_two.info_check = True
        self.check_two.previous_classifications_check = True
        self.check_two.classification_check = True
        self.check_two.diagnostic = True
        self.check_two.final_class = self.classification_two_obj
        self.check_two.final_score = 9
        self.check_two.complete_check()

        # complete analysis, two checks by the same person
        #TODO add in this test after done with testing - currently commented out
        #self.check_two.user = self.user_one
        #status, message = self.new_var_obj.signoff_check(self.check_two, "complete")
        #self.assertFalse(status)
        #self.assertEqual(message, "Cannot complete analysis, last two checkers are the same analyst")
        #self.check_two.user = self.user

        # complete analysis, last two classifications don't agree
        status, message = self.new_var_obj.signoff_check(self.check_two, "complete")
        self.assertFalse(status)
        self.assertEqual(message, "Cannot complete analysis, overall classification from last two checkers dont agree")
        
        # complete analysis, last two scores don't agree
        self.check_two.final_class = self.classification_one_obj
        self.check_two.save()
        status, message = self.new_var_obj.signoff_check(self.check_two, "complete")
        self.assertFalse(status)
        self.assertEqual(message, "Cannot complete analysis, scores from last two checkers dont agree")

        # all checks pass, update object
        self.check_two.final_score = 10
        self.check_two.save()
        status, message = self.new_var_obj.signoff_check(self.check_two, "complete")
        self.assertTrue(status)
        self.assertIsNone(message)

    def test_analysis_variant_instance_get_sample_info(self):
        # check sample info when tumour type not assigned
        expected_sample_info = {
            "sample_id": "dna_test_1",
            "worksheet_id": "dna_ws_1",
            "svd_panel": "Tumour",
            "specific_tumour_type": None
        }
        self.assertEqual(self.new_var_obj.get_sample_info(), expected_sample_info)
        # check sample info when tumour type assigned
        self.new_var_obj.update_tumour_type(1)
        expected_sample_info = {
            "sample_id": "dna_test_1",
            "worksheet_id": "dna_ws_1",
            "svd_panel": "Tumour",
            "specific_tumour_type": "Lung"
        }
        self.assertEqual(self.new_var_obj.get_sample_info(), expected_sample_info)

    def test_swgs_germline_variant_instance_get_sample_info(self):
        #TODO write this code first
        pass

    def test_swgs_somatic_variant_instance_get_sample_info(self):
        #TODO write this code first
        pass

    def test_manual_variant_instance_get_sample_info(self):
        #TODO write this code first
        pass

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
        
        expected_classification_dict = {
            "Benign": -9999,
            "Likely benign": -6,
            "VUS": 0,
            "Likely oncogenic": 6,
            "Oncogenic": 10
        }

        expected_classification_tuple = (
            (1, "Benign"), (2, "Likely benign"), (3, "VUS"), (7, "Likely oncogenic"), (9, "Oncogenic")
        )

        self.assertEqual(self.guideline_obj.create_final_classification_ordered_dict(), expected_classification_dict)
        self.assertEqual(self.guideline_obj.create_final_classification_tuple(), expected_classification_tuple)
