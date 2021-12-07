from django.shortcuts import render, redirect
from django.http import Http404, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.template.loader import get_template
from django.template import Context

from .forms import NewVariantForm, SubmitForm, VariantCommentForm, UpdatePatientName, CoverageCheckForm, FusionCommentForm, SampleCommentForm, UnassignForm, ReopenForm
from .models import *
from .utils import link_callback, get_samples, unassign_check, signoff_check, make_next_check, get_variant_info, get_coverage_data, get_sample_info, get_fusion_info

import json
import os

from xhtml2pdf import pisa 
    

def signup(request):
    """
    Allow users to sign up
    User accounts are inactive by default - an admin must activate it using the admin page.
    """

    form = UserCreationForm()
    warnings = []

    if request.method == 'POST':

        form = UserCreationForm(request.POST)

        if form.is_valid():

            form.save()

            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=raw_password)
            user.is_active = False
            user.save()

            return redirect('home')
            #TODO - add some kind of confirmation

        else:
            warnings.append('Could not create an account, check that your password meets the requirements below')

    return render(request, 'analysis/sign-up.html', {'form': form, 'warning': warnings})


@login_required
def home(request):
    """
    TODO - no home page yet, just redirect to list of worksheets
    """
    return redirect('view_worksheets')


@login_required
def view_worksheets(request):
    """
    Displays all worksheets and links to the page to show all samples 
    within the worksheet
    """
    worksheets = Worksheet.objects.all().order_by('-ws_id')

    # Two seperate lists so that diagnostics runs appear first
    diagnostics_ws_list = []
    other_ws_list = []

    for w in worksheets:
        # if first two characters are digits, add to diagnostics list, otherwise add to other list
        if w.ws_id[0:2].isdigit():
            diagnostics_ws_list.append({
                'worksheet_id': w.ws_id,
                'run_id': w.run.run_id,
                'assay': w.assay,
                'status': w.get_status(),
            })
        else:
            other_ws_list.append({
                'worksheet_id': w.ws_id,
                'run_id': w.run.run_id,
                'assay': w.assay,
                'status': w.get_status(),
            })

    ws_list = diagnostics_ws_list + other_ws_list

    context = {
        'worksheets': ws_list,
    }

    return render(request, 'analysis/view_worksheets.html', context)


@login_required
def view_samples(request, worksheet_id):
    """
    Displays all samples with a worksheet and links to the analysis 
    for the sample
    """
    samples = SampleAnalysis.objects.filter(worksheet = worksheet_id)
    sample_dict = get_samples(samples)

    # if unassign modal button is pressed
    if request.method == 'POST':
        if 'unassign' in request.POST:
            unassign_form = UnassignForm(request.POST)
            if unassign_form.is_valid():
                # get sample analysis pk from form
                sample_pk = unassign_form.cleaned_data['unassign']
                sample_analysis_obj = SampleAnalysis.objects.get(pk=sample_pk)

                # get latest check and reset
                unassign_check(sample_analysis_obj)

                # reload context
                samples = SampleAnalysis.objects.filter(worksheet = worksheet_id)
                sample_dict = get_samples(samples)

     # if reopen modal button is pressed
    if request.method == 'POST':
        if 'reopen' in request.POST:
            reopen_form = ReopenForm(request.POST)
            if reopen_form.is_valid():
                # get sample analysis pk from form
                sample_pk = reopen_form.cleaned_data['reopen']
                print(sample_pk)
                sample_analysis_obj = SampleAnalysis.objects.get(pk=sample_pk)
                checks = sample_analysis_obj.get_checks()
                current_check_object=checks.get("current_check_object")

                current_check_object.status='P'
                current_check_object.save()

                # reload context
                samples = SampleAnalysis.objects.filter(worksheet = worksheet_id)
                sample_dict = get_samples(samples)

    
    # render context
    context = {
        'worksheet': worksheet_id,
        'samples': sample_dict,
        'unassign_form': UnassignForm(),
        'reopen_form': ReopenForm(),
    }

    return render(request, 'analysis/view_samples.html', context)


