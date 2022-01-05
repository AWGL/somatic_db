from django.test import TestCase
from analysis.utils import *

from decimal import Decimal


class TestViews(TestCase):
	"""
	Test ability to navigate through the different pages of the database

	"""

	# load in test data
	fixtures = ['dna_test_1.json']

	def setUp(self):
		''' Runs before each test '''
		self.client.login(username='test', password='hello123')


	def test_signup(self):
		''' Access signup page '''
		self.client.logout()
		response = self.client.get('/signup', follow=True)
		self.assertEqual(response.status_code, 200)


	def test_login(self):
		''' Access login page '''
		self.client.logout()
		response = self.client.get('/login', follow=True)
		self.assertEqual(response.status_code, 200)


	def test_view_worksheets(self):
		''' Access worksheets page '''
		response = self.client.get('/worksheets', follow=True)
		self.assertEqual(response.status_code, 200)


	def test_logout(self):
		''' Access logout page '''
		response = self.client.get('/logout', follow=True)
		self.assertEqual(response.status_code, 200)


class TestDna(TestCase):
	"""
	Load in DNA control sample with each virtual panel applied, test that data is as expected

	"""

	# load in test data
	fixtures = ['dna_test_1.json']


	def test_get_samples(self):
		'''
		Pull correct sample info from worksheet

		'''
		samples = SampleAnalysis.objects.filter(worksheet = 'dna_ws_1')
		samples_dict = get_samples(samples)

		self.assertEqual(list(samples_dict.keys()), ['dna_test_1'])

		sample = samples_dict.get('dna_test_1')
		self.assertEqual(sample.get('dna_rna'), 'DNA')


	def test_get_sample_info_dna(self):
		'''
		Loop through each panel and get the sample info
		The control panel has been uploaded with each of the different panels applied
		
		'''
		panels = ['Tumour', 'Lung', 'Glioma', 'Thyroid', 'GIST', 'Melanoma', 'Colorectal']

		for panel in panels:
			panel_obj = Panel.objects.get(panel_name=panel, dna_or_rna='DNA')

			sample = SampleAnalysis.objects.get(sample_id='dna_test_1', panel=panel_obj)

			sample_info = get_sample_info(sample)

			self.assertEqual(sample_info.get('dna_or_rna'), 'DNA')
			self.assertEqual(sample_info.get('sample_id'), 'dna_test_1')
			self.assertEqual(sample_info.get('worksheet_id'), 'dna_ws_1')
			self.assertEqual(sample_info.get('panel'), panel)
			self.assertEqual(sample_info.get('run_id'), 'run_1')
			self.assertEqual(sample_info.get('total_reads'), None)
			self.assertEqual(sample_info.get('total_reads_ntc'), None)
			self.assertEqual((sample_info.get('checks')).get('current_status'), 'IGV check 1')
			self.assertEqual((sample_info.get('checks')).get('assigned_to'), None)


	def test_get_variant_info_tumour(self):
		'''
		Check a subset of variants in the tumour panel

		'''
		panel_obj = Panel.objects.get(panel_name='Tumour', dna_or_rna='DNA')

		sample = SampleAnalysis.objects.get(sample_id='dna_test_1', panel=panel_obj)
		sample_data = get_sample_info(sample)

		variant_calls = get_variant_info(sample_data, sample)['variant_calls']

		variant_0 = variant_calls[0]
		variant_5 = variant_calls[5]
		variant_14 = variant_calls[14]
		variant_22 = variant_calls[22]
		variant_37 = variant_calls[37]
		variant_44 = variant_calls[44]
		variant_58 = variant_calls[58]
		variant_63 = variant_calls[63]
		variant_72 = variant_calls[72]
		variant_77 = variant_calls[77]

		self.assertEqual(variant_0.get('genomic'), '1:27023212C>T')
		self.assertEqual(variant_0.get('gene'), 'ARID1A')
		self.assertEqual(variant_0.get('exon'), '1/20')
		self.assertEqual(variant_0.get('hgvs_c'), 'NM_006015.4:c.318C>T')
		self.assertEqual(variant_0.get('hgvs_p'), 'NM_006015.4:c.318C>T(p.(Asn106=))')
		self.assertEqual((variant_0.get('vaf').get('vaf')), Decimal('7.71'))
		self.assertEqual((variant_0.get('vaf').get('total_count')), 363)
		self.assertEqual((variant_0.get('vaf').get('alt_count')), 28)
		self.assertEqual(variant_0.get('checks'), ['Pending'])

		self.assertEqual(variant_5.get('genomic'), '1:27105930TG>T')
		self.assertEqual(variant_5.get('gene'), 'ARID1A')
		self.assertEqual(variant_5.get('exon'), '20/20')
		self.assertEqual(variant_5.get('hgvs_c'), 'NM_006015.4:c.5548del')
		self.assertEqual(variant_5.get('hgvs_p'), 'NP_006006.3:p.(Asp1850ThrfsTer33)')
		self.assertEqual((variant_5.get('vaf').get('vaf')), Decimal('10.39'))
		self.assertEqual((variant_5.get('vaf').get('total_count')), 1587)
		self.assertEqual((variant_5.get('vaf').get('alt_count')), 165)
		self.assertEqual(variant_5.get('checks'), ['Pending'])

		self.assertEqual(variant_14.get('genomic'), '7:55241707G>A')
		self.assertEqual(variant_14.get('gene'), 'EGFR')
		self.assertEqual(variant_14.get('exon'), '18/28')
		self.assertEqual(variant_14.get('hgvs_c'), 'NM_005228.4:c.2155G>A')
		self.assertEqual(variant_14.get('hgvs_p'), 'NP_005219.2:p.(Gly719Ser)')
		self.assertEqual((variant_14.get('vaf').get('vaf')), Decimal('3.67'))
		self.assertEqual((variant_14.get('vaf').get('total_count')), 1471)
		self.assertEqual((variant_14.get('vaf').get('alt_count')), 54)
		self.assertEqual(variant_14.get('checks'), ['Pending'])

		self.assertEqual(variant_22.get('genomic'), '10:43595968A>G')
		self.assertEqual(variant_22.get('gene'), 'RET')
		self.assertEqual(variant_22.get('exon'), '2/20')
		self.assertEqual(variant_22.get('hgvs_c'), 'NM_020975.4:c.135=')
		self.assertEqual(variant_22.get('hgvs_p'), 'NM_020975.4:c.135=(p.(Ala45=))')
		self.assertEqual((variant_22.get('vaf').get('vaf')), Decimal('76.27'))
		self.assertEqual((variant_22.get('vaf').get('total_count')), 1450)
		self.assertEqual((variant_22.get('vaf').get('alt_count')), 1106)
		self.assertEqual(variant_22.get('checks'), ['Pending'])

		self.assertEqual(variant_37.get('genomic'), '13:32911463A>G')
		self.assertEqual(variant_37.get('gene'), 'BRCA2')
		self.assertEqual(variant_37.get('exon'), '11/27')
		self.assertEqual(variant_37.get('hgvs_c'), 'NM_000059.3:c.2971A>G')
		self.assertEqual(variant_37.get('hgvs_p'), 'NP_000050.2:p.(Asn991Asp)')
		self.assertEqual((variant_37.get('vaf').get('vaf')), Decimal('8.44'))
		self.assertEqual((variant_37.get('vaf').get('total_count')), 876)
		self.assertEqual((variant_37.get('vaf').get('alt_count')), 74)
		self.assertEqual(variant_37.get('checks'), ['Pending'])

		self.assertEqual(variant_44.get('genomic'), '13:32913836CA>C')
		self.assertEqual(variant_44.get('gene'), 'BRCA2')
		self.assertEqual(variant_44.get('exon'), '11/27')
		self.assertEqual(variant_44.get('hgvs_c'), 'NM_000059.3:c.5351del')
		self.assertEqual(variant_44.get('hgvs_p'), 'NP_000050.2:p.(Asn1784ThrfsTer7)')
		self.assertEqual((variant_44.get('vaf').get('vaf')), Decimal('15.09'))
		self.assertEqual((variant_44.get('vaf').get('total_count')), 795)
		self.assertEqual((variant_44.get('vaf').get('alt_count')), 120)
		self.assertEqual(variant_44.get('checks'), ['Pending'])

		self.assertEqual(variant_58.get('genomic'), '17:41234470A>G')
		self.assertEqual(variant_58.get('gene'), 'BRCA1')
		self.assertEqual(variant_58.get('exon'), '12/23')
		self.assertEqual(variant_58.get('hgvs_c'), 'NM_007294.3:c.4308T>C')
		self.assertEqual(variant_58.get('hgvs_p'), 'NM_007294.3:c.4308T>C(p.(Ser1436=))')
		self.assertEqual((variant_58.get('vaf').get('vaf')), Decimal('20.63'))
		self.assertEqual((variant_58.get('vaf').get('total_count')), 1565)
		self.assertEqual((variant_58.get('vaf').get('alt_count')), 323)
		self.assertEqual(variant_58.get('checks'), ['Pending'])

		self.assertEqual(variant_63.get('genomic'), '17:41245090T>C')
		self.assertEqual(variant_63.get('gene'), 'BRCA1')
		self.assertEqual(variant_63.get('exon'), '10/23')
		self.assertEqual(variant_63.get('hgvs_c'), 'NM_007294.3:c.2458A>G')
		self.assertEqual(variant_63.get('hgvs_p'), 'NP_009225.1:p.(Lys820Glu)')
		self.assertEqual((variant_63.get('vaf').get('vaf')), Decimal('9.39'))
		self.assertEqual((variant_63.get('vaf').get('total_count')), 1480)
		self.assertEqual((variant_63.get('vaf').get('alt_count')), 139)
		self.assertEqual(variant_63.get('checks'), ['Pending'])

		self.assertEqual(variant_72.get('genomic'), 'X:76937963G>C')
		self.assertEqual(variant_72.get('gene'), 'ATRX')
		self.assertEqual(variant_72.get('exon'), '9/35')
		self.assertEqual(variant_72.get('hgvs_c'), 'NM_000489.4:c.2785=')
		self.assertEqual(variant_72.get('hgvs_p'), 'NM_000489.4:c.2785=(p.(Glu929=))')
		self.assertEqual((variant_72.get('vaf').get('vaf')), Decimal('30.72'))
		self.assertEqual((variant_72.get('vaf').get('total_count')), 742)
		self.assertEqual((variant_72.get('vaf').get('alt_count')), 228)
		self.assertEqual(variant_72.get('checks'), ['Pending'])

		self.assertEqual(variant_77.get('genomic'), '13:32972286AT>-')
		self.assertEqual(variant_77.get('gene'), 'N4BP2L1')
		self.assertEqual(variant_77.get('exon'), '')
		self.assertEqual(variant_77.get('hgvs_c'), '')
		self.assertEqual(variant_77.get('hgvs_p'), '')
		self.assertEqual((variant_77.get('vaf').get('vaf')), Decimal('4.45'))
		self.assertEqual((variant_77.get('vaf').get('total_count')), 292)
		self.assertEqual((variant_77.get('vaf').get('alt_count')), 13)
		self.assertEqual(variant_77.get('checks'), ['Pending'])


	def test_get_variant_info_gist(self):
		'''
		Check a subset of variants in the GIST panel

		'''
		panel_obj = Panel.objects.get(panel_name='GIST', dna_or_rna='DNA')

		sample = SampleAnalysis.objects.get(sample_id='dna_test_1', panel=panel_obj)
		sample_data = get_sample_info(sample)

		variant_calls = get_variant_info(sample_data, sample)['variant_calls']

		variant_0 = variant_calls[0]
		variant_1 = variant_calls[1]
		variant_2 = variant_calls[2]

		self.assertEqual(variant_0.get('genomic'), '4:55141055A>G')
		self.assertEqual(variant_0.get('gene'), 'PDGFRA')
		self.assertEqual(variant_0.get('exon'), '12/23')
		self.assertEqual(variant_0.get('hgvs_c'), 'NM_006206.5:c.1701A>G')
		self.assertEqual(variant_0.get('hgvs_p'), 'NM_006206.5:c.1701A>G(p.(Pro567=))')
		self.assertEqual((variant_0.get('vaf').get('vaf')), Decimal('99.85'))
		self.assertEqual((variant_0.get('vaf').get('total_count')), 1404)
		self.assertEqual((variant_0.get('vaf').get('alt_count')), 1402)
		self.assertEqual(variant_0.get('checks'), ['Pending'])

		self.assertEqual(variant_1.get('genomic'), '4:55152040C>T')
		self.assertEqual(variant_1.get('gene'), 'PDGFRA')
		self.assertEqual(variant_1.get('exon'), '18/23')
		self.assertEqual(variant_1.get('hgvs_c'), 'NM_006206.5:c.2472C>T')
		self.assertEqual(variant_1.get('hgvs_p'), 'NM_006206.5:c.2472C>T(p.(Val824=))')
		self.assertEqual((variant_1.get('vaf').get('vaf')), Decimal('18.75'))
		self.assertEqual((variant_1.get('vaf').get('total_count')), 1445)
		self.assertEqual((variant_1.get('vaf').get('alt_count')), 271)
		self.assertEqual(variant_1.get('checks'), ['Pending'])

		self.assertEqual(variant_2.get('genomic'), '4:55599268C>T')
		self.assertEqual(variant_2.get('gene'), 'KIT')
		self.assertEqual(variant_2.get('exon'), '17/21')
		self.assertEqual(variant_2.get('hgvs_c'), 'NM_000222.2:c.2394C>T')
		self.assertEqual(variant_2.get('hgvs_p'), 'NM_000222.2:c.2394C>T(p.(Ile798=))')
		self.assertEqual((variant_2.get('vaf').get('vaf')), Decimal('3.57'))
		self.assertEqual((variant_2.get('vaf').get('total_count')), 1090)
		self.assertEqual((variant_2.get('vaf').get('alt_count')), 39)
		self.assertEqual(variant_2.get('checks'), ['Pending'])


	def test_get_variant_info_glioma(self):
		'''
		Check a subset of variants in the glioma panel

		'''
		panel_obj = Panel.objects.get(panel_name='Glioma', dna_or_rna='DNA')

		sample = SampleAnalysis.objects.get(sample_id='dna_test_1', panel=panel_obj)
		sample_data = get_sample_info(sample)

		variant_calls = get_variant_info(sample_data, sample)['variant_calls']

		variant_0 = variant_calls[0]
		variant_6 = variant_calls[6]
		variant_12 = variant_calls[12]
		variant_19 = variant_calls[19]

		self.assertEqual(variant_0.get('genomic'), '2:209113192G>A')
		self.assertEqual(variant_0.get('gene'), 'IDH1')
		self.assertEqual(variant_0.get('exon'), '4/10')
		self.assertEqual(variant_0.get('hgvs_c'), 'NM_005896.3:c.315C>T')
		self.assertEqual(variant_0.get('hgvs_p'), 'NM_005896.3:c.315C>T(p.(Gly105=))')
		self.assertEqual((variant_0.get('vaf').get('vaf')), Decimal('15.55'))
		self.assertEqual((variant_0.get('vaf').get('total_count')), 1234)
		self.assertEqual((variant_0.get('vaf').get('alt_count')), 192)
		self.assertEqual(variant_0.get('checks'), ['Pending'])

		self.assertEqual(variant_6.get('genomic'), '9:21970916C>T')
		self.assertEqual(variant_6.get('gene'), 'CDKN2A')
		self.assertEqual(variant_6.get('exon'), '2/3')
		self.assertEqual(variant_6.get('hgvs_c'), 'NM_000077.4:c.442G>A')
		self.assertEqual(variant_6.get('hgvs_p'), 'NP_000068.1:p.(Ala148Thr)')
		self.assertEqual((variant_6.get('vaf').get('vaf')), Decimal('7.71'))
		self.assertEqual((variant_6.get('vaf').get('total_count')), 687)
		self.assertEqual((variant_6.get('vaf').get('alt_count')), 53)
		self.assertEqual(variant_6.get('checks'), ['Pending'])

		self.assertEqual(variant_12.get('genomic'), '17:7578419C>A')
		self.assertEqual(variant_12.get('gene'), 'TP53')
		self.assertEqual(variant_12.get('exon'), '5/11')
		self.assertEqual(variant_12.get('hgvs_c'), 'NM_000546.5:c.511G>T')
		self.assertEqual(variant_12.get('hgvs_p'), 'NP_000537.3:p.(Glu171Ter)')
		self.assertEqual((variant_12.get('vaf').get('vaf')), Decimal('15.95'))
		self.assertEqual((variant_12.get('vaf').get('total_count')), 1460)
		self.assertEqual((variant_12.get('vaf').get('alt_count')), 233)
		self.assertEqual(variant_12.get('checks'), ['Pending'])

		self.assertEqual(variant_19.get('genomic'), 'X:76938208A>G')
		self.assertEqual(variant_19.get('gene'), 'ATRX')
		self.assertEqual(variant_19.get('exon'), '9/35')
		self.assertEqual(variant_19.get('hgvs_c'), 'NM_000489.4:c.2540T>C')
		self.assertEqual(variant_19.get('hgvs_p'), 'NP_000480.3:p.(Phe847Ser)')
		self.assertEqual((variant_19.get('vaf').get('vaf')), Decimal('6.65'))
		self.assertEqual((variant_19.get('vaf').get('total_count')), 526)
		self.assertEqual((variant_19.get('vaf').get('alt_count')), 35)
		self.assertEqual(variant_19.get('checks'), ['Pending'])


	def test_get_variant_info_lung(self):
		'''
		Check a subset of variants in the lung panel

		'''
		panel_obj = Panel.objects.get(panel_name='Lung', dna_or_rna='DNA')

		sample = SampleAnalysis.objects.get(sample_id='dna_test_1', panel=panel_obj)
		sample_data = get_sample_info(sample)

		variant_calls = get_variant_info(sample_data, sample)['variant_calls']

		variant_0 = variant_calls[0]
		variant_1 = variant_calls[1]
		variant_4 = variant_calls[4]
		variant_5 = variant_calls[5]

		self.assertEqual(variant_0.get('genomic'), '7:55241707G>A')
		self.assertEqual(variant_0.get('gene'), 'EGFR')
		self.assertEqual(variant_0.get('exon'), '18/28')
		self.assertEqual(variant_0.get('hgvs_c'), 'NM_005228.4:c.2155G>A')
		self.assertEqual(variant_0.get('hgvs_p'), 'NP_005219.2:p.(Gly719Ser)')
		self.assertEqual((variant_0.get('vaf').get('vaf')), Decimal('3.67'))
		self.assertEqual((variant_0.get('vaf').get('total_count')), 1471)
		self.assertEqual((variant_0.get('vaf').get('alt_count')), 54)
		self.assertEqual(variant_0.get('checks'), ['Pending'])

		self.assertEqual(variant_1.get('genomic'), '7:55242464AGGAATTAAGAGAAGC>A')
		self.assertEqual(variant_1.get('gene'), 'EGFR')
		self.assertEqual(variant_1.get('exon'), '19/28')
		self.assertEqual(variant_1.get('hgvs_c'), 'NM_005228.4:c.2235_2249del')
		self.assertEqual(variant_1.get('hgvs_p'), 'NP_005219.2:p.(Glu746_Ala750del)')
		self.assertEqual((variant_1.get('vaf').get('vaf')), Decimal('3.78'))
		self.assertEqual((variant_1.get('vaf').get('total_count')), 1742)
		self.assertEqual((variant_1.get('vaf').get('alt_count')), 66)
		self.assertEqual(variant_1.get('checks'), ['Pending'])

		self.assertEqual(variant_4.get('genomic'), '7:140453136A>T')
		self.assertEqual(variant_4.get('gene'), 'BRAF')
		self.assertEqual(variant_4.get('exon'), '15/18')
		self.assertEqual(variant_4.get('hgvs_c'), 'NM_004333.4:c.1799T>A')
		self.assertEqual(variant_4.get('hgvs_p'), 'NP_004324.2:p.(Val600Glu)')
		self.assertEqual((variant_4.get('vaf').get('vaf')), Decimal('14.41'))
		self.assertEqual((variant_4.get('vaf').get('total_count')), 1283)
		self.assertEqual((variant_4.get('vaf').get('alt_count')), 185)
		self.assertEqual(variant_4.get('checks'), ['Pending'])

		self.assertEqual(variant_5.get('genomic'), '12:25398281C>T')
		self.assertEqual(variant_5.get('gene'), 'KRAS')
		self.assertEqual(variant_5.get('exon'), '2/6')
		self.assertEqual(variant_5.get('hgvs_c'), 'NM_033360.3:c.38G>A')
		self.assertEqual(variant_5.get('hgvs_p'), 'NP_203524.1:p.(Gly13Asp)')
		self.assertEqual((variant_5.get('vaf').get('vaf')), Decimal('5.02'))
		self.assertEqual((variant_5.get('vaf').get('total_count')), 1015)
		self.assertEqual((variant_5.get('vaf').get('alt_count')), 51)
		self.assertEqual(variant_5.get('checks'), ['Pending'])


	def test_get_variant_info_melanoma(self):
		'''
		Check a subset of variants in the melanoma panel

		'''
		panel_obj = Panel.objects.get(panel_name='Melanoma', dna_or_rna='DNA')

		sample = SampleAnalysis.objects.get(sample_id='dna_test_1', panel=panel_obj)
		sample_data = get_sample_info(sample)

		variant_calls = get_variant_info(sample_data, sample)['variant_calls']

		variant_0 = variant_calls[0]
		variant_1 = variant_calls[1]

		self.assertEqual(variant_0.get('genomic'), '4:55599268C>T')
		self.assertEqual(variant_0.get('gene'), 'KIT')
		self.assertEqual(variant_0.get('exon'), '17/21')
		self.assertEqual(variant_0.get('hgvs_c'), 'NM_000222.2:c.2394C>T')
		self.assertEqual(variant_0.get('hgvs_p'), 'NM_000222.2:c.2394C>T(p.(Ile798=))')
		self.assertEqual((variant_0.get('vaf').get('vaf')), Decimal('3.57'))
		self.assertEqual((variant_0.get('vaf').get('total_count')), 1090)
		self.assertEqual((variant_0.get('vaf').get('alt_count')), 39)
		self.assertEqual(variant_0.get('checks'), ['Pending'])

		self.assertEqual(variant_1.get('genomic'), '7:140453136A>T')
		self.assertEqual(variant_1.get('gene'), 'BRAF')
		self.assertEqual(variant_1.get('exon'), '15/18')
		self.assertEqual(variant_1.get('hgvs_c'), 'NM_004333.4:c.1799T>A')
		self.assertEqual(variant_1.get('hgvs_p'), 'NP_004324.2:p.(Val600Glu)')
		self.assertEqual((variant_1.get('vaf').get('vaf')), Decimal('14.41'))
		self.assertEqual((variant_1.get('vaf').get('total_count')), 1283)
		self.assertEqual((variant_1.get('vaf').get('alt_count')), 185)
		self.assertEqual(variant_1.get('checks'), ['Pending'])


	def test_get_variant_info_colorectal(self):
		'''
		Check a subset of variants in the colorectal panel

		'''
		panel_obj = Panel.objects.get(panel_name='Colorectal', dna_or_rna='DNA')

		sample = SampleAnalysis.objects.get(sample_id='dna_test_1', panel=panel_obj)
		sample_data = get_sample_info(sample)

		variant_calls = get_variant_info(sample_data, sample)['variant_calls']

		variant_0 = variant_calls[0]
		variant_8 = variant_calls[8]
		variant_11 = variant_calls[11]

		self.assertEqual(variant_0.get('genomic'), '3:178936091G>A')
		self.assertEqual(variant_0.get('gene'), 'PIK3CA')
		self.assertEqual(variant_0.get('exon'), '10/21')
		self.assertEqual(variant_0.get('hgvs_c'), 'NM_006218.3:c.1633G>A')
		self.assertEqual(variant_0.get('hgvs_p'), 'NP_006209.2:p.(Glu545Lys)')
		self.assertEqual((variant_0.get('vaf').get('vaf')), Decimal('3.46'))
		self.assertEqual((variant_0.get('vaf').get('total_count')), 1040)
		self.assertEqual((variant_0.get('vaf').get('alt_count')), 36)
		self.assertEqual(variant_0.get('checks'), ['Pending'])

		self.assertEqual(variant_8.get('genomic'), '17:7577559G>A')
		self.assertEqual(variant_8.get('gene'), 'TP53')
		self.assertEqual(variant_8.get('exon'), '7/11')
		self.assertEqual(variant_8.get('hgvs_c'), 'NM_000546.5:c.722C>T')
		self.assertEqual(variant_8.get('hgvs_p'), 'NP_000537.3:p.(Ser241Phe)')
		self.assertEqual((variant_8.get('vaf').get('vaf')), Decimal('9.18'))
		self.assertEqual((variant_8.get('vaf').get('total_count')), 1089)
		self.assertEqual((variant_8.get('vaf').get('alt_count')), 100)
		self.assertEqual(variant_8.get('checks'), ['Pending'])

		self.assertEqual(variant_11.get('genomic'), '17:7579472G>C')
		self.assertEqual(variant_11.get('gene'), 'TP53')
		self.assertEqual(variant_11.get('exon'), '4/11')
		self.assertEqual(variant_11.get('hgvs_c'), 'NM_000546.5:c.215C>G')
		self.assertEqual(variant_11.get('hgvs_p'), 'NP_000537.3:p.(Pro72Arg)')
		self.assertEqual((variant_11.get('vaf').get('vaf')), Decimal('82.79'))
		self.assertEqual((variant_11.get('vaf').get('total_count')), 1412)
		self.assertEqual((variant_11.get('vaf').get('alt_count')), 1169)
		self.assertEqual(variant_11.get('checks'), ['Pending'])


	def test_get_variant_info_thyroid(self):
		'''
		Check a subset of variants in the thyroid panel

		'''
		panel_obj = Panel.objects.get(panel_name='Thyroid', dna_or_rna='DNA')

		sample = SampleAnalysis.objects.get(sample_id='dna_test_1', panel=panel_obj)
		sample_data = get_sample_info(sample)

		variant_calls = get_variant_info(sample_data, sample)['variant_calls']

		variant_1 = variant_calls[1]
		variant_9 = variant_calls[9]
		variant_14 = variant_calls[14]

		self.assertEqual(variant_1.get('genomic'), '10:43595968A>G')
		self.assertEqual(variant_1.get('gene'), 'RET')
		self.assertEqual(variant_1.get('exon'), '2/20')
		self.assertEqual(variant_1.get('hgvs_c'), 'NM_020975.4:c.135=')
		self.assertEqual(variant_1.get('hgvs_p'), 'NM_020975.4:c.135=(p.(Ala45=))')
		self.assertEqual((variant_1.get('vaf').get('vaf')), Decimal('76.27'))
		self.assertEqual((variant_1.get('vaf').get('total_count')), 1450)
		self.assertEqual((variant_1.get('vaf').get('alt_count')), 1106)
		self.assertEqual(variant_1.get('checks'), ['Pending'])

		self.assertEqual(variant_9.get('genomic'), '11:534242A>G')
		self.assertEqual(variant_9.get('gene'), 'HRAS')
		self.assertEqual(variant_9.get('exon'), '2/6')
		self.assertEqual(variant_9.get('hgvs_c'), 'NM_005343.3:c.81T>C')
		self.assertEqual(variant_9.get('hgvs_p'), 'NM_005343.3:c.81T>C(p.(His27=))')
		self.assertEqual((variant_9.get('vaf').get('vaf')), Decimal('25.84'))
		self.assertEqual((variant_9.get('vaf').get('total_count')), 1180)
		self.assertEqual((variant_9.get('vaf').get('alt_count')), 305)
		self.assertEqual(variant_9.get('checks'), ['Pending'])

		self.assertEqual(variant_14.get('genomic'), '17:7579472G>C')
		self.assertEqual(variant_14.get('gene'), 'TP53')
		self.assertEqual(variant_14.get('exon'), '4/11')
		self.assertEqual(variant_14.get('hgvs_c'), 'NM_000546.5:c.215C>G')
		self.assertEqual(variant_14.get('hgvs_p'), 'NP_000537.3:p.(Pro72Arg)')
		self.assertEqual((variant_14.get('vaf').get('vaf')), Decimal('82.79'))
		self.assertEqual((variant_14.get('vaf').get('total_count')), 1412)
		self.assertEqual((variant_14.get('vaf').get('alt_count')), 1169)
		self.assertEqual(variant_14.get('checks'), ['Pending'])


	def test_get_coverage_data_glioma(self):
		'''
		Check correct coverage values are pulled through for glioma panel

		'''
		panel_obj = Panel.objects.get(panel_name='Glioma', dna_or_rna='DNA')
		sample_obj = SampleAnalysis.objects.get(sample_id='dna_test_1',panel=panel_obj)

		coverage_data = get_coverage_data(sample_obj)

		H3F3A_coverage = coverage_data.get('H3F3A')
		IDH1_coverage = coverage_data.get('IDH1')
		TERT_coverage = coverage_data.get('TERT')
		EGFR_coverage = coverage_data.get('EGFR')
		BRAF_coverage = coverage_data.get('BRAF')
		IDH2_coverage = coverage_data.get('IDH2')
		CDKN2A_coverage = coverage_data.get('CDKN2A')
		PTEN_coverage = coverage_data.get('PTEN')
		TP53_coverage = coverage_data.get('TP53')
		ATRX_coverage = coverage_data.get('ATRX')

		# H3F3A overall coverage
		self.assertEqual(H3F3A_coverage.get('av_coverage'), 860)
		self.assertEqual(H3F3A_coverage.get('percent_270x'), 100)
		self.assertEqual(H3F3A_coverage.get('percent_135x'), 100)
		self.assertEqual(H3F3A_coverage.get('av_ntc_coverage'), 0)
		self.assertEqual(H3F3A_coverage.get('percent_ntc'), 0)

		# H3F3A regions
		H3F3A_regions = H3F3A_coverage.get('regions')

		H3F3A_region_0 = H3F3A_regions[0]
		self.assertEqual(H3F3A_region_0.get('hgvs_c'), 'H3F3A(NM_002107.4):c.82_84')
		self.assertEqual(H3F3A_region_0.get('average_coverage'), 851)
		self.assertEqual(H3F3A_region_0.get('hotspot_or_genescreen'), 'Hotspot')
		self.assertEqual(H3F3A_region_0.get('percent_135x'), 100)
		self.assertEqual(H3F3A_region_0.get('percent_270x'), 100)
		self.assertEqual(H3F3A_region_0.get('ntc_coverage'), 0)
		self.assertEqual(H3F3A_region_0.get('percent_ntc'), 0)

		H3F3A_region_1 = H3F3A_regions[1]
		self.assertEqual(H3F3A_region_1.get('hgvs_c'), 'H3F3A(NM_002107.4):c.103_105')
		self.assertEqual(H3F3A_region_1.get('average_coverage'), 870)
		self.assertEqual(H3F3A_region_1.get('hotspot_or_genescreen'), 'Hotspot')
		self.assertEqual(H3F3A_region_1.get('percent_135x'), 100)
		self.assertEqual(H3F3A_region_1.get('percent_270x'), 100)
		self.assertEqual(H3F3A_region_1.get('ntc_coverage'), 0)
		self.assertEqual(H3F3A_region_1.get('percent_ntc'), 0)

		# IGH1 overall
		self.assertEqual(IDH1_coverage.get('av_coverage'), 930)
		self.assertEqual(IDH1_coverage.get('percent_270x'), 100)
		self.assertEqual(IDH1_coverage.get('percent_135x'), 100)
		self.assertEqual(IDH1_coverage.get('av_ntc_coverage'), 0)
		self.assertEqual(IDH1_coverage.get('percent_ntc'), 0)

		# TERT overall
		self.assertEqual(TERT_coverage.get('av_coverage'), 274)
		self.assertEqual(TERT_coverage.get('percent_270x'), 50)
		self.assertEqual(TERT_coverage.get('percent_135x'), 100)
		self.assertEqual(TERT_coverage.get('av_ntc_coverage'), 0)
		self.assertEqual(TERT_coverage.get('percent_ntc'), 0)

		# BRAF overall
		self.assertEqual(BRAF_coverage.get('av_coverage'), 1158)
		self.assertEqual(BRAF_coverage.get('percent_270x'), 100)
		self.assertEqual(BRAF_coverage.get('percent_135x'), 100)
		self.assertEqual(BRAF_coverage.get('av_ntc_coverage'), 0)
		self.assertEqual(BRAF_coverage.get('percent_ntc'), 0)

		# IDH2 overall
		self.assertEqual(IDH2_coverage.get('av_coverage'), 1345)
		self.assertEqual(IDH2_coverage.get('percent_270x'), 100)
		self.assertEqual(IDH2_coverage.get('percent_135x'), 100)
		self.assertEqual(IDH2_coverage.get('av_ntc_coverage'), 0)
		self.assertEqual(IDH2_coverage.get('percent_ntc'), 0)

		# CDKN2A overall
		self.assertEqual(CDKN2A_coverage.get('av_coverage'), 664)
		self.assertEqual(CDKN2A_coverage.get('percent_270x'), 96)
		self.assertEqual(CDKN2A_coverage.get('percent_135x'), 100)
		self.assertEqual(CDKN2A_coverage.get('av_ntc_coverage'), 0)
		self.assertEqual(CDKN2A_coverage.get('percent_ntc'), 0)

		# PTEN overall
		self.assertEqual(PTEN_coverage.get('av_coverage'), 850)
		self.assertEqual(PTEN_coverage.get('percent_270x'), 100)
		self.assertEqual(PTEN_coverage.get('percent_135x'), 100)
		self.assertEqual(PTEN_coverage.get('av_ntc_coverage'), 0)
		self.assertEqual(PTEN_coverage.get('percent_ntc'), 0)

		# PTEN regions
		PTEN_regions = PTEN_coverage.get('regions')

		PTEN_region_0 = PTEN_regions[0]
		self.assertEqual(PTEN_region_0.get('hgvs_c'), 'PTEN(NM_000314.4):c.-6_79+5')
		self.assertEqual(PTEN_region_0.get('average_coverage'), 1393)
		self.assertEqual(PTEN_region_0.get('hotspot_or_genescreen'), 'Genescreen')
		self.assertEqual(PTEN_region_0.get('percent_135x'), 100)
		self.assertEqual(PTEN_region_0.get('percent_270x'), 100)
		self.assertEqual(PTEN_region_0.get('ntc_coverage'), 0)
		self.assertEqual(PTEN_region_0.get('percent_ntc'), 0)

		PTEN_region_4 = PTEN_regions[4]
		self.assertEqual(PTEN_region_4.get('hgvs_c'), 'PTEN(NM_000314.4):c.254-5_492+5')
		self.assertEqual(PTEN_region_4.get('average_coverage'), 932)
		self.assertEqual(PTEN_region_4.get('hotspot_or_genescreen'), 'Genescreen')
		self.assertEqual(PTEN_region_4.get('percent_135x'), 100)
		self.assertEqual(PTEN_region_4.get('percent_270x'), 100)
		self.assertEqual(PTEN_region_4.get('ntc_coverage'), 0)
		self.assertEqual(PTEN_region_4.get('percent_ntc'), 0)

		PTEN_region_8 = PTEN_regions[8]
		self.assertEqual(PTEN_region_8.get('hgvs_c'), 'PTEN(NM_000314.4):c.1027-5_*5')
		self.assertEqual(PTEN_region_8.get('average_coverage'), 515)
		self.assertEqual(PTEN_region_8.get('hotspot_or_genescreen'), 'Genescreen')
		self.assertEqual(PTEN_region_8.get('percent_135x'), 100)
		self.assertEqual(PTEN_region_8.get('percent_270x'), 100)
		self.assertEqual(PTEN_region_8.get('ntc_coverage'), 0)
		self.assertEqual(PTEN_region_8.get('percent_ntc'), 0)

		# TP53 overall
		self.assertEqual(TP53_coverage.get('av_coverage'), 1228)
		self.assertEqual(TP53_coverage.get('percent_270x'), 100)
		self.assertEqual(TP53_coverage.get('percent_135x'), 100)
		self.assertEqual(TP53_coverage.get('av_ntc_coverage'), 0)
		self.assertEqual(TP53_coverage.get('percent_ntc'), 0)

		# ATRX overall
		self.assertEqual(ATRX_coverage.get('av_coverage'), 631)
		self.assertEqual(ATRX_coverage.get('percent_270x'), 100)
		self.assertEqual(ATRX_coverage.get('percent_135x'), 100)
		self.assertEqual(ATRX_coverage.get('av_ntc_coverage'), 0)
		self.assertEqual(ATRX_coverage.get('percent_ntc'), 0)


	def test_get_coverage_data_melanoma(self):
		'''
		Check correct coverage values are pulled through for melanoma panel

		'''
		panel_obj = Panel.objects.get(panel_name='Melanoma', dna_or_rna='DNA')
		sample_obj = SampleAnalysis.objects.get(sample_id='dna_test_1',panel=panel_obj)
		coverage_data = get_coverage_data(sample_obj)

		NRAS_coverage = coverage_data.get('NRAS')
		KIT_coverage = coverage_data.get('KIT')
		BRAF_coverage = coverage_data.get('BRAF')

		# NRAS overall
		self.assertEqual(NRAS_coverage.get('av_coverage'), 1220)
		self.assertEqual(NRAS_coverage.get('percent_270x'), 100)
		self.assertEqual(NRAS_coverage.get('percent_135x'), 100)
		self.assertEqual(NRAS_coverage.get('av_ntc_coverage'), 0)
		self.assertEqual(NRAS_coverage.get('percent_ntc'), 0)

		# KIT overall
		self.assertEqual(KIT_coverage.get('av_coverage'), 1149)
		self.assertEqual(KIT_coverage.get('percent_270x'), 100)
		self.assertEqual(KIT_coverage.get('percent_135x'), 100)
		self.assertEqual(KIT_coverage.get('av_ntc_coverage'), 0)
		self.assertEqual(KIT_coverage.get('percent_ntc'), 0)

		# KIT regions
		KIT_regions = KIT_coverage.get('regions')

		KIT_region_2 = KIT_regions[2]
		self.assertEqual(KIT_region_2.get('hgvs_c'), 'KIT(NM_000222.2):c.1880-5_1990+5')
		self.assertEqual(KIT_region_2.get('average_coverage'), 1233)
		self.assertEqual(KIT_region_2.get('hotspot_or_genescreen'), 'Hotspot')
		self.assertEqual(KIT_region_2.get('percent_135x'), 100)
		self.assertEqual(KIT_region_2.get('percent_270x'), 100)
		self.assertEqual(KIT_region_2.get('ntc_coverage'), 0)
		self.assertEqual(KIT_region_2.get('percent_ntc'), 0)

		# BRAF overall
		self.assertEqual(BRAF_coverage.get('av_coverage'), 1219)
		self.assertEqual(BRAF_coverage.get('percent_270x'), 100)
		self.assertEqual(BRAF_coverage.get('percent_135x'), 100)
		self.assertEqual(BRAF_coverage.get('av_ntc_coverage'), 0)
		self.assertEqual(BRAF_coverage.get('percent_ntc'), 0)


	def test_get_coverage_data_gist(self):
		'''
		Check correct coverage values are pulled through for GIST panel
		
		'''
		panel_obj = Panel.objects.get(panel_name='GIST', dna_or_rna='DNA')
		sample_obj = SampleAnalysis.objects.get(sample_id='dna_test_1',panel=panel_obj)

		coverage_data = get_coverage_data(sample_obj)

		PDGFRA_coverage = coverage_data.get('PDGFRA')
		KIT_coverage = coverage_data.get('KIT')

		# PDGFRA overall
		self.assertEqual(PDGFRA_coverage.get('av_coverage'), 1387)
		self.assertEqual(PDGFRA_coverage.get('percent_270x'), 100)
		self.assertEqual(PDGFRA_coverage.get('percent_135x'), 100)
		self.assertEqual(PDGFRA_coverage.get('av_ntc_coverage'), 0)
		self.assertEqual(PDGFRA_coverage.get('percent_ntc'), 0)

		# KIT overall
		self.assertEqual(KIT_coverage.get('av_coverage'), 1149)
		self.assertEqual(KIT_coverage.get('percent_270x'), 100)
		self.assertEqual(KIT_coverage.get('percent_135x'), 100)
		self.assertEqual(KIT_coverage.get('av_ntc_coverage'), 0)
		self.assertEqual(KIT_coverage.get('percent_ntc'), 0)

		# KIT regions
		KIT_regions = KIT_coverage.get('regions')

		KIT_region_4 = KIT_regions[4]
		self.assertEqual(KIT_region_4.get('hgvs_c'), 'KIT(NM_000222.2):c.2362-5_2484+5')
		self.assertEqual(KIT_region_4.get('average_coverage'), 1023)
		self.assertEqual(KIT_region_4.get('hotspot_or_genescreen'), 'Hotspot')
		self.assertEqual(KIT_region_4.get('percent_135x'), 100)
		self.assertEqual(KIT_region_4.get('percent_270x'), 100)
		self.assertEqual(KIT_region_4.get('ntc_coverage'), 0)
		self.assertEqual(KIT_region_4.get('percent_ntc'), 0)


	def test_get_coverage_data_tumour(self):
		'''
		Check correct coverage values are pulled through for tumour panel
		
		'''
		panel_obj = Panel.objects.get(panel_name='Tumour', dna_or_rna='DNA')
		sample_obj = SampleAnalysis.objects.get(sample_id='dna_test_1',panel=panel_obj)

		coverage_data = get_coverage_data(sample_obj)
 
		AR_coverage = coverage_data.get('AR')
		KIT_coverage = coverage_data.get('KIT')
		ATRX_coverage = coverage_data.get('ATRX')
		ARID1A_coverage = coverage_data.get('ARID1A')
		NRAS_coverage = coverage_data.get('NRAS')
		BRCA2_coverage = coverage_data.get('BRCA2')
		IDH2_coverage = coverage_data.get('IDH2')
		TP53_coverage = coverage_data.get('TP53')
		ERBB2_coverage = coverage_data.get('ERBB2')
		BRCA1_coverage = coverage_data.get('BRCA1')

		# AR overall
		self.assertEqual(AR_coverage.get('av_coverage'), 1021)
		self.assertEqual(AR_coverage.get('percent_270x'), 98)
		self.assertEqual(AR_coverage.get('percent_135x'), 99)
		self.assertEqual(AR_coverage.get('av_ntc_coverage'), 0)
		self.assertEqual(AR_coverage.get('percent_ntc'), 0)

		# ATRX overall
		self.assertEqual(ATRX_coverage.get('av_coverage'), 631)
		self.assertEqual(ATRX_coverage.get('percent_270x'), 100)
		self.assertEqual(ATRX_coverage.get('percent_135x'), 100)
		self.assertEqual(ATRX_coverage.get('av_ntc_coverage'), 0)
		self.assertEqual(ATRX_coverage.get('percent_ntc'), 0)

		# ARID1A overall
		self.assertEqual(ARID1A_coverage.get('av_coverage'), 1202)
		self.assertEqual(ARID1A_coverage.get('percent_270x'), 91)
		self.assertEqual(ARID1A_coverage.get('percent_135x'), 96)
		self.assertEqual(ARID1A_coverage.get('av_ntc_coverage'), 0)
		self.assertEqual(ARID1A_coverage.get('percent_ntc'), 0)

		# NRAS overall
		self.assertEqual(NRAS_coverage.get('av_coverage'), 1220)
		self.assertEqual(NRAS_coverage.get('percent_270x'), 100)
		self.assertEqual(NRAS_coverage.get('percent_135x'), 100)
		self.assertEqual(NRAS_coverage.get('av_ntc_coverage'), 0)
		self.assertEqual(NRAS_coverage.get('percent_ntc'), 0)

		# NRAS regions
		NRAS_regions = NRAS_coverage.get('regions')

		NRAS_region_3 = NRAS_regions[3]
		self.assertEqual(NRAS_region_3.get('hgvs_c'), 'NRAS(NM_002524.3):c.175_177')
		self.assertEqual(NRAS_region_3.get('average_coverage'), 1000)
		self.assertEqual(NRAS_region_3.get('hotspot_or_genescreen'), 'Hotspot')
		self.assertEqual(NRAS_region_3.get('percent_135x'), 100)
		self.assertEqual(NRAS_region_3.get('percent_270x'), 100)
		self.assertEqual(NRAS_region_3.get('ntc_coverage'), 0)
		self.assertEqual(NRAS_region_3.get('percent_ntc'), 0)

		# BRCA2 overall
		self.assertEqual(BRCA2_coverage.get('av_coverage'), 901)
		self.assertEqual(BRCA2_coverage.get('percent_270x'), 100)
		self.assertEqual(BRCA2_coverage.get('percent_135x'), 100)
		self.assertEqual(BRCA2_coverage.get('av_ntc_coverage'), 0)
		self.assertEqual(BRCA2_coverage.get('percent_ntc'), 0)

		# IDH2 overall
		self.assertEqual(IDH2_coverage.get('av_coverage'), 1345)
		self.assertEqual(IDH2_coverage.get('percent_270x'), 100)
		self.assertEqual(IDH2_coverage.get('percent_135x'), 100)
		self.assertEqual(IDH2_coverage.get('av_ntc_coverage'), 0)
		self.assertEqual(IDH2_coverage.get('percent_ntc'), 0)

		# TP53 overall
		self.assertEqual(TP53_coverage.get('av_coverage'), 1228)
		self.assertEqual(TP53_coverage.get('percent_270x'), 100)
		self.assertEqual(TP53_coverage.get('percent_135x'), 100)
		self.assertEqual(TP53_coverage.get('av_ntc_coverage'), 0)
		self.assertEqual(TP53_coverage.get('percent_ntc'), 0)

		# ERBB2 overall
		self.assertEqual(ERBB2_coverage.get('av_coverage'), 1586)
		self.assertEqual(ERBB2_coverage.get('percent_270x'), 100)
		self.assertEqual(ERBB2_coverage.get('percent_135x'), 100)
		self.assertEqual(ERBB2_coverage.get('av_ntc_coverage'), 0)
		self.assertEqual(ERBB2_coverage.get('percent_ntc'), 0)

		# BRCA1 overall
		self.assertEqual(BRCA1_coverage.get('av_coverage'), 1384)
		self.assertEqual(BRCA1_coverage.get('percent_270x'), 100)
		self.assertEqual(BRCA1_coverage.get('percent_135x'), 100)
		self.assertEqual(BRCA1_coverage.get('av_ntc_coverage'), 0)
		self.assertEqual(BRCA1_coverage.get('percent_ntc'), 0)


	def test_get_coverage_data_colorectal(self):
		'''
		Check correct coverage values are pulled through for colorectal panel
		
		'''
		panel_obj = Panel.objects.get(panel_name='Colorectal', dna_or_rna='DNA')
		sample_obj = SampleAnalysis.objects.get(sample_id='dna_test_1',panel=panel_obj)

		coverage_data = get_coverage_data(sample_obj)

		NRAS_coverage = coverage_data.get('NRAS')
		PIK3CA_coverage = coverage_data.get('PIK3CA')
		EGFR_coverage = coverage_data.get('EGFR')
		BRAF_coverage = coverage_data.get('BRAF')
		KRAS_coverage = coverage_data.get('KRAS')
		PTEN_coverage = coverage_data.get('PTEN')
		TP53_coverage = coverage_data.get('TP53')

		# NRAS overall
		self.assertEqual(NRAS_coverage.get('av_coverage'), 1220)
		self.assertEqual(NRAS_coverage.get('percent_270x'), 100)
		self.assertEqual(NRAS_coverage.get('percent_135x'), 100)
		self.assertEqual(NRAS_coverage.get('av_ntc_coverage'), 0)
		self.assertEqual(NRAS_coverage.get('percent_ntc'), 0)

		# PIK3CA overall
		self.assertEqual(PIK3CA_coverage.get('av_coverage'), 1127)
		self.assertEqual(PIK3CA_coverage.get('percent_270x'), 100)
		self.assertEqual(PIK3CA_coverage.get('percent_135x'), 100)
		self.assertEqual(PIK3CA_coverage.get('av_ntc_coverage'), 0)
		self.assertEqual(PIK3CA_coverage.get('percent_ntc'), 0)

		# EGFR overall
		self.assertEqual(EGFR_coverage.get('av_coverage'), 1692)
		self.assertEqual(EGFR_coverage.get('percent_270x'), 100)
		self.assertEqual(EGFR_coverage.get('percent_135x'), 100)
		self.assertEqual(EGFR_coverage.get('av_ntc_coverage'), 0)
		self.assertEqual(EGFR_coverage.get('percent_ntc'), 0)

		# BRAF overall
		self.assertEqual(BRAF_coverage.get('av_coverage'), 1219)
		self.assertEqual(BRAF_coverage.get('percent_270x'), 100)
		self.assertEqual(BRAF_coverage.get('percent_135x'), 100)
		self.assertEqual(BRAF_coverage.get('av_ntc_coverage'), 0)
		self.assertEqual(BRAF_coverage.get('percent_ntc'), 0)

		# BRAF regions
		BRAF_regions = BRAF_coverage.get('regions')

		BRAF_region_1 = BRAF_regions[1]
		self.assertEqual(BRAF_region_1.get('hgvs_c'), 'BRAF(NM_004333.4):c.1315-5_1432+5')
		self.assertEqual(BRAF_region_1.get('average_coverage'), 1280)
		self.assertEqual(BRAF_region_1.get('hotspot_or_genescreen'), 'Hotspot')
		self.assertEqual(BRAF_region_1.get('percent_135x'), 100)
		self.assertEqual(BRAF_region_1.get('percent_270x'), 100)
		self.assertEqual(BRAF_region_1.get('ntc_coverage'), 0)
		self.assertEqual(BRAF_region_1.get('percent_ntc'), 0)

		# KRAS overall
		self.assertEqual(KRAS_coverage.get('av_coverage'), 1102)
		self.assertEqual(KRAS_coverage.get('percent_270x'), 100)
		self.assertEqual(KRAS_coverage.get('percent_135x'), 100)
		self.assertEqual(KRAS_coverage.get('av_ntc_coverage'), 0)
		self.assertEqual(KRAS_coverage.get('percent_ntc'), 0)

		# PTEN overall
		self.assertEqual(PTEN_coverage.get('av_coverage'), 850)
		self.assertEqual(PTEN_coverage.get('percent_270x'), 100)
		self.assertEqual(PTEN_coverage.get('percent_135x'), 100)
		self.assertEqual(PTEN_coverage.get('av_ntc_coverage'), 0)
		self.assertEqual(PTEN_coverage.get('percent_ntc'), 0)

		# TP53 overall
		self.assertEqual(TP53_coverage.get('av_coverage'), 1228)
		self.assertEqual(TP53_coverage.get('percent_270x'), 100)
		self.assertEqual(TP53_coverage.get('percent_135x'), 100)
		self.assertEqual(TP53_coverage.get('av_ntc_coverage'), 0)
		self.assertEqual(TP53_coverage.get('percent_ntc'), 0)


	def test_get_coverage_data_thyroid(self):
		'''
		Check correct coverage values are pulled through for thyroid panel
		
		'''
		panel_obj = Panel.objects.get(panel_name='Thyroid', dna_or_rna='DNA')
		sample_obj = SampleAnalysis.objects.get(sample_id='dna_test_1',panel=panel_obj)

		coverage_data = get_coverage_data(sample_obj)

		NRAS_coverage = coverage_data.get('NRAS')
		HRAS_coverage = coverage_data.get('HRAS')
		KRAS_coverage = coverage_data.get('KRAS')
		BRAF_coverage = coverage_data.get('BRAF')
		TP53_coverage = coverage_data.get('TP53')
		RET_coverage = coverage_data.get('RET')

		# NRAS overall
		self.assertEqual(NRAS_coverage.get('av_coverage'), 1220)
		self.assertEqual(NRAS_coverage.get('percent_270x'), 100)
		self.assertEqual(NRAS_coverage.get('percent_135x'), 100)
		self.assertEqual(NRAS_coverage.get('av_ntc_coverage'), 0)
		self.assertEqual(NRAS_coverage.get('percent_ntc'), 0)

		# HRAS overall
		self.assertEqual(HRAS_coverage.get('av_coverage'), 1337)
		self.assertEqual(HRAS_coverage.get('percent_270x'), 100)
		self.assertEqual(HRAS_coverage.get('percent_135x'), 100)
		self.assertEqual(HRAS_coverage.get('av_ntc_coverage'), 0)
		self.assertEqual(HRAS_coverage.get('percent_ntc'), 0)

		# KRAS overall
		self.assertEqual(KRAS_coverage.get('av_coverage'), 1102)
		self.assertEqual(KRAS_coverage.get('percent_270x'), 100)
		self.assertEqual(KRAS_coverage.get('percent_135x'), 100)
		self.assertEqual(KRAS_coverage.get('av_ntc_coverage'), 0)
		self.assertEqual(KRAS_coverage.get('percent_ntc'), 0)

		# BRAF overall
		self.assertEqual(BRAF_coverage.get('av_coverage'), 1280)
		self.assertEqual(BRAF_coverage.get('percent_270x'), 100)
		self.assertEqual(BRAF_coverage.get('percent_135x'), 100)
		self.assertEqual(BRAF_coverage.get('av_ntc_coverage'), 0)
		self.assertEqual(BRAF_coverage.get('percent_ntc'), 0)

		# TP53 overall
		self.assertEqual(TP53_coverage.get('av_coverage'), 1228)
		self.assertEqual(TP53_coverage.get('percent_270x'), 100)
		self.assertEqual(TP53_coverage.get('percent_135x'), 100)
		self.assertEqual(TP53_coverage.get('av_ntc_coverage'), 0)
		self.assertEqual(TP53_coverage.get('percent_ntc'), 0)

		# TP53 regions
		TP53_regions = TP53_coverage.get('regions')

		TP53_region_5 = TP53_regions[5]
		self.assertEqual(TP53_region_5.get('hgvs_c'), 'TP53(NM_000546.4):c.673-5_782+5')
		self.assertEqual(TP53_region_5.get('average_coverage'), 1140)
		self.assertEqual(TP53_region_5.get('hotspot_or_genescreen'), 'Genescreen')
		self.assertEqual(TP53_region_5.get('percent_135x'), 100)
		self.assertEqual(TP53_region_5.get('percent_270x'), 100)
		self.assertEqual(TP53_region_5.get('ntc_coverage'), 0)
		self.assertEqual(TP53_region_5.get('percent_ntc'), 0)

		# RET overall
		self.assertEqual(RET_coverage.get('av_coverage'), 1569)
		self.assertEqual(RET_coverage.get('percent_270x'), 100)
		self.assertEqual(RET_coverage.get('percent_135x'), 100)
		self.assertEqual(RET_coverage.get('av_ntc_coverage'), 0)
		self.assertEqual(RET_coverage.get('percent_ntc'), 0)


	def test_get_coverage_data_lung(self):
		'''
		Check correct coverage values are pulled through for lung panel
		
		'''
		panel_obj = Panel.objects.get(panel_name='Lung', dna_or_rna='DNA')
		sample_obj = SampleAnalysis.objects.get(sample_id='dna_test_1',panel=panel_obj)

		coverage_data = get_coverage_data(sample_obj)

		EGFR_coverage = coverage_data.get('EGFR')
		BRAF_coverage = coverage_data.get('BRAF')
		KRAS_coverage = coverage_data.get('KRAS')

		# EGFR overall
		self.assertEqual(EGFR_coverage.get('av_coverage'), 1692)
		self.assertEqual(EGFR_coverage.get('percent_270x'), 100)
		self.assertEqual(EGFR_coverage.get('percent_135x'), 100)
		self.assertEqual(EGFR_coverage.get('av_ntc_coverage'), 0)
		self.assertEqual(EGFR_coverage.get('percent_ntc'), 0)

		# EGFR regions
		EGFR_regions = EGFR_coverage.get('regions')

		EGFR_region_3 = EGFR_regions[3]
		self.assertEqual(EGFR_region_3.get('hgvs_c'), 'EGFR(NM_005228.3):c.2470-5_2625+5')
		self.assertEqual(EGFR_region_3.get('average_coverage'), 1683)
		self.assertEqual(EGFR_region_3.get('hotspot_or_genescreen'), 'Hotspot')
		self.assertEqual(EGFR_region_3.get('percent_135x'), 100)
		self.assertEqual(EGFR_region_3.get('percent_270x'), 100)
		self.assertEqual(EGFR_region_3.get('ntc_coverage'), 0)
		self.assertEqual(EGFR_region_3.get('percent_ntc'), 0)

		# BRAF overall
		self.assertEqual(BRAF_coverage.get('av_coverage'), 1219)
		self.assertEqual(BRAF_coverage.get('percent_270x'), 100)
		self.assertEqual(BRAF_coverage.get('percent_135x'), 100)
		self.assertEqual(BRAF_coverage.get('av_ntc_coverage'), 0)
		self.assertEqual(BRAF_coverage.get('percent_ntc'), 0)

		# KRAS overall
		self.assertEqual(KRAS_coverage.get('av_coverage'), 1102)
		self.assertEqual(KRAS_coverage.get('percent_270x'), 100)
		self.assertEqual(KRAS_coverage.get('percent_135x'), 100)
		self.assertEqual(KRAS_coverage.get('av_ntc_coverage'), 0)
		self.assertEqual(KRAS_coverage.get('percent_ntc'), 0)


