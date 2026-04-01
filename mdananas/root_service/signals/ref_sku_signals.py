# signals.py
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from root_service.models.ref_sku_models import TuDimensions, CuDimensions, Tu, MixDimensions, MixComposition, Mix

@receiver(pre_save, sender=TuDimensions)
def calculate_tu_weight(sender, instance, **kwargs):
    """Автоматический расчет веса TU перед сохранением"""
    if instance.root_tu and instance.root_tu.root_cu:
        try:
            cu_dimensions = CuDimensions.objects.get(root_cu=instance.root_tu.root_cu)
            if cu_dimensions.net_weight is not None:
                instance.net_weight = cu_dimensions.net_weight * instance.root_tu.cu_in_tu / 1000
        except CuDimensions.DoesNotExist:
            pass
        except Exception as e:
            pass


@receiver(post_save, sender=CuDimensions)
def update_related_tu_dimensions(sender, instance, **kwargs):
    """Обновляем вес всех TU, связанных с измененным CU"""
    related_tus = Tu.objects.filter(root_cu=instance.root_cu)
    
    if not related_tus.exists():
        return
    
    for tu in related_tus:
        try:
            tu_dimensions, created = TuDimensions.objects.get_or_create(root_tu=tu)
            tu_dimensions.net_weight = (instance.net_weight or 0) * (tu.cu_in_tu or 0) / 1000
            tu_dimensions.save(update_fields=['net_weight'])
        except Exception as e:
            pass


@receiver(post_save, sender=Tu)
def update_tu_dimensions_on_tu_change(sender, instance, **kwargs):
    """Обновляем вес TU при изменении cu_in_tu или root_cu"""

    cu_in_tu_changed = hasattr(instance, '_original_cu_in_tu') and instance._original_cu_in_tu != instance.cu_in_tu
    root_cu_changed = hasattr(instance, '_original_root_cu') and instance._original_root_cu != instance.root_cu

    if not (cu_in_tu_changed or root_cu_changed):
        return  # Ничего не изменилось

    try:
        tu_dimensions = TuDimensions.objects.get_or_create(root_tu=instance)[0]
        
        # Если root_cu стал None или нет связанного CuDimensions, обнуляем вес
        if not instance.root_cu:
            tu_dimensions.net_weight = None
            tu_dimensions.save(update_fields=['net_weight'])
            return
        
        try:
            cu_dimensions = CuDimensions.objects.get(root_cu=instance.root_cu)
            
            if cu_dimensions.net_weight is not None:
                new_weight = cu_dimensions.net_weight * (instance.cu_in_tu or 0) / 1000
                tu_dimensions.net_weight = new_weight
                tu_dimensions.save(update_fields=['net_weight'])
            else:
                tu_dimensions.net_weight = None
                tu_dimensions.save(update_fields=['net_weight'])
                
        except CuDimensions.DoesNotExist:
            # Нет CuDimensions для нового root_cu, обнуляем вес
            tu_dimensions.net_weight = None
            tu_dimensions.save(update_fields=['net_weight'])
            
    except Exception as e:
        pass

# Дополнительный сигнал для отслеживания изменений cu_in_tu в Tu
@receiver(pre_save, sender=Tu)
def store_original_cu_in_tu(sender, instance, **kwargs):
    """Сохраняем оригинальное значение cu_in_tu для сравнения"""
    if instance.pk:
        try:
            original = Tu.objects.get(pk=instance.pk)
            instance._original_cu_in_tu = original.cu_in_tu
            instance._original_root_cu = original.root_cu
        except Tu.DoesNotExist:
            instance._original_cu_in_tu = None
            instance._original_root_cu = None
    else:
        instance._original_cu_in_tu = None
        instance._original_root_cu = None

@receiver(pre_save, sender=MixDimensions)
def calculate_mix_weight(sender, instance, **kwargs):
    """Автоматический расчет веса Mix перед сохранением"""
    if instance.root_mix:
        # Получаем все компоненты Mix
        compositions = MixComposition.objects.filter(root_mix=instance.root_mix)
        
        if not compositions.exists():
            instance.net_weight = None
            return
        
        total_weight = 0
        has_weight = False
        
        for comp in compositions:
            try:
                cu_dimensions = CuDimensions.objects.get(root_cu=comp.root_cu)
                if cu_dimensions.net_weight is not None and comp.quantity is not None:
                    total_weight += cu_dimensions.net_weight * comp.quantity
                    has_weight = True
            except CuDimensions.DoesNotExist:
                pass
            except Exception as e:
                pass
        
        instance.net_weight = total_weight if has_weight else None


@receiver(post_save, sender=MixComposition)
def update_related_mix_dimensions(sender, instance, **kwargs):
    """Обновляем вес Mix при изменении состава"""
    try:
        mix_dimensions, created = MixDimensions.objects.get_or_create(root_mix=instance.root_mix)
        
        # Пересчитываем вес
        compositions = MixComposition.objects.filter(root_mix=instance.root_mix)
        
        if not compositions.exists():
            mix_dimensions.net_weight = None
            mix_dimensions.save(update_fields=['net_weight'])
            return
        
        total_weight = 0
        has_weight = False
        
        for comp in compositions:
            try:
                cu_dimensions = CuDimensions.objects.get(root_cu=comp.root_cu)
                if cu_dimensions.net_weight is not None and comp.quantity is not None:
                    total_weight += cu_dimensions.net_weight * comp.quantity
                    has_weight = True
            except CuDimensions.DoesNotExist:
                pass
        
        mix_dimensions.net_weight = total_weight if has_weight else None
        mix_dimensions.save(update_fields=['net_weight'])
        
    except Exception as e:
        pass