@login_required
def analysis_sheet(request, sample_id):
    """
    Display coverage and variant metrics to allow checking of data 
    in IGV
    """
    # load in data that is common to both RNA and DNA workflows
    sample_obj = SampleAnalysis.objects.get(pk = sample_id)
    sample_data = get_sample_info(sample_obj)

    current_step_obj = sample_data['checks']['current_check_object']

    # assign to whoever clicked the sample and reload check objects
    if sample_data['checks']['current_status'] not in ['Complete', 'Fail']:
        if current_step_obj.user == None:
            current_step_obj.user = request.user
            current_step_obj.save()
            sample_data['checks'] = sample_obj.get_checks()

        if current_step_obj.user != request.user:
            raise PermissionDenied()
        
    # set up context dictionary
    context = {
        'success': [],
        'warning': [],
        'sample_data': sample_data,
        'new_variant_form': NewVariantForm(),
        'submit_form': SubmitForm(),
        'update_name_form': UpdatePatientName(),
        'sample_comment_form': SampleCommentForm(
            comment=current_step_obj.overall_comment,
            info_check=current_step_obj.patient_info_check,
            pk=current_step_obj.pk, 
        ),
        'coverage_check_form': CoverageCheckForm(
            pk=current_step_obj.pk, 
            comment=current_step_obj.coverage_comment,
            ntc_check=current_step_obj.coverage_ntc_check,
        ),

    }


    # DNA workflow
    if sample_data['dna_or_rna'] == 'DNA':
        context['variant_data'] = get_variant_info(sample_data, sample_obj)
        context['coverage_data'] = get_coverage_data(sample_obj)

    # RNA workflow
    elif sample_data['dna_or_rna'] == 'RNA':
        context['fusion_data'] = get_fusion_info(sample_data, sample_obj)

        
    ####################################
    #  If any buttons are pressed
    ####################################

    # download PDF reports
    if request.method == 'GET':

        if 'download-dna' in request.GET:
            filename=f"{context['sample_data']['worksheet_id']}_{context['sample_data']['sample_id']}_{context['sample_data']['panel']}.pdf"

            # Create a Django response object, and specify content_type as pdf
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'

            # find the template and render it.
            template = get_template('analysis/download_dna_report.html')
            html = template.render(context)

            # create a pdf
            pisa_status = pisa.CreatePDF(
                html, dest=response, link_callback=link_callback
            )

            return response

        if 'download-rna' in request.GET:
            filename=f"{context['sample_data']['worksheet_id']}_{context['sample_data']['sample_id']}_{context['sample_data']['panel']}.pdf"

            # Create a Django response object, and specify content_type as pdf
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'

            # find the template and render it.
            template = get_template('analysis/download_rna_report.html')
            html = template.render(context)

            # create a pdf
            pisa_status = pisa.CreatePDF(
                html, dest=response, link_callback=link_callback
            )

            return response


    # submit buttons
    if request.method == 'POST':
        # patient name input form
        if 'name' in request.POST:
            update_name_form = UpdatePatientName(request.POST)

            if update_name_form.is_valid():
                new_name = update_name_form.cleaned_data['name']
                Sample.objects.filter(pk=sample_obj.sample.pk).update(sample_name=new_name)
                sample_obj = SampleAnalysis.objects.get(pk = sample_id)
                context['sample_data'] = get_sample_info(sample_obj)

        # comments submit button
        if 'variant_comment' in request.POST:
            new_comment = request.POST['variant_comment']
            pk = request.POST['pk']

            # update comment
            VariantCheck.objects.filter(pk=request.POST['pk']).update(
                comment=new_comment,
                comment_updated=timezone.now(),
            )

            # reload variant data
            context['variant_data'] = get_variant_info(sample_data, sample_obj)

        # coverage comments button
        if 'coverage_comment' in request.POST:
            new_comment = request.POST['coverage_comment']
            try:
                if request.POST['ntc_checked'] == 'on':
                    ntc_checked = True
            except:
                ntc_checked = False
            pk = request.POST['pk']

            # update comment
            Check.objects.filter(pk=request.POST['pk']).update(
                coverage_comment=new_comment,
                coverage_comment_updated=timezone.now(),
                coverage_ntc_check=ntc_checked,
            )

            # reload sample data
            context['sample_data'] = get_sample_info(sample_obj)
            current_step_obj = context['sample_data']['checks']['current_check_object']
            context['coverage_check_form'] = CoverageCheckForm(
                pk=current_step_obj.pk, 
                comment=current_step_obj.coverage_comment,
                ntc_check=current_step_obj.coverage_ntc_check,
            )

        # fusion comments submit button
        if 'fusion_comment' in request.POST:
            new_comment = request.POST['fusion_comment']
            hgvs = request.POST['hgvs']
            pk = request.POST['pk']

            # update comment
            fusion_check_obj = FusionCheck.objects.get(pk=request.POST['pk'])
            fusion_check_obj.comment=request.POST['fusion_comment']
            fusion_check_obj.comment_updated=timezone.now()

            # update fusion HGVS
            fusion_instance = fusion_check_obj.fusion_analysis.fusion_instance
            fusion_instance.hgvs = hgvs

            # save objects to database
            fusion_check_obj.save()
            fusion_instance.save()
            
            # reload variant data
            context['fusion_data'] = get_fusion_info(sample_data, sample_obj)


        # if add new variant form is clicked
        if 'hgvs_g' in request.POST:
            new_variant_form = NewVariantForm(request.POST)

            if new_variant_form.is_valid():

                new_variant_data = new_variant_form.cleaned_data

                vaf = int((new_variant_data['alt_reads'] / new_variant_data['total_reads']) * 100)

                new_variant_object, created = Variant.objects.get_or_create(
                    genomic_37 = new_variant_data['hgvs_g'],
                    genomic_38 = None,
                )
                new_variant_object.save()
                new_variant_instance_object = VariantInstance(
                    variant = new_variant_object,
                    gene = new_variant_data['gene'],
                    exon = new_variant_data['exon'],
                    hgvs_c = new_variant_data['hgvs_c'],
                    hgvs_p = new_variant_data['hgvs_p'],
                    sample = sample_obj.sample, 
                    vaf = vaf, 
                    total_count = new_variant_data['total_reads'], 
                    alt_count = new_variant_data['alt_reads'], 
                    in_ntc = new_variant_data['in_ntc'], 
                    manual_upload = True,
                )
                new_variant_instance_object.save()
                new_variant_panel_object = VariantPanelAnalysis(
                    variant_instance=new_variant_instance_object, 
                    sample_analysis=sample_obj
                )
                new_variant_panel_object.save()
                new_variant_check_object = VariantCheck(
                    variant_analysis=new_variant_panel_object, 
                    check_object=sample_obj.get_checks().get('current_check_object')
                )
                new_variant_check_object.save()

                # reload context
                context['variant_data'] = get_variant_info(sample_data, sample_obj)


        # overall sample comments form
        if 'sample_comment' in request.POST:
            new_comment = request.POST['sample_comment']
            try:
                if request.POST['patient_demographics'] == 'on':
                    info_check = True
            except:
                info_check = False
            pk = request.POST['pk']

            # update comment
            Check.objects.filter(pk=pk).update(
                overall_comment=new_comment,
                overall_comment_updated=timezone.now(),
                patient_info_check=info_check,
            )

            # reload sample data
            context['sample_data'] = get_sample_info(sample_obj)
            current_step_obj = context['sample_data']['checks']['current_check_object']
            context['sample_comment_form'] = SampleCommentForm(
                comment=current_step_obj.overall_comment,
                info_check=current_step_obj.patient_info_check,
                pk=current_step_obj.pk, 
            )



        # if finalise check submit form is clicked
        if 'next_step' in request.POST:
            submit_form = SubmitForm(request.POST)

            if submit_form.is_valid():
                next_step = submit_form.cleaned_data['next_step']
                current_step = sample_data['checks']['current_status']
                
                if sample_data['sample_name'] == None:
                    context['warning'].append('Did not finalise check - input patient name before continuing')

                if (sample_data['dna_or_rna'] == 'DNA') and (current_step_obj.coverage_ntc_check == False) and (next_step != "Fail sample"):
                    context['warning'].append('Did not finalise check - check NTC before continuing')

                if current_step_obj.patient_info_check == False:
                    context['warning'].append('Did not finalise check - check patient demographics before continuing')

                # only enter this loop if there are no warnings so far, otherwise the warnings above get skipped
                if len(context['warning']) == 0:
                    if next_step == 'Complete check':

                        # if 1st IGV, make 2nd IGV
                        if current_step == 'IGV check 1':
                            if signoff_check(request.user, current_step_obj, sample_obj):
                                make_next_check(sample_obj, 'IGV')
                                return redirect('view_samples', sample_data['worksheet_id'])
                            else:
                                context['warning'].append('Did not finalise check - not all variant have been checked')
                            
                        # if 2nd IGV (or 3rd...)
                        else:
                            # Check whether the last two checkers disagree
                            variants_match = True
                            non_matching_variants = []

                            if sample_data['dna_or_rna'] == 'DNA':
                                for variant in context['variant_data']['variant_calls']:
                                    if not variant['latest_checks_agree']:
                                        variants_match = False
                                        non_matching_variants.append(variant['genomic'])

                            elif sample_data['dna_or_rna'] == 'RNA':
                                for fusion in context['fusion_data']['fusion_calls']:
                                    if not fusion['latest_checks_agree']:
                                        variants_match = False
                                        non_matching_variants.append(fusion['fusion_genes'])

                            if not variants_match:
                                warning_text = ', '.join(non_matching_variants)
                                context['warning'].append(f'Did not finalise check - the last two checkers dont agree for the following variants: {warning_text}')
                            
                            elif signoff_check(request.user, current_step_obj, sample_obj):
                                return redirect('view_samples', sample_data['worksheet_id'])
                            else:
                                context['warning'].append('Did not finalise check - not all variants have been checked')

                                # TODO - error if there aren't at least two classifications per variant?


                    elif next_step == 'Request extra check':

                        # make extra IGV check
                        if signoff_check(request.user, current_step_obj, sample_obj):
                            make_next_check(sample_obj, 'IGV')
                            return redirect('view_samples', sample_data['worksheet_id'])
                        else:
                            context['warning'].append('Did not finalise check - not all variants have been checked')


                    elif next_step == 'Fail sample':

                        # TODO other checks on fails??? - will only count total fails, not two in a row/ mixture of fails and passes

                        # if failed 1st check, make 2nd check 
                        if current_step == 'IGV check 1':
                            signoff_check(request.user, current_step_obj, sample_obj, 'F')
                            make_next_check(sample_obj, 'IGV')
                            return redirect('view_samples', sample_data['worksheet_id'])

                        # otherwise sign off and make sample failed
                        else:
                            signoff_check(request.user, current_step_obj, sample_obj, 'F')
                            return redirect('view_samples', sample_data['worksheet_id'])


    # render the pages
    if sample_data['dna_or_rna'] == 'DNA':
        return render(request, 'analysis/analysis_sheet_dna.html', context)
    if sample_data['dna_or_rna'] == 'RNA':
        return render(request, 'analysis/analysis_sheet_rna.html', context)

    else:
        raise Http404(f'Sample must be either DNA or RNA, not {sample_data["dna_or_rna"]}')


