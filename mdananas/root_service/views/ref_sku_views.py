from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.forms import inlineformset_factory
from django.db.models import Q
from ..models.ref_sku_models import *
from ..forms.ref_sku_forms import *
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

def main_page(request):
    return HttpResponse("Hello, world!")

def ref_sku(request):
    if 'category' in request.GET or 'groupname' in request.GET or 'xcode' in request.GET:
        response = HttpResponseRedirect(request.path)
        response.set_cookie('category-filter', request.GET['category'], max_age = 86400)
        response.set_cookie('groupname-filter', request.GET['groupname'], max_age = 86400)
        response.set_cookie('xcode-filter', request.GET['xcode'], max_age = 86400)
        return response
    selected_category = request.COOKIES.get('category-filter')
    selected_groupname = request.COOKIES.get('groupname-filter')
    selected_xcode = request.COOKIES.get('xcode-filter')
    cu_filters = Q()
    tu_filters = Q()
    mix_filters = Q()
    if selected_category or selected_groupname or selected_xcode:
        if selected_category:
            cu_filters &= Q(category=selected_category)
            tu_filters &= Q(root_cu__category=selected_category)
            mix_filters &= Q(category=selected_category)
        if selected_groupname:
            cu_filters &= Q(groupname=selected_groupname)
            tu_filters &= Q(root_cu__groupname=selected_groupname)
            mix_filters &= Q(groupname=selected_groupname)
        if selected_xcode:
            cu_filters &= Q(xcode_cu__contains=selected_xcode)
            tu_filters &= Q(xcode_tu__contains=selected_xcode)
            mix_filters &= Q(xcode_mix__contains=selected_xcode)
    selected_cu = request.GET.get('selected_cu')
    existing_cu = Cu.objects.filter(cu_filters)
    existing_tu = Tu.objects.filter(root_cu_id = selected_cu).order_by('xcode_tu') if selected_cu else Tu.objects.filter(tu_filters).order_by('xcode_tu')
    existing_mix = Mix.objects.filter(mixcomposition__root_cu_id = selected_cu) if selected_cu else Mix.objects.filter(mix_filters)
    existing_categories = existing_cu.values_list('category', flat=True).union(existing_mix.values_list('category', flat=True)).order_by('category')
    existing_groupnames = existing_cu.values_list('groupname', flat=True).union(existing_mix.values_list('groupname', flat=True)).order_by('groupname')
    return render(request, 'root_service/ref_sku_page.html', context = {'existing_cu': existing_cu.order_by('xcode_cu'), 'existing_tu': existing_tu, 'existing_mix': existing_mix.order_by('xcode_mix'),
                                                                        'selected_cu': int(selected_cu) if selected_cu else None,
                                                                        'existing_categories': existing_categories, 'existing_groupnames': existing_groupnames,
                                                                        'selected_category': selected_category, 'selected_groupname': selected_groupname,
                                                                        'selected_xcode': selected_xcode})

def cu_creation_page(request):
    existing_categories = Cu.objects.values_list('category', flat=True).distinct().order_by('category')
    existing_groupnames = Cu.objects.values_list('groupname', flat=True).distinct().order_by('groupname')
    definitions = Definition.objects.all()
    suppliers = Supplier.objects.all().order_by('supplier_name')
    return render(request, 'root_service/cu_page.html', context = {'is_create_mode': True,
                                                                   'cu': None, 'dimensions': None,
                                                                   'customs_info': None,
                                                                   'existing_categories': existing_categories, 'existing_groupnames': existing_groupnames,
                                                                   'suppliers': suppliers, 'definitions': definitions})

