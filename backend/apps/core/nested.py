from django.shortcuts import get_object_or_404
from .api import ResourceViewSet

class NestedResource(ResourceViewSet):
    parent_model=None
    parent_field=''
    def get_queryset(self):
        qs=super().get_queryset()
        get_object_or_404(self.parent_model.objects,pk=self.kwargs['parent_id'])
        return qs.filter(**{self.parent_field+'_id':self.kwargs['parent_id']})
    def get_serializer(self,*args,**kwargs):
        if 'data' in kwargs:
            data=kwargs['data'].copy();data[self.parent_field]=self.kwargs['parent_id'];kwargs['data']=data
        return super().get_serializer(*args,**kwargs)