class TestNTCCalls(TestCase):
	"""
	Load in DNA control sample with NTC contamination spiked in, test that 
	NTC variants are called correctly and at correct VAFs

	"""

	# load in test data
	fixtures = ['dna_test_1.json']

	# dictionary of expected data for comparison later on
	model_data = {
		'7:55241707G>A': {
			'in_ntc': True,
			'ntc_total': 1,
			'ntc_alt': 1,
			'ntc_vaf': Decimal('100.00'),
		},
		'7:55242464AGGAATTAAGAGAAGC>A': {
			'in_ntc': False,
			'ntc_total': None,
			'ntc_alt': None,
			'ntc_vaf': None,
		},
		'7:55248998A>ATGGCCAGCG': {
			'in_ntc': False,
			'ntc_total': None,
			'ntc_alt': None,
			'ntc_vaf': None,
		},
		'7:55249063G>A': {
			'in_ntc': False,
			'ntc_total': None,
			'ntc_alt': None,
			'ntc_vaf': None,
		},
		'7:140453136A>T': {
			'in_ntc': True,
			'ntc_total': 4,
			'ntc_alt': 1,
			'ntc_vaf': Decimal('25.00'),
		},
		'12:25398281C>T': {
			'in_ntc': True,
			'ntc_total': 1015,
			'ntc_alt': 281,
			'ntc_vaf': Decimal('27.68'),
		},
	}

	def test_ntc_calls(self):
		'''
		Check a subset of variant calls with fake NTC contamination

		'''
		# load sample objects
		panel_obj = Panel.objects.get(panel_name='Lung', dna_or_rna='DNA')

		sample = SampleAnalysis.objects.get(sample_id='dna_test_2', panel=panel_obj)
		sample_data = get_sample_info(sample)

		variant_calls = get_variant_info(sample_data, sample)['variant_calls']

		# loop through each call and compare to expected answer dict
		for v in variant_calls:
			model_answers = self.model_data[ v['genomic'] ]

			self.assertEqual(v['this_run']['ntc'], model_answers['in_ntc'])
			self.assertEqual(v['this_run']['alt_count_ntc'], model_answers['ntc_alt'])
			self.assertEqual(v['this_run']['total_count_ntc'], model_answers['ntc_total'])
			self.assertEqual(v['this_run']['vaf_ntc'], model_answers['ntc_vaf'])