def cu_creation_page_save(request):
    if request.method == 'POST':
        xcode_cu = request.POST.get('xcode_cu')
        if not xcode_cu:
            return redirect('cu_create')
        form = CuForm(request.POST)
        if form.is_valid():
            cu_object = Cu()
            if form.cleaned_data.get('rus_definition'):
                cu_object.root_pd = Definition.objects.get_or_create(rus_definition=form.cleaned_data.get('rus_definition'))[0]
            else:
                cu_object.root_pd = Definition.objects.get(id=form.cleaned_data.get('root_pd'))
            cu_object.xcode_cu = form.cleaned_data.get('xcode_cu')
            cu_object.ean_cu = form.cleaned_data.get('ean_cu')
            cu_object.category = form.cleaned_data.get('category')
            cu_object.groupname = form.cleaned_data.get('groupname')
            cu_object.shelf_life = form.cleaned_data.get('shelf_life')
            cu_object.save()
            CuDimensions.objects.create(root_cu=cu_object)
            CuCustomsInfo.objects.create(root_cu=cu_object)
            return redirect('show_cu', cu_id=cu_object.id)
        else:
            print(form.errors)
    return redirect('cu_create')

def get_lclass_tree():
    classifications = LClassification.objects.all()
    tree = {}
    for item in classifications:
        l1 = item.l1_class
        l2 = item.l2_class
        l3 = item.l3_class
        l4 = item.l4_class
        l5 = item.l5_class
        
        if l1 not in tree:
            tree[l1] = {}
        if l2 not in tree[l1]:
            tree[l1][l2] = {}
        if l3 not in tree[l1][l2]:
            tree[l1][l2][l3] = {}
        if l4 not in tree[l1][l2][l3]:
            tree[l1][l2][l3][l4] = {}

        tree[l1][l2][l3][l4][l5] = item.id
    
    return tree

def cu_page(request, cu_id):
    cu_object = get_object_or_404(Cu, id=cu_id)
    existing_categories = Cu.objects.values_list('category', flat=True).distinct().order_by('category')
    existing_groupnames = Cu.objects.values_list('groupname', flat=True).distinct().order_by('groupname')
    definitions = Definition.objects.all()
    suppliers = Supplier.objects.all().order_by('supplier_name')
    cu_dimensions, created_cu_dimensions = CuDimensions.objects.get_or_create(root_cu=cu_object)
    cu_customs_info, created_cu_customs_info = CuCustomsInfo.objects.get_or_create(root_cu=cu_object)
    related_tus = Tu.objects.filter(root_cu = cu_object)
    related_mixes = [comp.root_mix for comp in MixComposition.objects.filter(root_cu = cu_object)]
    return render(request, 'root_service/cu_page.html', context = {'is_create_mode': False,
                                                                   'cu': cu_object, 'dimensions': created_cu_dimensions if created_cu_dimensions else cu_dimensions,
                                                                   'customs_info': created_cu_customs_info if created_cu_customs_info else cu_customs_info,
                                                                   'existing_categories': existing_categories, 'existing_groupnames': existing_groupnames,
                                                                   'suppliers': suppliers, 'definitions': definitions, 'related_tus': related_tus, 'related_mixes': related_mixes,
                                                                   'tree_data': get_lclass_tree()})
#тут жоский вайбкодинг
def cu_set_classification(request, cu_id):
    try:
        data = json.loads(request.body)
        classification_id = data.get('classification_id')
        
        # Получаем объекты
        cu = Cu.objects.get(id=cu_id)
        classification = LClassification.objects.get(id=classification_id)
        
        # Привязываем классификацию к CU
        cu.root_lclass = classification
        cu.save()
        
        # Возвращаем успешный ответ
        return JsonResponse({
            'status': 'success',
            'message': 'Классификация успешно сохранена',
            'data': {
                'cu_id': cu_id,
                'classification_id': classification_id,
                'full_path': ""
            }
        })
        
    except Cu.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'CU не найден'
        }, status=404)
        
    except LClassification.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Классификация не найдена'
        }, status=404)
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

