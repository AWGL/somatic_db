from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from .models import *

@login_required
def home_swgs(request):
    """
    """
    return render(request, 'swgs/home.html', {})

@login_required
def view_runs(request):
    """
    View runs / worksheets
    """

    # get all the runs
    runs = Run.objects.all().order_by("-run")
    runs_list = []
    for run in runs:
        run_dict = {
            "run": run.run,
            "worksheet": run.worksheet,
            "patient_analyses": run.get_patient_analysis()
        }
        runs_list.append(run_dict)

    # context dictionary
    context = {
        'runs': runs_list
    }

    return render(request, "swgs/view_runs.html", context)

@login_required
def view_patient_analysis(request, patient_id):
    """
    View variants in a PatientAnalysis
    """

    patient_analysis = PatientAnalysis.objects.get(id=patient_id)

    germline_snvs_query = GermlineVariantInstance.objects.filter(patient_analysis=patient_analysis)
    somatic_snvs_query = SomaticVariantInstance.objects.filter(patient_analysis=patient_analysis)
    germline_snvs = []
    somatic_snvs = []

    for v in somatic_snvs_query:
        variant = v.variant.variant
        gnomad = v.gnomad_popmax_af
        vaf = float(v.af) * 100
        if float(gnomad) >= 0.05:
            pass
        elif float(gnomad) == -1:
            gnomad = "Not in Gnomad"
            variant_dict = {
                "pk": variant,
                "gnomad": str(gnomad),
                "vaf": f"{vaf:.2f}"
            }
            somatic_snvs.append(variant_dict)
        else:
            variant_dict = {
                "pk": variant,
                "gnomad": str(gnomad),
                "vaf": f"{vaf:.2f}"
            }
            somatic_snvs.append(variant_dict)

    for v in germline_snvs_query:
        variant = v.variant.variant
        gnomad = v.gnomad_popmax_af
        vaf = float(v.af) * 100
        if float(gnomad) >= 0.05:
            pass
        elif float(gnomad) == -1:
            gnomad = "Not in Gnomad"
            variant_dict = {
                "pk": variant,
                "gnomad": str(gnomad),
                "vaf": f"{vaf:.2f}"
            }
            germline_snvs.append(variant_dict)
        else:
            variant_dict = {
                "pk": variant,
                "gnomad": str(gnomad),
                "vaf": f"{vaf:.2f}"
            }
            germline_snvs.append(variant_dict)
    
    context = {
        "somatic_snvs": somatic_snvs,
        "germline_snvs": germline_snvs
    }

    return render(request, "swgs/view_patient_analysis.html", context)
    