@receiver(post_save, sender=CuDimensions)
def update_related_mix_on_cu_weight_change(sender, instance, **kwargs):
    """Обновляем вес всех Mix, связанных с измененным CU"""
    # Находим все MixComposition, где используется этот CU
    related_compositions = MixComposition.objects.filter(root_cu=instance.root_cu)
    
    if not related_compositions.exists():
        return
    
    # Обновляем каждый уникальный Mix
    updated_mixes = set()
    for comp in related_compositions:
        if comp.root_mix not in updated_mixes:
            updated_mixes.add(comp.root_mix)
            
            try:
                mix_dimensions, created = MixDimensions.objects.get_or_create(root_mix=comp.root_mix)
                
                # Пересчитываем вес для этого Mix
                compositions = MixComposition.objects.filter(root_mix=comp.root_mix)
                
                total_weight = 0
                has_weight = False
                
                for c in compositions:
                    try:
                        cu_dim = CuDimensions.objects.get(root_cu=c.root_cu)
                        if cu_dim.net_weight is not None and c.quantity is not None:
                            total_weight += cu_dim.net_weight * c.quantity
                            has_weight = True
                    except CuDimensions.DoesNotExist:
                        pass
                
                mix_dimensions.net_weight = total_weight if has_weight else None
                mix_dimensions.save(update_fields=['net_weight'])
                
            except Exception as e:
                pass


@receiver(pre_save, sender=MixComposition)
def store_original_mix_composition_values(sender, instance, **kwargs):
    """Сохраняем оригинальные значения MixComposition для сравнения"""
    if instance.pk:
        try:
            original = MixComposition.objects.get(pk=instance.pk)
            instance._original_root_cu = original.root_cu
            instance._original_quantity = original.quantity
        except MixComposition.DoesNotExist:
            instance._original_root_cu = None
            instance._original_quantity = None
    else:
        instance._original_root_cu = None
        instance._original_quantity = None


@receiver(post_save, sender=MixComposition)
def update_mix_dimensions_on_composition_change(sender, instance, **kwargs):
    """Обновляем вес Mix при изменении quantity или root_cu в составе"""
    
    quantity_changed = hasattr(instance, '_original_quantity') and instance._original_quantity != instance.quantity
    root_cu_changed = hasattr(instance, '_original_root_cu') and instance._original_root_cu != instance.root_cu
    
    if not (quantity_changed or root_cu_changed):
        return
    
    try:
        mix_dimensions, created = MixDimensions.objects.get_or_create(root_mix=instance.root_mix)
        
        # Если изменился root_cu и старый CU использовался только в этом составе,
        # то старый Mix уже будет обновлен через сигнал update_related_mix_on_cu_weight_change
        # Но нам нужно обновить текущий Mix
        
        compositions = MixComposition.objects.filter(root_mix=instance.root_mix)
        
        if not compositions.exists():
            mix_dimensions.net_weight = None
            mix_dimensions.save(update_fields=['net_weight'])
            return
        
        total_weight = 0
        has_weight = False
        
        for comp in compositions:
            try:
                cu_dimensions = CuDimensions.objects.get(root_cu=comp.root_cu)
                if cu_dimensions.net_weight is not None and comp.quantity is not None:
                    total_weight += cu_dimensions.net_weight * comp.quantity
                    has_weight = True
            except CuDimensions.DoesNotExist:
                pass
        
        mix_dimensions.net_weight = total_weight if has_weight else None
        mix_dimensions.save(update_fields=['net_weight'])
        
    except Exception as e:
        pass


@receiver(post_delete, sender=MixComposition)
def update_mix_dimensions_on_composition_delete(sender, instance, **kwargs):
    """Обновляем вес Mix при удалении компонента"""
    try:
        mix_dimensions, created = MixDimensions.objects.get_or_create(root_mix=instance.root_mix)
        
        compositions = MixComposition.objects.filter(root_mix=instance.root_mix)
        
        if not compositions.exists():
            mix_dimensions.net_weight = None
            mix_dimensions.save(update_fields=['net_weight'])
            return
        
        total_weight = 0
        has_weight = False
        
        for comp in compositions:
            try:
                cu_dimensions = CuDimensions.objects.get(root_cu=comp.root_cu)
                if cu_dimensions.net_weight is not None and comp.quantity is not None:
                    total_weight += cu_dimensions.net_weight * comp.quantity
                    has_weight = True
            except CuDimensions.DoesNotExist:
                pass
        
        mix_dimensions.net_weight = total_weight if has_weight else None
        mix_dimensions.save(update_fields=['net_weight'])
        
    except Exception as e:
        pass