def mix_set_classification(request, mix_id):
    """Сохранение классификации для MIX"""
    try:
        data = json.loads(request.body)
        classification_id = data.get('classification_id')
        
        if not classification_id:
            return JsonResponse({
                'status': 'error',
                'message': 'classification_id is required'
            }, status=400)
        
        # Получаем объекты
        mix = get_object_or_404(Mix, id=mix_id)
        classification = get_object_or_404(LClassification, id=classification_id)
        
        # Привязываем классификацию к MIX
        mix.root_lclass = classification
        mix.save()
        
        # Получаем полный путь
        full_path = f"{classification.l1_class} / {classification.l2_class} / {classification.l3_class} / {classification.l4_class} / {classification.l5_class}"
        
        return JsonResponse({
            'status': 'success',
            'message': 'Классификация MIX успешно сохранена',
            'data': {
                'mix_id': mix_id,
                'classification_id': classification_id,
                'full_path': full_path,
                'levels': {
                    'l1': classification.l1_class,
                    'l2': classification.l2_class,
                    'l3': classification.l3_class,
                    'l4': classification.l4_class,
                    'l5': classification.l5_class
                }
            }
        })
        
    except Mix.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': f'MIX with id {mix_id} not found'
        }, status=404)
        
    except LClassification.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': f'Classification with id {classification_id} not found'
        }, status=404)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON'
        }, status=400)
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

def cu_page_save(request, cu_id):
    cu_object = get_object_or_404(Cu, id=cu_id)
    if request.method == 'POST':
        form = CuForm(request.POST)
        if form.is_valid():
            if form.cleaned_data.get('rus_definition'):
                cu_object.root_pd = Definition.objects.get_or_create(rus_definition=form.cleaned_data.get('rus_definition'))[0]
            elif form.cleaned_data.get('root_pd'):
                cu_object.root_pd = Definition.objects.get(id=form.cleaned_data.get('root_pd'))
            else:
                cu_object.root_pd = None
            cu_object.xcode_cu = form.cleaned_data.get('xcode_cu')
            cu_object.ean_cu = form.cleaned_data.get('ean_cu') or None
            cu_object.category = form.cleaned_data.get('category')
            cu_object.groupname = form.cleaned_data.get('groupname')
            cu_object.shelf_life = form.cleaned_data.get('shelf_life')
            cu_object.tmp_xcode_cu = form.cleaned_data.get('tmp_xcode_cu') or None
            cu_object.save()
        else:
            print(form.errors)
    return redirect('show_cu', cu_id=cu_id)

def cu_page_save_dimensions(request, cu_id):
    cu_object = get_object_or_404(Cu, id=cu_id)
    cu_dimensions, created_cu_dimensions = CuDimensions.objects.get_or_create(root_cu=cu_object)
    if request.method == 'POST':
        form = CuDimensionsForm(request.POST, instance=created_cu_dimensions if created_cu_dimensions else cu_dimensions)
        if form.is_valid():
            form.save()
    return redirect('show_cu', cu_id=cu_id)

def cu_page_get_supplier_info(request):
    supplier_id = request.GET.get('supplier_id')
    if supplier_id:
        return JsonResponse({'ownership': Supplier.objects.get(id = supplier_id).ownership, 'currency': Supplier.objects.get(id = supplier_id).currency})

def cu_page_save_customs_info(request, cu_id):
    cu_object = get_object_or_404(Cu, id=cu_id)
    cu_customs_info, created_cu_customs_info = CuCustomsInfo.objects.get_or_create(root_cu=cu_object)
    if request.method == 'POST':
        form = CuCustomsInfoForm(request.POST, instance=created_cu_customs_info if created_cu_customs_info else cu_customs_info)
        if form.is_valid():
            form.save()
        else:
            print(form.errors)
    return redirect('show_cu', cu_id=cu_id)

def cu_page_save_supplier(request, cu_id):
    cu_object = get_object_or_404(Cu, id=cu_id)
    if request.method == 'POST':
        if request.POST.get('supplier_name'):
            supplier_object = Supplier.objects.get_or_create(supplier_name=request.POST.get('supplier_name'))[0]
            supplier_object.ownership = request.POST.get('ownership')
            supplier_object.currency = request.POST.get('currency')
            supplier_object.save()
        else:
            supplier_object = Supplier.objects.get(id = request.POST.get('supplier'))
        cu_object.supplier = supplier_object
        cu_object.save()
    return redirect('show_cu', cu_id=cu_id)