class TestRna(TestCase):

	# test data
	fixtures = ['rna_test_1.json']


	def test_get_samples(self):
		'''
		Pull correct sample info from worksheet

		'''
		samples = SampleAnalysis.objects.filter(worksheet = 'rna_ws_1')
		samples_dict = get_samples(samples)

		self.assertEqual(list(samples_dict.keys()), ['rna_test_1'])

		sample = samples_dict.get('rna_test_1')
		self.assertEqual(sample.get('dna_rna'), 'RNA')


	def test_get_sample_info_rna_tumour(self):
		'''
		Check sample info for tumour panel

		'''
		panel_obj = Panel.objects.get(panel_name='Tumour', dna_or_rna='RNA')
		sample_obj = SampleAnalysis.objects.get(sample_id='rna_test_1', panel=panel_obj)

		sample_info = get_sample_info(sample_obj)

		self.assertEqual(sample_info.get('dna_or_rna'), 'RNA')
		self.assertEqual(sample_info.get('sample_id'), 'rna_test_1')
		self.assertEqual(sample_info.get('worksheet_id'), 'rna_ws_1')
		self.assertEqual(sample_info.get('panel'), 'Tumour')
		self.assertEqual(sample_info.get('run_id'), 'run_1')
		self.assertEqual(sample_info.get('total_reads'), 9000004)
		self.assertEqual(sample_info.get('total_reads_ntc'), 596)
		self.assertEqual((sample_info.get('checks')).get('current_status'), 'IGV check 1')
		self.assertEqual((sample_info.get('checks')).get('assigned_to'), None)

		
	def test_get_sample_info_rna_glioma(self):
		'''
		Check sample info for glioma panel 

		'''
		panel_obj = Panel.objects.get(panel_name='Glioma', dna_or_rna='RNA')
		sample_obj = SampleAnalysis.objects.get(sample_id='rna_test_1', panel=panel_obj)

		sample_info = get_sample_info(sample_obj)
		
		self.assertEqual(sample_info.get('dna_or_rna'), 'RNA')
		self.assertEqual(sample_info.get('sample_id'), 'rna_test_1')
		self.assertEqual(sample_info.get('worksheet_id'), 'rna_ws_1')
		self.assertEqual(sample_info.get('panel'), 'Glioma')
		self.assertEqual(sample_info.get('run_id'), 'run_1')
		self.assertEqual(sample_info.get('total_reads'), 23875300)
		self.assertEqual(sample_info.get('total_reads_ntc'), 6170)
		self.assertEqual((sample_info.get('checks')).get('current_status'), 'IGV check 1')
		self.assertEqual((sample_info.get('checks')).get('assigned_to'), None)


	def test_get_sample_info_rna_gist(self):
		'''
		Check sample info for gist panel

		'''
		panel_obj = Panel.objects.get(panel_name='GIST', dna_or_rna='RNA')
		sample_obj = SampleAnalysis.objects.get(sample_id='rna_test_1', panel=panel_obj)

		sample_info = get_sample_info(sample_obj)

		self.assertEqual(sample_info.get('dna_or_rna'), 'RNA')
		self.assertEqual(sample_info.get('sample_id'), 'rna_test_1')
		self.assertEqual(sample_info.get('worksheet_id'), 'rna_ws_1')
		self.assertEqual(sample_info.get('panel'), 'GIST')
		self.assertEqual(sample_info.get('run_id'), 'run_1')
		self.assertEqual(sample_info.get('total_reads'), 69576959)
		self.assertEqual(sample_info.get('total_reads_ntc'), 765)
		self.assertEqual((sample_info.get('checks')).get('current_status'), 'IGV check 1')
		self.assertEqual((sample_info.get('checks')).get('assigned_to'), None)


	def test_get_sample_info_rna_melanoma(self):
		'''
		Check sample info for melanoma panel

		'''
		panel_obj = Panel.objects.get(panel_name='Melanoma', dna_or_rna='RNA')
		sample_obj = SampleAnalysis.objects.get(sample_id='rna_test_1', panel=panel_obj)

		sample_info = get_sample_info(sample_obj)
		
		self.assertEqual(sample_info.get('dna_or_rna'), 'RNA')
		self.assertEqual(sample_info.get('sample_id'), 'rna_test_1')
		self.assertEqual(sample_info.get('worksheet_id'), 'rna_ws_1')
		self.assertEqual(sample_info.get('panel'), 'Melanoma')
		self.assertEqual(sample_info.get('run_id'), 'run_1')
		self.assertEqual(sample_info.get('total_reads'), 34444)
		self.assertEqual(sample_info.get('total_reads_ntc'), 6170)
		self.assertEqual((sample_info.get('checks')).get('current_status'), 'IGV check 1')
		self.assertEqual((sample_info.get('checks')).get('assigned_to'), None)


	def test_get_sample_info_rna_lung(self):
		'''
		Check sample info for lung panel

		'''
		panel_obj = Panel.objects.get(panel_name='Lung', dna_or_rna='RNA')
		sample_obj = SampleAnalysis.objects.get(sample_id='rna_test_1', panel=panel_obj)

		sample_info = get_sample_info(sample_obj)

		self.assertEqual(sample_info.get('dna_or_rna'), 'RNA')
		self.assertEqual(sample_info.get('sample_id'), 'rna_test_1')
		self.assertEqual(sample_info.get('worksheet_id'), 'rna_ws_1')
		self.assertEqual(sample_info.get('panel'), 'Lung')
		self.assertEqual(sample_info.get('run_id'), 'run_1')
		self.assertEqual(sample_info.get('total_reads'), 8795879)
		self.assertEqual(sample_info.get('total_reads_ntc'), 34)
		self.assertEqual((sample_info.get('checks')).get('current_status'), 'IGV check 1')
		self.assertEqual((sample_info.get('checks')).get('assigned_to'), None)


	def test_get_sample_info_rna_thyroid(self):
		'''
		Check sample info for thyroid panel

		'''
		panel_obj = Panel.objects.get(panel_name='Thyroid', dna_or_rna='RNA')
		sample_obj = SampleAnalysis.objects.get(sample_id='rna_test_1', panel=panel_obj)

		sample_info = get_sample_info(sample_obj)

		self.assertEqual(sample_info.get('dna_or_rna'), 'RNA')
		self.assertEqual(sample_info.get('sample_id'), 'rna_test_1')
		self.assertEqual(sample_info.get('worksheet_id'), 'rna_ws_1')
		self.assertEqual(sample_info.get('panel'), 'Thyroid')
		self.assertEqual(sample_info.get('run_id'), 'run_1')
		self.assertEqual(sample_info.get('total_reads'), 6000)
		self.assertEqual(sample_info.get('total_reads_ntc'), 170)
		self.assertEqual((sample_info.get('checks')).get('current_status'), 'IGV check 1')
		self.assertEqual((sample_info.get('checks')).get('assigned_to'), None)


	def test_get_sample_info_rna_ntrk(self):
		'''
		Check sample info for ntrk panel

		'''
		panel_obj = Panel.objects.get(panel_name='NTRK', dna_or_rna='RNA')
		sample_obj = SampleAnalysis.objects.get(sample_id='rna_test_1', panel=panel_obj)

		sample_info = get_sample_info(sample_obj)

		self.assertEqual(sample_info.get('dna_or_rna'), 'RNA')
		self.assertEqual(sample_info.get('sample_id'), 'rna_test_1')
		self.assertEqual(sample_info.get('worksheet_id'), 'rna_ws_1')
		self.assertEqual(sample_info.get('panel'), 'NTRK')
		self.assertEqual(sample_info.get('run_id'), 'run_1')
		self.assertEqual(sample_info.get('total_reads'), 1070560)
		self.assertEqual(sample_info.get('total_reads_ntc'), 14)
		self.assertEqual((sample_info.get('checks')).get('current_status'), 'IGV check 1')
		self.assertEqual((sample_info.get('checks')).get('assigned_to'), None)


	def test_get_sample_info_rna_colorectal(self):
		'''
		Check sample info for colorectal panel

		'''
		panel_obj = Panel.objects.get(panel_name='Colorectal', dna_or_rna='RNA')
		sample_obj = SampleAnalysis.objects.get(sample_id='rna_test_1', panel=panel_obj)

		sample_info = get_sample_info(sample_obj)

		self.assertEqual(sample_info.get('dna_or_rna'), 'RNA')
		self.assertEqual(sample_info.get('sample_id'), 'rna_test_1')
		self.assertEqual(sample_info.get('worksheet_id'), 'rna_ws_1')
		self.assertEqual(sample_info.get('panel'), 'Colorectal')
		self.assertEqual(sample_info.get('run_id'), 'run_1')
		self.assertEqual(sample_info.get('total_reads'), 67794769)
		self.assertEqual(sample_info.get('total_reads_ntc'), 49674)
		self.assertEqual((sample_info.get('checks')).get('current_status'), 'IGV check 1')
		self.assertEqual((sample_info.get('checks')).get('assigned_to'), None)


	def test_get_fusion_info_tumour(self):
		'''
		Check correct calls are present in tumour panel

		'''
		panel_obj = Panel.objects.get(panel_name='Tumour', dna_or_rna='RNA')
		sample_obj = SampleAnalysis.objects.get(sample_id='rna_test_1',panel=panel_obj)

		sample_data = get_sample_info(sample_obj)
		fusion_data = get_fusion_info(sample_data, sample_obj)
		fusion_calls = fusion_data.get('fusion_calls')

		fusion_0 = fusion_calls[0]
		self.assertEqual(fusion_0.get('fusion_genes'), 'TPM3-NTRK1')
		self.assertEqual(fusion_0.get('left_breakpoint'), 'chr1:154142876')
		self.assertEqual(fusion_0.get('right_breakpoint'), 'chr1:156844361')

		fusion_1 = fusion_calls[1]
		self.assertEqual(fusion_1.get('fusion_genes'), 'LMNA-NTRK1')
		self.assertEqual(fusion_1.get('left_breakpoint'), 'chr1:156100562')
		self.assertEqual(fusion_1.get('right_breakpoint'), 'chr1:156844696')

		fusion_2 = fusion_calls[2]
		self.assertEqual(fusion_2.get('fusion_genes'), 'SLC45A3-BRAF')
		self.assertEqual(fusion_2.get('left_breakpoint'), 'chr1:205649521')
		self.assertEqual(fusion_2.get('right_breakpoint'), 'chr7:140494266')

		fusion_3 = fusion_calls[3]
		self.assertEqual(fusion_3.get('fusion_genes'), 'EML4-ALK')
		self.assertEqual(fusion_3.get('left_breakpoint'), 'chr2:42522654')
		self.assertEqual(fusion_3.get('right_breakpoint'), 'chr2:29446394')

		fusion_4 = fusion_calls[4]
		self.assertEqual(fusion_4.get('fusion_genes'), 'TFG-NTRK1')
		self.assertEqual(fusion_4.get('left_breakpoint'), 'chr3:100451513')
		self.assertEqual(fusion_4.get('right_breakpoint'), 'chr1:156844360')

		fusion_5 = fusion_calls[5]
		self.assertEqual(fusion_5.get('fusion_genes'), 'SLC34A2-ROS1;GOPC')
		self.assertEqual(fusion_5.get('left_breakpoint'), 'chr4:25665950')
		self.assertEqual(fusion_5.get('right_breakpoint'), 'chr6:117645578')

		fusion_6 = fusion_calls[6]
		self.assertEqual(fusion_6.get('fusion_genes'), 'CD74-ROS1;GOPC')
		self.assertEqual(fusion_6.get('left_breakpoint'), 'chr5:149784243')
		self.assertEqual(fusion_6.get('right_breakpoint'), 'chr6:117645578')

		fusion_7 = fusion_calls[7]
		self.assertEqual(fusion_7.get('fusion_genes'), 'KIF5B-RET')
		self.assertEqual(fusion_7.get('left_breakpoint'), 'chr10:32306071')
		self.assertEqual(fusion_7.get('right_breakpoint'), 'chr10:43609927')

		fusion_8 = fusion_calls[8]
		self.assertEqual(fusion_8.get('fusion_genes'), 'NCOA4-RET')
		self.assertEqual(fusion_8.get('left_breakpoint'), 'chr10:51582937')
		self.assertEqual(fusion_8.get('right_breakpoint'), 'chr10:43612030')

		fusion_9 = fusion_calls[9]
		self.assertEqual(fusion_9.get('fusion_genes'), 'CCDC6-RET')
		self.assertEqual(fusion_9.get('left_breakpoint'), 'chr10:61665879')
		self.assertEqual(fusion_9.get('right_breakpoint'), 'chr10:43612032')

		fusion_10 = fusion_calls[10]
		self.assertEqual(fusion_10.get('fusion_genes'), 'ETV6-NTRK3')
		self.assertEqual(fusion_10.get('left_breakpoint'), 'chr12:12022900')
		self.assertEqual(fusion_10.get('right_breakpoint'), 'chr15:88483984')

		fusion_11 = fusion_calls[11]
		self.assertEqual(fusion_11.get('fusion_genes'), 'EGFR 2-7/28')
		self.assertEqual(fusion_11.get('left_breakpoint'), 'chr7:55087058')
		self.assertEqual(fusion_11.get('right_breakpoint'), 'chr7:55223522')

		fusion_12 = fusion_calls[12]
		self.assertEqual(fusion_12.get('fusion_genes'), 'MET 14/21')
		self.assertEqual(fusion_12.get('left_breakpoint'), 'chr7:116411708')
		self.assertEqual(fusion_12.get('right_breakpoint'), 'chr7:116414934')


	def test_get_fusion_info_glioma(self):
		'''
		Check correct calls are present in glioma panel

		'''
		panel_obj = Panel.objects.get(panel_name='Glioma', dna_or_rna='RNA')
		sample_obj = SampleAnalysis.objects.get(sample_id='rna_test_1',panel=panel_obj)

		sample_data = get_sample_info(sample_obj)
		fusion_data = get_fusion_info(sample_data, sample_obj)
		fusion_calls = fusion_data.get('fusion_calls')

		fusion_0 = fusion_calls[0]
		self.assertEqual(fusion_0.get('fusion_genes'), 'TPM3-NTRK1')
		self.assertEqual(fusion_0.get('left_breakpoint'), 'chr1:154142876')
		self.assertEqual(fusion_0.get('right_breakpoint'), 'chr1:156844361')

		fusion_1 = fusion_calls[1]
		self.assertEqual(fusion_1.get('fusion_genes'), 'LMNA-NTRK1')
		self.assertEqual(fusion_1.get('left_breakpoint'), 'chr1:156100562')
		self.assertEqual(fusion_1.get('right_breakpoint'), 'chr1:156844696')

		fusion_2 = fusion_calls[2]
		self.assertEqual(fusion_2.get('fusion_genes'), 'SLC45A3-BRAF')
		self.assertEqual(fusion_2.get('left_breakpoint'), 'chr1:205649521')
		self.assertEqual(fusion_2.get('right_breakpoint'), 'chr7:140494266')

		fusion_3 = fusion_calls[3]
		self.assertEqual(fusion_3.get('fusion_genes'), 'TFG-NTRK1')
		self.assertEqual(fusion_3.get('left_breakpoint'), 'chr3:100451513')
		self.assertEqual(fusion_3.get('right_breakpoint'), 'chr1:156844360')

		fusion_4 = fusion_calls[4]
		self.assertEqual(fusion_4.get('fusion_genes'), 'ETV6-NTRK3')
		self.assertEqual(fusion_4.get('left_breakpoint'), 'chr12:12022900')
		self.assertEqual(fusion_4.get('right_breakpoint'), 'chr15:88483984')

		fusion_5 = fusion_calls[5]
		self.assertEqual(fusion_5.get('fusion_genes'), 'EGFR 2-7/28')
		self.assertEqual(fusion_5.get('left_breakpoint'), 'chr7:55087058')
		self.assertEqual(fusion_5.get('right_breakpoint'), 'chr7:55223522')


	def test_get_fusion_info_melanoma(self):
		'''
		Check correct calls are present in melanoma panel

		'''
		panel_obj = Panel.objects.get(panel_name='Melanoma', dna_or_rna='RNA')
		sample_obj = SampleAnalysis.objects.get(sample_id='rna_test_1',panel=panel_obj)

		sample_data = get_sample_info(sample_obj)
		fusion_data = get_fusion_info(sample_data, sample_obj)
		fusion_calls = fusion_data.get('fusion_calls')

		fusion_0 = fusion_calls[0]
		self.assertEqual(fusion_0.get('fusion_genes'), 'TPM3-NTRK1')
		self.assertEqual(fusion_0.get('left_breakpoint'), 'chr1:154142876')
		self.assertEqual(fusion_0.get('right_breakpoint'), 'chr1:156844361')

		fusion_1 = fusion_calls[1]
		self.assertEqual(fusion_1.get('fusion_genes'), 'LMNA-NTRK1')
		self.assertEqual(fusion_1.get('left_breakpoint'), 'chr1:156100562')
		self.assertEqual(fusion_1.get('right_breakpoint'), 'chr1:156844696')

		fusion_2 = fusion_calls[2]
		self.assertEqual(fusion_2.get('fusion_genes'), 'TFG-NTRK1')
		self.assertEqual(fusion_2.get('left_breakpoint'), 'chr3:100451513')
		self.assertEqual(fusion_2.get('right_breakpoint'), 'chr1:156844360')

		fusion_3 = fusion_calls[3]
		self.assertEqual(fusion_3.get('fusion_genes'), 'ETV6-NTRK3')
		self.assertEqual(fusion_3.get('left_breakpoint'), 'chr12:12022900')
		self.assertEqual(fusion_3.get('right_breakpoint'), 'chr15:88483984')


	def test_get_fusion_info_ntrk(self):
		'''
		Check correct calls are present in ntrk panel

		'''
		panel_obj = Panel.objects.get(panel_name='NTRK', dna_or_rna='RNA')
		sample_obj = SampleAnalysis.objects.get(sample_id='rna_test_1',panel=panel_obj)

		sample_data = get_sample_info(sample_obj)
		fusion_data = get_fusion_info(sample_data, sample_obj)
		fusion_calls = fusion_data.get('fusion_calls')

		fusion_0 = fusion_calls[0]
		self.assertEqual(fusion_0.get('fusion_genes'), 'TPM3-NTRK1')
		self.assertEqual(fusion_0.get('left_breakpoint'), 'chr1:154142876')
		self.assertEqual(fusion_0.get('right_breakpoint'), 'chr1:156844361')

		fusion_1 = fusion_calls[1]
		self.assertEqual(fusion_1.get('fusion_genes'), 'LMNA-NTRK1')
		self.assertEqual(fusion_1.get('left_breakpoint'), 'chr1:156100562')
		self.assertEqual(fusion_1.get('right_breakpoint'), 'chr1:156844696')

		fusion_2 = fusion_calls[2]
		self.assertEqual(fusion_2.get('fusion_genes'), 'TFG-NTRK1')
		self.assertEqual(fusion_2.get('left_breakpoint'), 'chr3:100451513')
		self.assertEqual(fusion_2.get('right_breakpoint'), 'chr1:156844360')

		fusion_3 = fusion_calls[3]
		self.assertEqual(fusion_3.get('fusion_genes'), 'ETV6-NTRK3')
		self.assertEqual(fusion_3.get('left_breakpoint'), 'chr12:12022900')
		self.assertEqual(fusion_3.get('right_breakpoint'), 'chr15:88483984')


	def test_get_fusion_info_gist(self):
		'''
		Check correct calls are present in GIST panel

		'''
		panel_obj = Panel.objects.get(panel_name='GIST', dna_or_rna='RNA')
		sample_obj = SampleAnalysis.objects.get(sample_id='rna_test_1',panel=panel_obj)

		sample_data = get_sample_info(sample_obj)
		fusion_data = get_fusion_info(sample_data, sample_obj)
		fusion_calls = fusion_data.get('fusion_calls')

		fusion_0 = fusion_calls[0]
		self.assertEqual(fusion_0.get('fusion_genes'), 'TPM3-NTRK1')
		self.assertEqual(fusion_0.get('left_breakpoint'), 'chr1:154142876')
		self.assertEqual(fusion_0.get('right_breakpoint'), 'chr1:156844361')

		fusion_1 = fusion_calls[1]
		self.assertEqual(fusion_1.get('fusion_genes'), 'LMNA-NTRK1')
		self.assertEqual(fusion_1.get('left_breakpoint'), 'chr1:156100562')
		self.assertEqual(fusion_1.get('right_breakpoint'), 'chr1:156844696')

		fusion_2 = fusion_calls[2]
		self.assertEqual(fusion_2.get('fusion_genes'), 'TFG-NTRK1')
		self.assertEqual(fusion_2.get('left_breakpoint'), 'chr3:100451513')
		self.assertEqual(fusion_2.get('right_breakpoint'), 'chr1:156844360')

		fusion_3 = fusion_calls[3]
		self.assertEqual(fusion_3.get('fusion_genes'), 'ETV6-NTRK3')
		self.assertEqual(fusion_3.get('left_breakpoint'), 'chr12:12022900')
		self.assertEqual(fusion_3.get('right_breakpoint'), 'chr15:88483984')


	def test_get_fusion_info_thyroid(self):
		'''
		Check correct calls are present in thyroid panel

		'''
		panel_obj = Panel.objects.get(panel_name='Thyroid', dna_or_rna='RNA')
		sample_obj = SampleAnalysis.objects.get(sample_id='rna_test_1',panel=panel_obj)

		sample_data = get_sample_info(sample_obj)
		fusion_data = get_fusion_info(sample_data, sample_obj)
		fusion_calls = fusion_data.get('fusion_calls')

		fusion_0 = fusion_calls[0]
		self.assertEqual(fusion_0.get('fusion_genes'), 'TPM3-NTRK1')
		self.assertEqual(fusion_0.get('left_breakpoint'), 'chr1:154142876')
		self.assertEqual(fusion_0.get('right_breakpoint'), 'chr1:156844361')

		fusion_1 = fusion_calls[1]
		self.assertEqual(fusion_1.get('fusion_genes'), 'LMNA-NTRK1')
		self.assertEqual(fusion_1.get('left_breakpoint'), 'chr1:156100562')
		self.assertEqual(fusion_1.get('right_breakpoint'), 'chr1:156844696')

		fusion_2 = fusion_calls[2]
		self.assertEqual(fusion_2.get('fusion_genes'), 'TFG-NTRK1')
		self.assertEqual(fusion_2.get('left_breakpoint'), 'chr3:100451513')
		self.assertEqual(fusion_2.get('right_breakpoint'), 'chr1:156844360')

		fusion_3 = fusion_calls[3]
		self.assertEqual(fusion_3.get('fusion_genes'), 'KIF5B-RET')
		self.assertEqual(fusion_3.get('left_breakpoint'), 'chr10:32306071')
		self.assertEqual(fusion_3.get('right_breakpoint'), 'chr10:43609927')

		fusion_4 = fusion_calls[4]
		self.assertEqual(fusion_4.get('fusion_genes'), 'NCOA4-RET')
		self.assertEqual(fusion_4.get('left_breakpoint'), 'chr10:51582937')
		self.assertEqual(fusion_4.get('right_breakpoint'), 'chr10:43612030')

		fusion_5 = fusion_calls[5]
		self.assertEqual(fusion_5.get('fusion_genes'), 'CCDC6-RET')
		self.assertEqual(fusion_5.get('left_breakpoint'), 'chr10:61665879')
		self.assertEqual(fusion_5.get('right_breakpoint'), 'chr10:43612032')

		fusion_6 = fusion_calls[6]
		self.assertEqual(fusion_6.get('fusion_genes'), 'ETV6-NTRK3')
		self.assertEqual(fusion_6.get('left_breakpoint'), 'chr12:12022900')
		self.assertEqual(fusion_6.get('right_breakpoint'), 'chr15:88483984')

		fusion_7 = fusion_calls[7]
		self.assertEqual(fusion_7.get('fusion_genes'), 'EGFR 2-7/28')
		self.assertEqual(fusion_7.get('left_breakpoint'), 'chr7:55087058')
		self.assertEqual(fusion_7.get('right_breakpoint'), 'chr7:55223522')


	def test_get_fusion_info_lung(self):
		'''
		Check correct calls are present in lung panel

		'''
		panel_obj = Panel.objects.get(panel_name='Lung', dna_or_rna='RNA')
		sample_obj = SampleAnalysis.objects.get(sample_id='rna_test_1',panel=panel_obj)

		sample_data = get_sample_info(sample_obj)
		fusion_data = get_fusion_info(sample_data, sample_obj)
		fusion_calls = fusion_data.get('fusion_calls')

		fusion_0 = fusion_calls[0]
		self.assertEqual(fusion_0.get('fusion_genes'), 'TPM3-NTRK1')
		self.assertEqual(fusion_0.get('left_breakpoint'), 'chr1:154142876')
		self.assertEqual(fusion_0.get('right_breakpoint'), 'chr1:156844361')

		fusion_1 = fusion_calls[1]
		self.assertEqual(fusion_1.get('fusion_genes'), 'LMNA-NTRK1')
		self.assertEqual(fusion_1.get('left_breakpoint'), 'chr1:156100562')
		self.assertEqual(fusion_1.get('right_breakpoint'), 'chr1:156844696')

		fusion_2 = fusion_calls[2]
		self.assertEqual(fusion_2.get('fusion_genes'), 'EML4-ALK')
		self.assertEqual(fusion_2.get('left_breakpoint'), 'chr2:42522654')
		self.assertEqual(fusion_2.get('right_breakpoint'), 'chr2:29446394')

		fusion_3 = fusion_calls[3]
		self.assertEqual(fusion_3.get('fusion_genes'), 'TFG-NTRK1')
		self.assertEqual(fusion_3.get('left_breakpoint'), 'chr3:100451513')
		self.assertEqual(fusion_3.get('right_breakpoint'), 'chr1:156844360')

		fusion_4 = fusion_calls[4]
		self.assertEqual(fusion_4.get('fusion_genes'), 'SLC34A2-ROS1;GOPC')
		self.assertEqual(fusion_4.get('left_breakpoint'), 'chr4:25665950')
		self.assertEqual(fusion_4.get('right_breakpoint'), 'chr6:117645578')

		fusion_5 = fusion_calls[5]
		self.assertEqual(fusion_5.get('fusion_genes'), 'CD74-ROS1;GOPC')
		self.assertEqual(fusion_5.get('left_breakpoint'), 'chr5:149784243')
		self.assertEqual(fusion_5.get('right_breakpoint'), 'chr6:117645578')

		fusion_6 = fusion_calls[6]
		self.assertEqual(fusion_6.get('fusion_genes'), 'KIF5B-RET')
		self.assertEqual(fusion_6.get('left_breakpoint'), 'chr10:32306071')
		self.assertEqual(fusion_6.get('right_breakpoint'), 'chr10:43609927')

		fusion_7 = fusion_calls[7]
		self.assertEqual(fusion_7.get('fusion_genes'), 'NCOA4-RET')
		self.assertEqual(fusion_7.get('left_breakpoint'), 'chr10:51582937')
		self.assertEqual(fusion_7.get('right_breakpoint'), 'chr10:43612030')

		fusion_8 = fusion_calls[8]
		self.assertEqual(fusion_8.get('fusion_genes'), 'CCDC6-RET')
		self.assertEqual(fusion_8.get('left_breakpoint'), 'chr10:61665879')
		self.assertEqual(fusion_8.get('right_breakpoint'), 'chr10:43612032')

		fusion_9 = fusion_calls[9]
		self.assertEqual(fusion_9.get('fusion_genes'), 'ETV6-NTRK3')
		self.assertEqual(fusion_9.get('left_breakpoint'), 'chr12:12022900')
		self.assertEqual(fusion_9.get('right_breakpoint'), 'chr15:88483984')

		fusion_10 = fusion_calls[10]
		self.assertEqual(fusion_10.get('fusion_genes'), 'EGFR 2-7/28')
		self.assertEqual(fusion_10.get('left_breakpoint'), 'chr7:55087058')
		self.assertEqual(fusion_10.get('right_breakpoint'), 'chr7:55223522')

		fusion_11 = fusion_calls[11]
		self.assertEqual(fusion_11.get('fusion_genes'), 'MET 14/21')
		self.assertEqual(fusion_11.get('left_breakpoint'), 'chr7:116411708')
		self.assertEqual(fusion_11.get('right_breakpoint'), 'chr7:116414934')


	def test_get_fusion_info_colorectal(self):
		'''
		Check correct calls are present in colorectal panel

		'''
		panel_obj = Panel.objects.get(panel_name='Colorectal', dna_or_rna='RNA')
		sample_obj = SampleAnalysis.objects.get(sample_id='rna_test_1',panel=panel_obj)

		sample_data = get_sample_info(sample_obj)
		fusion_data = get_fusion_info(sample_data, sample_obj)
		fusion_calls = fusion_data.get('fusion_calls')

		fusion_0 = fusion_calls[0]
		self.assertEqual(fusion_0.get('fusion_genes'), 'TPM3-NTRK1')
		self.assertEqual(fusion_0.get('left_breakpoint'), 'chr1:154142876')
		self.assertEqual(fusion_0.get('right_breakpoint'), 'chr1:156844361')

		fusion_1 = fusion_calls[1]
		self.assertEqual(fusion_1.get('fusion_genes'), 'LMNA-NTRK1')
		self.assertEqual(fusion_1.get('left_breakpoint'), 'chr1:156100562')
		self.assertEqual(fusion_1.get('right_breakpoint'), 'chr1:156844696')

		fusion_2 = fusion_calls[2]
		self.assertEqual(fusion_2.get('fusion_genes'), 'TFG-NTRK1')
		self.assertEqual(fusion_2.get('left_breakpoint'), 'chr3:100451513')
		self.assertEqual(fusion_2.get('right_breakpoint'), 'chr1:156844360')

		fusion_3 = fusion_calls[3]
		self.assertEqual(fusion_3.get('fusion_genes'), 'ETV6-NTRK3')
		self.assertEqual(fusion_3.get('left_breakpoint'), 'chr12:12022900')
		self.assertEqual(fusion_3.get('right_breakpoint'), 'chr15:88483984')
