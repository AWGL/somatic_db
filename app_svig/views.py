from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required

from somatic_variant_db.settings import SVIG_CODE_VERSION

from app_svig.models import *
from app_svig.forms import *

from analysis.models import VariantPanelAnalysis

import json

# Create your views here.
@login_required
def view_classifications(request):
    """
    """
    new_classifications_form = NewClassification()

    context = {
        'classifications': Classification.objects.all(),
        'new_form': new_classifications_form,
    }

    # when buttons are pressed
    if request.method == 'POST':

        # only one button at the mo
        new_classifications_form = NewClassification(request.POST)
        if new_classifications_form.is_valid():
            # get variant instance
            var = VariantPanelAnalysis(id = 28) # TODO this is hardcoded for testing

            # get latest annotations obj
            annotation_versions_obj = AnnotationVersions.objects.latest('version')

            new_var_obj = Variant(
                svd_variant = var,
                vep_csq = 'missense_variant',
                cgc_mode_action = 'TSG',
                cgc_mutation_types = 'Mis; N; F',
                annotation_versions = annotation_versions_obj,
            )
            new_var_obj.save()

            new_classification_obj = Classification(
                variant = new_var_obj,
                svig_version = SVIG_CODE_VERSION,
            )
            new_classification_obj.save()
            new_classification_obj.make_new_check()

            context['classifications'] = Classification.objects.all()


    return render(request, 'app_svig/all_classifications.html', context)


@login_required
def classify(request, classification):
    """
    Page to perform S-VIG classifications
    """
    # load in classification and check objects from url args
    classification_obj = Classification.objects.get(id = classification)
    current_check_obj = classification_obj.get_latest_check()

    # load context from classification obj
    context = classification_obj.get_context()

    # load in forms and add to context
    previous_class_choices = classification_obj.get_previous_classification_choices()
    context['forms'] = {
        'check_info_form': CheckInfoForm(),
        'reopen_check_info_form': ResetCheckInfoForm(),
        'previous_class_form': PreviousClassificationForm(previous_class_choices=previous_class_choices),
        'reopen_previous_class_form': ResetPreviousClassificationsForm(),
        'comment_form': CommentForm(),
        'finalise_form': FinaliseCheckForm(),
    }
    # TODO check if refreshes needed after form submit + hide reopen form in a modal
    # TODO visualise different forms depending on check etc
    # TODO comments modal
    # TODO when checks disagree
    # TODO generic template for all codes
    # TODO papers model with pubmed api
    # TODO finish previous classifications page

    # ------------------------------------------------------------------------
    # when buttons are pressed
    if request.method == 'POST':

        # button to confirm smaple/variant tab has been checked
        if 'check_info_form' in request.POST:
            check_info_form = CheckInfoForm(request.POST)
            if check_info_form.is_valid():
                current_check_obj.info_check = True
                current_check_obj.save()

        # button to reset sample/patient info tab
        if 'reset_info_check' in request.POST:
            reopen_check_info_form = ResetCheckInfoForm(request.POST)
            if reopen_check_info_form.is_valid():
                current_check_obj.info_check = False
                current_check_obj.previous_classifications_check = False
                current_check_obj.full_classification = False
                current_check_obj.save()
                current_check_obj.remove_codes()

        # button to select to use a previous classification or start a new one
        if 'use_previous_class' in request.POST:
            previous_class_form = PreviousClassificationForm(request.POST, previous_class_choices=previous_class_choices)
            if previous_class_form.is_valid():
                use_previous = previous_class_form.cleaned_data['use_previous_class']
                if use_previous == 'canonical':
                    print(use_previous)
                    #TODO change setting in classification obj and save link to reused classification

                elif use_previous == 'previous':
                    print(use_previous)
                    #TODO change setting in classification obj and save link to reused classification

                elif use_previous == 'new':
                    # change setting in classification obj and load up codes linked to check
                    current_check_obj.full_classification = True
                    current_check_obj.save()
                    current_check_obj.make_new_codes()

                    # redirect so that form isnt resubmitted on refresh
                    return redirect('svig-analysis', classification_obj.pk)

        # button to revert previous/new classification form
        if 'reset_previous_class_check' in request.POST:
            reopen_previous_class_form = ResetPreviousClassificationsForm(request.POST)
            if reopen_previous_class_form.is_valid():
                current_check_obj.full_classification = False
                current_check_obj.save()
                current_check_obj.remove_codes()

        if 'finalise_check' in request.POST:
            finalise_form = FinaliseCheckForm(request.POST)
            if finalise_form.is_valid():
                next_step = finalise_form.cleaned_data['next_step']
                current_check_obj.signoff_check(next_step)
                return redirect('view-all-svig')


    return render(request, 'app_svig/svig_base.html', context)


def ajax_svig(request):
    """
    Generates new chunks of HTML for the classification summary boxes on the S-VIG tab (within a div called class-box). 
    Called in JS at bottom of svig_classify.html
    """
    if request.is_ajax():
        # get variables from AJAX input
        selections = json.loads(request.POST.get('selections'))
        check_pk = request.POST.get('check_pk')

        # load variables needed for new display
        current_check_obj = Check.objects.get(id=check_pk)
        score, final_class, css_class = current_check_obj.update_codes(selections)
        codes_by_category = current_check_obj.codes_by_category()

        # empty dict for new html
        data = {}

        # make new classification box and add to results dict
        class_box_context = {
            'current_score': score,
            'current_class': final_class,
            'class_css': css_class,
        }
        class_box_html = render_to_string('app_svig/ajax/classification.html', class_box_context)
        data['class_box'] = class_box_html

        # make the code summary and complete true/false segments for each category of code and add to results dict
        for category, value in codes_by_category.items():

            # summary of codes applied
            html = render_to_string('app_svig/ajax/category_summary.html', {'applied_codes': value['applied_codes']})
            data[f'codes_summary_{category}'] = html

            # complete yes/no
            html = render_to_string('app_svig/ajax/category_complete.html', {'complete': value['complete']})
            data[f'complete_{category}'] = html

        return JsonResponse(data)