def tu_page(request, tu_id):
    tu_object = get_object_or_404(Tu, id=tu_id)
    existing_statuses = Tu.objects.values_list('status', flat=True).distinct()
    existing_types = Tu.objects.values_list('type', flat=True).distinct()
    existing_cu = Cu.objects.all().order_by('xcode_cu')
    existing_is_shared = TuOrderInfo.objects.values_list('is_shared', flat=True).distinct().order_by('is_shared')
    tu_dimensions, created_tu_dimensions = TuDimensions.objects.get_or_create(root_tu=tu_object)
    tu_descriptions, created_tu_descriptions = TuDescription.objects.get_or_create(root_tu=tu_object)
    tu_logistics_info, created_tu_logistics_info = TuLogisticsInfo.objects.get_or_create(root_tu=tu_object)
    tu_order_info, created_tu_order_info = TuOrderInfo.objects.get_or_create(root_tu=tu_object)
    active_list_object = Active_list.objects.filter(root_tu = tu_object).first()
    is_cons_active = active_list_object.cons_active if active_list_object else False
    return render(request, 'root_service/tu_page.html', context = {'is_create_mode': False,
                                                                   'tu': tu_object, 'tu_descriptions': created_tu_descriptions if created_tu_descriptions else tu_descriptions,
                                                                   'dimensions': created_tu_dimensions if created_tu_dimensions else tu_dimensions,
                                                                   'logistics_info': created_tu_logistics_info if created_tu_logistics_info else tu_logistics_info,
                                                                   'order_info': created_tu_order_info if created_tu_order_info else tu_order_info,
                                                                   'existing_statuses': existing_statuses, 'existing_cu': existing_cu, 'existing_types': existing_types,
                                                                   'existing_is_shared': existing_is_shared, 'is_cons_active': is_cons_active})

def tu_creation_page(request):
    existing_statuses = Tu.objects.values_list('status', flat=True).distinct()
    existing_types = Tu.objects.values_list('type', flat=True).distinct()
    existing_cu = Cu.objects.all().order_by('xcode_cu')
    return render(request, 'root_service/tu_page.html', context = {'is_create_mode': True,
                                                                   'tu': None, 'tu_descriptions': None,
                                                                   'dimensions': None,
                                                                   'logistics_info': None,
                                                                   'order_info': None,
                                                                   'existing_statuses': existing_statuses, 'existing_cu': existing_cu, 'existing_types': existing_types,
                                                                   'existing_is_shared': None})

def tu_creation_page_save(request):
    if request.method == 'POST':
        xcode_tu = request.POST.get('xcode_tu')
        if not xcode_tu:
            return redirect('tu_create')
        tu_form = TuForm(request.POST)
        if tu_form.is_valid():
            tu = tu_form.save()
            TuDimensions.objects.create(root_tu=tu)
            TuDescription.objects.create(root_tu=tu)
            TuLogisticsInfo.objects.create(root_tu=tu)
            TuOrderInfo.objects.create(root_tu=tu)
            return redirect('show_tu', tu_id=tu.id)
    return redirect('tu_create')

def tu_page_save(request, tu_id):
    tu_object = get_object_or_404(Tu, id=tu_id)
    active_list_object = Active_list.objects.filter(root_tu = tu_object).first()
    if request.method == 'POST':
        form = TuForm(request.POST, instance=tu_object)
        if form.is_valid():
            if form.cleaned_data['cons_active']:
                active_list_object = active_list_object if active_list_object else Active_list()
                active_list_object.root_tu = tu_object
                active_list_object.cons_active = True
                active_list_object.save()
            elif active_list_object:
                active_list_object.cons_active = False
                active_list_object.save()
            form.save()
        else:
            print(form.errors)
    return redirect('show_tu', tu_id=tu_id)

def copy_tu_side_object(object, tu):
    object.pk = None
    object.id = None
    object.root_tu = tu
    object.save()

