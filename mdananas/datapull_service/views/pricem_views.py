from django.shortcuts import render
from django.http import JsonResponse, HttpResponseRedirect
from django.db.models import Q
from datapull_service.models.pricem_models import *
from datapull_service.forms.pricem_forms import *

def main_page(request):
    if 'pricem_ext_suo' in request.GET:
        response = HttpResponseRedirect(request.path)
        response.set_cookie('pricem_ext_suo', 'on' if request.GET.get('pricem_ext_suo') == 'on' else 'off', max_age = 86400)
        return response
    pricem_ext_suo = request.COOKIES.get('pricem_ext_suo', 'on') == 'on'
    if 'pricem_int_suo' in request.GET:
        response = HttpResponseRedirect(request.path)
        response.set_cookie('pricem_int_suo', 'on' if request.GET.get('pricem_int_suo') == 'on' else 'off', max_age = 86400)
        return response
    pricem_int_suo = request.COOKIES.get('pricem_int_suo', 'on') == 'on'
    int_monitorings = PRICEM_DATA_INT_Monitoring.objects.filter(Q(root_mix=None) & Q(root_tu=None)) if pricem_int_suo else PRICEM_DATA_INT_Monitoring.objects.all()
    ext_monitorings = PRICEM_DATA_EXT_Monitoring.objects.filter(root_cmp=None) if pricem_ext_suo else PRICEM_DATA_EXT_Monitoring.objects.all()
    chains = PRICEM_PIVOT_Promoplan_chain.objects.all()
    schedule = TaskSchedule.objects.all()
    logs = PricemLOG.objects.all()
    existing_tu = Tu.objects.all().order_by('xcode_tu')
    existing_mix = Mix.objects.all().order_by('xcode_mix')
    existing_cmp = CMP.objects.all().order_by('ean')
    existing_customers = ROOT_PIVOT_Customer.objects.all()

    if request.method == 'POST':
        form = NewTaskForm(request.POST)
        if form.is_valid():
            task_object, _ = TaskSchedule.objects.update_or_create(
                time_hour=form.cleaned_data['time_hour'],
                time_minute=form.cleaned_data['time_minute'],
                defaults={'is_active': form.cleaned_data.get('is_active', False)},
            )
        else:
            form = ActionTaskForm(request.POST)
            if form.is_valid():
                match form.cleaned_data.get('form_name'):
                    case 'delete_task':
                        TaskSchedule.objects.filter(id = form.cleaned_data.get('task_id')).delete()
                    case 'change_task':
                        TaskSchedule.objects.filter(id = form.cleaned_data.get('task_id')).update(is_active = form.cleaned_data.get('is_active', False))
                    case _:
                        pass
            else:
                form = NewChainForm(request.POST)
                if form.is_valid():
                    source_customer = form.cleaned_data.get('source_customer')
                    promoplan_customer = form.cleaned_data.get('promoplan_customer')
                    chain_object, _ = PRICEM_PIVOT_Promoplan_chain.objects.get_or_create(source_root_pivot_customer = ROOT_PIVOT_Customer.objects.get(id = source_customer) if source_customer else None,
                                                                                         offer = form.cleaned_data.get('offer'),
                                                                                         promoplan_root_pivot_customer = ROOT_PIVOT_Customer.objects.get(id = promoplan_customer) if promoplan_customer else None,
                                                                                         additional_seller = form.cleaned_data.get('additional_seller'))
                else:
                    form = ActionChainForm(request.POST)
                    if form.is_valid():
                        match form.cleaned_data.get('form_name'):
                            case 'delete_chain':
                                PRICEM_PIVOT_Promoplan_chain.objects.filter(id = form.cleaned_data.get('chain_id')).delete()
                            case _:
                                pass
                    else:
                        form = UpdateExtMonitoringForm(request.POST)
                        if form.is_valid():
                            PRICEM_DATA_EXT_Monitoring.objects.filter(id = form.cleaned_data.get('ext_monitoring_id')).update(
                                root_cmp = CMP.objects.get(id = form.cleaned_data.get('root_cmp'))
                            )
                        else:
                            form = UpdateIntMonitoringForm(request.POST)
                            if form.is_valid():
                                object = PRICEM_DATA_INT_Monitoring.objects.get(id = form.cleaned_data['int_monitoring_id'])
                                if form.cleaned_data.get('is_mix'):
                                    object.is_mix = True
                                    object.root_tu = None
                                    object.root_mix = Mix.objects.get(id = form.cleaned_data['root_mix']) if form.cleaned_data['root_mix'] else None
                                else:
                                    object.is_mix = False
                                    object.root_mix = None
                                    object.root_tu = Tu.objects.get(id = form.cleaned_data['root_tu']) if form.cleaned_data['root_tu'] else None
                                object.save()
                            else:
                                print(form.errors)
    return render(request, 'datapull_service/pricem_page.html', context={'int_monitorings': int_monitorings, 'existing_tu': existing_tu, 'existing_mix': existing_mix,
                                                                         'ext_monitorings': ext_monitorings, 'existing_cmp': existing_cmp,
                                                                         'pricem_ext_suo': pricem_ext_suo, 'pricem_int_suo': pricem_int_suo,
                                                                         'existing_customers': existing_customers,
                                                                         'chains': chains, 'schedule': schedule, 'logs': logs})