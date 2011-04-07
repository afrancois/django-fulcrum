import os
from django import http
from django.db import models
from django.shortcuts import render_to_response
from django.utils.functional import update_wrapper
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache
from fulcrum.datastructures import EasyModel
from fulcrum.authentication import NoAuthentication
from fulcrum.handler import DefaultHandler, DefaultAnonymousHandler
from fulcrum.resource import Resource
from exceptions import Exception, KeyError


class AlreadyRegistered(Exception):
    pass

class NotRegistered(Exception):
    pass

class FulcrumSite(object):
    """
    Default fulcrum site.
    """
    
    def __init__(self, name=None, app_name='fulcrum', authentication=None):
        if name is None: self.name = 'fulcrum'
        else: self.name = name
        self.app_name = app_name
        self.registry = {}
        self.authentication = authentication or NoAuthentication() # default authentication for all resources
    
    
    def has_permission(self, request):
        """
        Returns True if the given HttpRequest has permission to view
        *at least one* page in the admin site.
        """
        #TODO: implement permissions check
        return True
    
    
    def register(self, model, handler_class=None, name=None, authentication=None, **options):
        """
        Register a resource.
        """
        if handler_class:
            handler = handler_class()
        else:
            if authentication:
                handler = DefaultHandler(model)
            else:
                handler = DefaultAnonymousHandler(model)
        authentication = authentication or self.authentication
        resource = Resource(handler, self, name, authentication)
        
        if resource.name in self.registry:
            raise AlreadyRegistered('The resource {0} is already registered'.format(resource.name))
        self.registry[resource.name] = resource
    
        
    def unregister(self, resource):
        """
        Unregister a resource.
        """
        
        if resource.name not in self.registry:
            raise NotRegistered('The resource {0} has not been registered'.format(resource.name))
        del self.registry[resource.name]
    
    
    def get_resource_list(self):
        return self.registry.keys()
    
    def get_resource_by_model(self, model):
        """
        Get a resource by model.
        """
        for k, v in self.registry.items():
            if model == v.model:
                return v
        return None
    
    
    def fulcrum_view(self, view, cacheable=False):
        """
        Decorator to create a fulcrum view attached to this ``FulcrumSite``. This
        wraps the view and provides permission checking by calling
        ``self.has_permission``.
        
        By default, fulcrum_views are marked non-cacheable using the
        ``never_cache`` decorator. If the view can be safely cached, set
        cacheable=True.
        """
        
        def inner(request, *args, **kwargs):
            if not self.has_permission(request):
                return self.login(request)
            return view(request, *args, **kwargs)
        if not cacheable:
            inner = never_cache(inner)
        # We add csrf_protect here so this function can be used as a utility
        # function for any view, without having to repeat 'csrf_protect'.
        if not getattr(view, 'csrf_exempt', False):
            inner = csrf_protect(inner)
        return update_wrapper(inner, view)
    
    
    def get_urls(self):
        from django.conf.urls.defaults import patterns, url, include

        def wrap(view, cacheable=False):
            def wrapper(*args, **kwargs):
                return self.fulcrum_view(view, cacheable)(*args, **kwargs)
            return update_wrapper(wrapper, view)
            
        urlpatterns = patterns('',
            url(r'^$', # root
                wrap(self.index),
                #self.index,
                name='fulcrum_index'),
            
            url(r'^(?P<resource_name>\w+)/$', # ex: resource_name
                wrap(self.resource_data_format),
                #self.resource_data_format,
                name='fulcrum_resource_data_format'),
            
            url(r'^(?P<resource_name>\w+)\.(?P<format>\w+)$', # ex: resource_name.json
                wrap(self.resource_data_format),
                #self.resource_data_format,
                name='fulcrum_resource_data_format'),
            
            url(r'^(?P<resource_name>\w+)/api/$', # ex: resource_name/api
                wrap(self.resource_api),
                #self.resource_api,
                name='fulcrum_resource_api'),
            
            url(r'^(?P<resource_name>\w+)/schema\.(?P<format>\w+)$', # ex: resource_name/schema.json
                wrap(self.resource_schema),
                #self.resource_schema,
                name='fulcrum_resource_schema'),
            
            url(r'^(?P<resource_name>\w+)/(?P<primary_key>\w+)/$', # ex: resource_name/1
                wrap(self.object_data_format),
                #self.object_data_format,
                name='fulcrum_object_data_format'),
            
            url(r'^(?P<resource_name>\w+)/(?P<primary_key>\w+)\.(?P<format>\w+)$', # ex: resource_name/1.json
                wrap(self.object_data_format),
                #self.object_data_format,
                name='fulcrum_object_data_format'),
        )
        
        return urlpatterns
    
    
    def urls(self):
        return self.get_urls(), self.app_name, self.name
    urls = property(urls)
    
    
    def index(self, request):
        """
        Renders index page view for fulcrum. Lists all registered resources.
        """
        
        print 'index()'
        
        r_list = [ self.registry[key] for key in self.registry.keys() ]
        return render_to_response('fulcrum/homepage.html', { 'resource_list': r_list })
        
    
    def login(self, request):
        return http.HttpResponse('login')
    
        
    def resource_data_format(self, request, resource_name, format='html', *args, **kwargs):
        """
        Resource data
        """
        
        print 'resource_data_format()'
        print '-- user: {0}'.format(request.user)
        
        try:
            resource = self.registry[resource_name]
        except KeyError:
            raise http.Http404("This resource has not been registered with fulcrum.")
        
        if format == 'htmlsss':
            return render_to_response('fulcrum/resource_detail.html', { 'resource': resource })
        else:
            return resource(request, emitter_format=format)
    
    
    def resource_api(self, request, resource_name, *args, **kwargs):
        """
        Resource API handler
        """
        
        print 'resource_api()'
        
        try:
            resource = self.registry[resource_name]
        except KeyError:
            raise http.Http404("This resource has not been registered with fulcrum.")
        
        schema_urls = resource.schema_urls()
        request_example = resource.get_request_example('json')
        response_example = resource.get_response_example('json')
        
        return render_to_response('fulcrum/resource_api.html', {
                'resource': resource,
                'schema_urls': schema_urls,
                'request_example': request_example,
                'response_example': response_example,
            })
    
        
    def resource_schema(self, request, resource_name, format, *args, **kwargs):
        """
        Resource schema handler
        """
        
        print 'resource_schema()'
        
        try:
            resource = self.registry[resource_name]
        except KeyError:
            raise http.Http404("This resource has not been registered with fulcrum.")
        
        return resource.get_schema_view(format)
        
    
    def object_data_format(self, request, resource_name, primary_key, format='html', *args, **kwargs):
        """
        Object data
        """
        
        print 'object_data_format()'
        
        try:
            resource = self.registry[resource_name]
        except KeyError:
            raise http.Http404("This resource has not been registered with fulcrum.")
        
        if format == 'html':
            try:
                object = resource.object_by_pk(primary_key)
            except:
                return http.HttpResponse('No object with primary key {0} could be found.'.format(primary_key))
            return render_to_response('fulcrum/object_detail.html', { 'object': object })
        else:
            return resource(request, pk=primary_key, emitter_format=format)
            
# Create Fulcrum instance        
site = FulcrumSite()
