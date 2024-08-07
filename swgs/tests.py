from django.test import TestCase
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

