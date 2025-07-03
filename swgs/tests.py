from django.test import TestCase
from django.utils import timezone

from swgs.models import *
from swgs.utils import * 


class TestVEPAnnotationsPubmed(TestCase):
    """
    Tests for the VEPAnnotationsPubmed model
    """

    def test_format_pubmed_link(self):
        p = VEPAnnotationsPubmed(pubmed_id="123456")
        expected_link = "https://pubmed.ncbi.nlm.nih.gov/123456/"
        self.assertEqual(p.format_pubmed_link(), expected_link)


class TestVEPAnnotationsClinvar(TestCase):
    """
    Tests for the VEPAnnotationsClinvar model
    """

    def test_format_clinvar_link(self):
        pass


class TestVEPAnnotationsConsequence(TestCase):
    """
    Tests for the VEPAnnotaitonsConsequence model
    """

    def test_display_term(self):
        i = VEPAnnotationsImpact(impact="HIGH")
        c = VEPAnnotationsConsequence(consequence="transcript_ablation", impact=i)
        expected_display_term = "transcript ablation"
        self.assertEqual(expected_display_term, c.format_display_term())

class TestCheckStatusUpdate(TestCase):
    """
    Tests for the status update after checks are submitted
    """

    def setUp(self):
        """
        Make some models to test
        """

        self.user = User.objects.create_user('test_user','test@test.com', 'test123')
        self.user2 = User.objects.create_user('test_user2', 'test2@test.com', 'test123')
        self.client.login(username='test_user', password='test123')

        genome_obj = GenomeBuild.objects.create(
            genome_build = "38"
        )
        
        variant_obj = Variant.objects.create(
            variant = "chr1:5:A>T",
            genome_build = genome_obj
        )

        patient_obj = Patient.objects.create(
            nhs_number = "1"
        )

        tumour_sample = Sample.objects.create(
            sample_id = "tumour"
        )

        germline_sample = Sample.objects.create(
            sample_id = "germline"
        )

        indication_obj = Indication.objects.create(
            indication = "1"
        )

        run_obj = Run.objects.create(
            run = "run1",
            worksheet = "ws1"
        )

        germline_cnv_quality_obj = QCGermlineCNVQuality.objects.create(
            passing_cnv_count = 10,
            passing_fraction = 1.0,
            log_loss_gain = 0.1
        )

        germline_ntc_obj = QCNTCContamination.objects.create(
            ntc_contamination = 0.01
        )

        low_qual_tumour = QCLowQualityTumourSample.objects.create(
            unevenness_of_coverage = 0.1,
            median_fragment_length = 0.1,
            at_drop = 0.1,
            cg_drop = 0.1
        )

        relatedness_obj = QCRelatedness.objects.create(
            relatedness = 0.1
        )

        somatic_vaf_obj = QCSomaticVAFDistribution.objects.create(
            low_vaf_proportion = 0.1
        )

        tumour_in_normal = QCTumourInNormalContamination.objects.create(
        )

        tumour_ntc_obj = QCNTCContamination.objects.create(
            ntc_contamination = 0.02
        )

        tumour_purity_obj = QCTumourPurity.objects.create(
            tumour_purity = 0.95
        )

        patient_analysis_obj = PatientAnalysis.objects.create(
            patient = patient_obj,
            tumour_sample = tumour_sample,
            germline_sample = germline_sample,
            indication = indication_obj,
            run = run_obj,
            germline_cnv_quality = germline_cnv_quality_obj,
            germline_ntc_contamination = germline_ntc_obj,
            low_quality_tumour_sample = low_qual_tumour,
            relatedness = relatedness_obj,
            somatic_vaf_distribution = somatic_vaf_obj,
            tumour_in_normal_contamination =  tumour_in_normal,
            tumour_ntc_contamination = tumour_ntc_obj,
            tumour_purity = tumour_purity_obj
        )

        variant_instance = GermlineVariantInstance.objects.create(
            variant = variant_obj,
            patient_analysis = patient_analysis_obj,
            ad = "10",
            af = 0.1,
            dp = 10,
        )

    def test_update_status(self):
        """
        Testing the function, additionally tests get checks too
        """

        #Get variant instance
        variant_instance = GermlineVariantInstance.objects.get(id=1)

        #No checks - after running command, status should still be pending
        variant_instance.update_status()
        self.assertEqual(variant_instance.status, 'P')

        #Add a check
        check1 = GermlineIGVCheck.objects.create(
            variant_instance = variant_instance,
            decision = "G",
            user = self.user,
            check_date = timezone.now()
        )

        checks = variant_instance.get_all_checks()
        self.assertEqual(len(checks), 1)
        self.assertEqual(checks[0]['decision'], 'Genuine')

        #One check so should still be pending
        variant_instance.update_status()
        self.assertEqual(variant_instance.status, 'P')

        #Add a second check, different user
        check2 = GermlineIGVCheck.objects.create(
            variant_instance = variant_instance,
            decision = "G",
            user = self.user2,
            check_date = timezone.now()
        )

        checks = variant_instance.get_all_checks()
        self.assertEqual(len(checks), 2)

        #Two matching checks, different users, now complete
        variant_instance.update_status()
        self.assertEqual(variant_instance.status, 'C')

        #Reset status and remove last check
        variant_instance.status = 'P'
        variant_instance.save()
        check2.delete()

        #Now add another second check, this time with same user as first
        check2 = GermlineIGVCheck.objects.create(
            variant_instance = variant_instance,
            decision = "G",
            user = self.user,
            check_date = timezone.now()
        )

        checks = variant_instance.get_all_checks()
        self.assertEqual(len(checks), 2)

        #Two matching checks, same user, still pending
        variant_instance.update_status()
        self.assertEqual(variant_instance.status, 'P')

        #Add third matching check with different user, then should complete
        check3 = GermlineIGVCheck.objects.create(
            variant_instance = variant_instance,
            decision = "G",
            user = self.user2,
            check_date = timezone.now()
        )

        checks = variant_instance.get_all_checks()
        self.assertEqual(len(checks), 3)

        #Three checks, Last two matching, different users, now complete
        variant_instance.update_status()
        self.assertEqual(variant_instance.status, 'C')

        #Reset status and remove last check
        variant_instance.status = 'P'
        variant_instance.save()
        check3.delete()

        #Add a check from a different user, but this time different decision, will stay pending
        check3 = GermlineIGVCheck.objects.create(
            variant_instance = variant_instance,
            decision = "A",
            user = self.user2,
            check_date = timezone.now()
        )

        checks = variant_instance.get_all_checks()
        self.assertEqual(len(checks), 3)

        #Three checks, last two different, different users, still pending
        variant_instance.update_status()
        self.assertEqual(variant_instance.status, 'P')

        #Remove all the checks to start afresh, check that it doesn't complete with two not analysed
        GermlineIGVCheck.objects.all().delete()

        #First not analysed
        checkN1 = GermlineIGVCheck.objects.create(
            variant_instance = variant_instance,
            decision = "N",
            user = self.user,
            check_date = timezone.now()
        )

        #One check, still pending
        variant_instance.update_status()
        self.assertEqual(variant_instance.status, 'P')

        #Second not analysed, different user
        checkN2 = GermlineIGVCheck.objects.create(
            variant_instance = variant_instance,
            decision = "N",
            user = self.user2,
            check_date = timezone.now()
        )

        #Two matching checks, with different users, but still pending as Not Analysed
        variant_instance.update_status()
        self.assertEqual(variant_instance.status, 'P')










        