def tu_page_copy(request, tu_id):
    tu_object = get_object_or_404(Tu, id=tu_id)
    new_description = get_object_or_404(TuDescription, root_tu = tu_object)
    new_dimensions = get_object_or_404(TuDimensions, root_tu = tu_object)
    new_logistics_info = get_object_or_404(TuLogisticsInfo, root_tu = tu_object)
    new_order_info = get_object_or_404(TuOrderInfo, root_tu = tu_object)
    tu_object.pk = None
    tu_object.id = None
    tu_object.xcode_tu = f"{tu_object.xcode_tu}-COPY"
    tu_object.save()
    copy_tu_side_object(new_description, tu_object)
    copy_tu_side_object(new_dimensions, tu_object)
    copy_tu_side_object(new_logistics_info, tu_object)
    copy_tu_side_object(new_order_info, tu_object)
    return redirect('show_tu', tu_id=tu_object.id)

def tu_page_save_descriptions(request, tu_id):
    tu_object = get_object_or_404(Tu, id=tu_id)
    tu_descriptions, created_tu_descriptions = TuDescription.objects.get_or_create(root_tu=tu_object)
    if request.method == 'POST':
        form = TuDescriptionForm(request.POST, instance=created_tu_descriptions if created_tu_descriptions else tu_descriptions)
        if form.is_valid():
            form.save()
    return redirect('show_tu', tu_id=tu_id)

def tu_page_save_dimensions(request, tu_id):
    tu_object = get_object_or_404(Tu, id=tu_id)
    tu_dimensions, created_tu_dimensions = TuDimensions.objects.get_or_create(root_tu=tu_object)
    if request.method == 'POST':
        form = TuDimensionsForm(request.POST, instance=created_tu_dimensions if created_tu_dimensions else tu_dimensions)
        if form.is_valid():
            form.save()
    return redirect('show_tu', tu_id=tu_id)

def tu_page_save_logistics_info(request, tu_id):
    tu_object = get_object_or_404(Tu, id=tu_id)
    tu_logistics_info, created_tu_logistics_info = TuLogisticsInfo.objects.get_or_create(root_tu=tu_object)
    if request.method == 'POST':
        form = TuLogisticsInfoForm(request.POST, instance=created_tu_logistics_info if created_tu_logistics_info else tu_logistics_info)
        if form.is_valid():
            form.save()
    return redirect('show_tu', tu_id=tu_id)

def tu_page_save_order_info(request, tu_id):
    tu_object = get_object_or_404(Tu, id=tu_id)
    tu_order_info, created_tu_order_info = TuOrderInfo.objects.get_or_create(root_tu=tu_object)
    if request.method == 'POST':
        form = TuOrderInfoForm(request.POST, instance=created_tu_order_info if created_tu_order_info else tu_order_info)
        if form.is_valid():
            form.save()
    return redirect('show_tu', tu_id=tu_id)

