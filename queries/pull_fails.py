# Description:
# Pull out all sample fail checks between two dates, date range hardcoded in script
# 
# Date: 11/10/2023 - SS
# Use: python manage.py shell < /home/ew/somatic_db/queries/pull_fails.py (with somatic_variant_db env activated)

import datetime
from analysis.models import VariantInstance, SampleAnalysis, VariantPanelAnalysis
from django.contrib.humanize.templatetags.humanize import ordinal

#set date range
start_date = datetime.date(2023, 9, 20)
end_date = datetime.date(2023, 12, 20)

#Get all sample analyses
samples = SampleAnalysis.objects.all()

#Loop over samples
for s in samples:

	#Get all IGV checks
	checks = s.get_checks()['all_checks']
	
	#Use date of first check therefore will be after go live
	#if the check is between the dates, get it. Additionally check it's DNA
	if checks[0].signoff_time != None:
	
		within_timeframe = start_date <= checks[0].signoff_time.date() <= end_date
		if within_timeframe: #and s.panel.assay == 1:

			if s.panel.assay == "1":

				#Loop over checks and print those with a fail plus the referral type
				for check in checks:

					if check.status == "F":

						print (s.sample_id, s.panel.panel_name)