def ajax(request):
    """
    Handles the submission of the genuine/ artefact etc dropdown box
    """
    if request.is_ajax():

        sample_pk = request.POST.get('sample_pk')
        sample_obj = SampleAnalysis.objects.get(pk = sample_pk)
        dna_or_rna = sample_obj.sample.sample_type

        selections = json.loads(request.POST.get('selections'))

        if dna_or_rna == 'DNA':
            for variant in selections:
                variant_obj = VariantPanelAnalysis.objects.get(pk=variant)
                current_check = variant_obj.get_current_check()

                new_choice = selections[variant]['genuine_dropdown']
                current_check.decision = new_choice
                current_check.save()

                # TODO make more robust - could potentially end up with not analysed labelled as something else if people click multiple times
                if new_choice != 'N':
                    variant_instance_obj = variant_obj.variant_instance
                    variant_instance_obj.final_decision = new_choice
                    variant_instance_obj.save()

        elif dna_or_rna == 'RNA':
            for variant in selections:
                fusion_obj = FusionPanelAnalysis.objects.get(pk=variant)
                current_check = fusion_obj.get_current_check()

                new_choice = selections[variant]['genuine_dropdown']
                current_check.decision = new_choice
                current_check.save()

                # TODO make more robust - could potentially end up with not analysed labelled as something else if people click multiple times
                if new_choice != 'N':
                    fusion_obj = fusion_obj.fusion_instance
                    fusion_obj.final_decision = new_choice
                    fusion_obj.save()

        # dont think this redirect is doing anything but there needs to be a HTML response
        # actual reidrect is handled inside AJAX call in analysis-snvs.html
        return redirect('analysis_sheet', sample_pk)