def mix_page(request, mix_id):
    mix_object = get_object_or_404(Mix, id=mix_id)
    existing_categories = Mix.objects.values_list('category', flat=True).distinct().order_by('category')
    existing_groupnames = Mix.objects.values_list('groupname', flat=True).distinct().order_by('groupname')
    definitions = Definition.objects.all()
    mix_dimensions, created_mix_dimensions = MixDimensions.objects.get_or_create(root_mix=mix_object)
    mix_logistics_info, created_mix_logistics_info = MixLogisticsInfo.objects.get_or_create(root_mix=mix_object)
    mix_customs_info, created_mix_customs_info = MixCustomsInfo.objects.get_or_create(root_mix=mix_object)
    mix_descriptions, created_mix_descriptions = MixDescription.objects.get_or_create(root_mix=mix_object)
    existing_statuses = Tu.objects.values_list('status', flat=True).distinct().order_by('status')
    compositions = MixComposition.objects.filter(root_mix = mix_id)
    active_list_object = Active_list.objects.filter(root_mix = mix_object).first()
    is_cons_active = active_list_object.cons_active if active_list_object else False
    MixComponentFormSet = inlineformset_factory(
        parent_model=Mix,
        model=MixComposition,
        form=MixCompositionForm,
        extra=1,
        can_delete=True
    )
    formset = MixComponentFormSet(instance=mix_object)
    return render(request, 'root_service/mix_page.html', context = {'is_create_mode': False,
                                                                   'mix': mix_object,
                                                                   'existing_categories': existing_categories, 'existing_groupnames': existing_groupnames,
                                                                   'existing_statuses': existing_statuses, 'definitions': definitions, 'compositions': compositions,
                                                                   'formset': formset, 'dimensions': created_mix_dimensions if created_mix_dimensions else mix_dimensions,
                                                                   'logistics_info': created_mix_logistics_info if created_mix_logistics_info else mix_logistics_info,
                                                                   'customs_info': created_mix_customs_info if created_mix_customs_info else mix_customs_info,
                                                                   'descriptions': created_mix_descriptions if created_mix_descriptions else mix_descriptions,
                                                                   'is_cons_active': is_cons_active, 'tree_data': get_lclass_tree()})

def mix_page_save_dimensions(request, mix_id):
    mix_object = get_object_or_404(Mix, id=mix_id)
    mix_dimensions, created_mix_dimensions = MixDimensions.objects.get_or_create(root_mix=mix_object)
    if request.method == 'POST':
        form = MixDimensionsForm(request.POST, instance=created_mix_dimensions if created_mix_dimensions else mix_dimensions)
        if form.is_valid():
            form.save()
    return redirect('show_mix', mix_id=mix_id)

def mix_page_save_logistics_info(request, mix_id):
    mix_object = get_object_or_404(Mix, id=mix_id)
    mix_logistics_info, created_mix_logistics_info = MixLogisticsInfo.objects.get_or_create(root_mix=mix_object)
    if request.method == 'POST':
        form = MixLogisticsInfoForm(request.POST, instance=created_mix_logistics_info if created_mix_logistics_info else mix_logistics_info)
        if form.is_valid():
            form.save()
    return redirect('show_mix', mix_id=mix_id)

def mix_page_save_customs_info(request, mix_id):
    mix_object = get_object_or_404(Mix, id=mix_id)
    mix_customs_info, created_mix_customs_info = MixCustomsInfo.objects.get_or_create(root_mix=mix_object)
    if request.method == 'POST':
        form = MixCustomsInfoForm(request.POST, instance=created_mix_customs_info if created_mix_customs_info else mix_customs_info)
        if form.is_valid():
            form.save()
        else:
            print(form.errors)
    return redirect('show_mix', mix_id=mix_id)

def mix_page_save_descriptions(request, mix_id):
    mix_object = get_object_or_404(Mix, id=mix_id)
    mix_descriptions, created_mix_descriptions = MixDescription.objects.get_or_create(root_mix=mix_object)
    if request.method == 'POST':
        form = MixDescriptionForm(request.POST, instance=created_mix_descriptions if created_mix_descriptions else mix_descriptions)
        if form.is_valid():
            form.save()
    return redirect('show_mix', mix_id=mix_id)

def mix_creation_page(request):
    existing_categories = Mix.objects.values_list('category', flat=True).distinct().order_by('category')
    existing_groupnames = Mix.objects.values_list('groupname', flat=True).distinct().order_by('groupname')
    definitions = Definition.objects.all()
    existing_statuses = Tu.objects.values_list('status', flat=True).distinct().order_by('status')
    return render(request, 'root_service/mix_page.html', context = {'is_create_mode': True,
                                                                   'mix': None,
                                                                   'existing_categories': existing_categories, 'existing_groupnames': existing_groupnames,
                                                                   'existing_statuses': existing_statuses, 'definitions': definitions, 'compositions': None,
                                                                   'formset': None})

def mix_creation_page_save(request):
    if request.method == 'POST':
        xcode_mix = request.POST.get('xcode_mix')
        if not xcode_mix:
            return redirect('mix_create')
        form = MixForm(request.POST)
        if form.is_valid():
            mix_object = Mix()
            if form.cleaned_data.get('rus_definition'):
                mix_object.root_pd = Definition.objects.get_or_create(rus_definition=form.cleaned_data.get('rus_definition'))[0]
            else:
                mix_object.root_pd = Definition.objects.get(id=form.cleaned_data.get('root_pd'))
            mix_object.xcode_mix = form.cleaned_data.get('xcode_mix')
            mix_object.ean_mix = form.cleaned_data.get('ean_mix')
            mix_object.category = form.cleaned_data.get('category')
            mix_object.groupname = form.cleaned_data.get('groupname')
            mix_object.status = form.cleaned_data.get('status')
            mix_object.mix_in_box = form.cleaned_data.get('mix_in_box')
            mix_object.save()
            return redirect('show_mix', mix_id=mix_object.id)
        else:
            print(form.errors)
    return redirect('mix_create')

def mix_page_save(request, mix_id):
    mix_object = get_object_or_404(Mix, id=mix_id)
    active_list_object = Active_list.objects.filter(root_mix = mix_object).first()
    if request.method == 'POST':
        form = MixForm(request.POST)
        if form.is_valid():
            if form.cleaned_data.get('rus_definition'):
                mix_object.root_pd = Definition.objects.get_or_create(rus_definition=form.cleaned_data.get('rus_definition'))[0]
            elif form.cleaned_data.get('root_pd'):
                mix_object.root_pd = Definition.objects.get(id=form.cleaned_data.get('root_pd'))
            else:
                mix_object.root_pd = None
            mix_object.xcode_mix = form.cleaned_data.get('xcode_mix')
            mix_object.ean_mix = form.cleaned_data.get('ean_mix')
            mix_object.category = form.cleaned_data.get('category')
            mix_object.groupname = form.cleaned_data.get('groupname')
            mix_object.status = form.cleaned_data.get('status')
            mix_object.mix_in_box = form.cleaned_data.get('mix_in_box')
            mix_object.save()
            if form.cleaned_data['cons_active']:
                active_list_object = active_list_object if active_list_object else Active_list()
                active_list_object.root_mix = mix_object
                active_list_object.cons_active = True
                active_list_object.save()
            elif active_list_object:
                active_list_object.cons_active = False
                active_list_object.save()
    return redirect('show_mix', mix_id=mix_id)

def mix_page_save_compositions(request, mix_id):
    mix_object = get_object_or_404(Mix, id=mix_id)
    def clean_post_data(post):
        cleaned = {}
        for key, value in post.lists():
            if isinstance(value, list):
                cleaned[key] = next((v for v in reversed(value) if v != ''), '')
            else:
                cleaned[key] = value
        return cleaned
    if request.method == 'POST':
        post_data = clean_post_data(request.POST)
        MixComponentFormSet = inlineformset_factory(
            Mix, 
            MixComposition,
            form=MixCompositionForm,
            fields=('root_cu', 'quantity'),
            extra=1,
            can_delete=True
        )
        if not MixComposition.objects.filter(root_mix=mix_object).exists():
            post_data.update({
                'mixcomposition_set-INITIAL_FORMS': '0',
                'mixcomposition_set-TOTAL_FORMS': '1'  # Принудительно 1 форма
            })
        formset = MixComponentFormSet(post_data, instance=mix_object)
        if formset.is_valid():
            instances = []
            for form in formset:
                if not form.cleaned_data.get('DELETE', False) and form.cleaned_data.get('root_cu'):
                    instance = form.save(commit=False)
                    instance.root_mix = mix_object
                    instance.save()
                    instances.append(instance)
            for form in formset:
                if form.cleaned_data.get('DELETE', False) and form.instance.pk:
                    form.instance.delete()
            return redirect('show_mix', mix_id=mix_id)
        else:
            print("Formset errors:", formset.errors)
    return redirect('show_mix', mix_id=mix_id)
