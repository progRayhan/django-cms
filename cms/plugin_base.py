from cms.models import CMSPlugin
from cms.exceptions import SubClassNeededError
from django.forms.models import ModelForm
from django.utils.encoding import smart_str
from django.contrib import admin
from cms import settings as cms_settings
 
class CMSPluginBase(admin.ModelAdmin):
    name = ""
    form = None
    
    change_form_template = "admin/cms/page/plugin_change_form.html"
    admin_preview = True #Should the plugin be rendered in the admin?
    
    render_template = None
    model = CMSPlugin
    opts = {}
    placeholders = None # a tupple with placeholder names this plugin can be placed. All if empty
    text_enabled = False
    
    def __init__(self, model=None,  admin_site=None):
        if self.model:
            if not CMSPlugin in self.model._meta.parents and self.model != CMSPlugin:
                raise SubClassNeededError, "plugin model needs to subclass CMSPlugin"
            if not self.form:
                class DefaultModelForm(ModelForm):
                    class Meta:
                        model = self.model
                        exclude = ('page', 'position', 'placeholder', 'language', 'plugin_type')
                self.form = DefaultModelForm
        
            # Move 'advanced' fields into separate fieldset.
            # Currently disabled if fieldsets already set, though
            # could simply append an additional 'advanced' fieldset -- 
            # but then the plugin can't customise the advanced fields
            if not self.__class__.fieldsets:
                basic_fields = []
                advanced_fields = []
                for f in self.model._meta.fields:
                    if not f.auto_created and f.editable:
                        if hasattr(f,'advanced'): 
                            advanced_fields.append(f.name)
                        else: basic_fields.append(f.name)
                if advanced_fields: # leave well enough alone otherwise
                    self.__class__.fieldsets = (
                        (None, { 'fields' : basic_fields}),
                        (_('Advanced options'), 
                         {'fields' : advanced_fields, 
                          'classes' : ('collapse',)})
                        )

        if admin_site:
            super(CMSPluginBase, self).__init__(self.model, admin_site)
        
        self.object_successfully_changed = False
        
        # variables will be overriden in edit_view, so we got requred
        self.cms_plugin_instance = None
        self.placeholder = None
    
    
    def render(self, context, placeholder):
        raise NotImplementedError, "render needs to be implemented"
    
    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        """
        We just need the popup interface here
        """
        context.update({
            'is_popup': True,
            'plugin': self.cms_plugin_instance,
            'CMS_MEDIA_URL': cms_settings.CMS_MEDIA_URL,
        })
        
        return super(CMSPluginBase, self).render_change_form(request, context, add, change, form_url, obj)
    
    def has_add_permission(self, request, *args, **kwargs):
        """Permission handling change - if user is allowed to change the page
        he must be also allowed to add/change/delete plugins..
        
        Not sure if there will be plugin permission requirement in future, but
        if, then this must be changed.
        """
        return self.cms_plugin_instance.page.has_change_permission(request)
    has_delete_permission = has_change_permission = has_add_permission
    
    def save_model(self, request, obj, form, change):
        """
        Override original method, and add some attributes to obj
        This have to be made, because if object is newly created, he must know
        where he belives.
        Attributes from cms_plugin_instance have to be assigned to object, if
        is cms_plugin_instance attribute available.
        """
        
        if getattr(self, "cms_plugin_instance"):
            # assign stuff to object
            fields = self.cms_plugin_instance._meta.fields
            for field in fields:
                # assign all the fields - we can do this, because object is
                # subclassing cms_plugin_instance (one to one relation)
                value = getattr(self.cms_plugin_instance, field.name)
                setattr(obj, field.name, value)
        
        # remember the saved object
        self.saved_object = obj
        
        return super(CMSPluginBase, self).save_model(request, obj, form, change)
    
    def response_change(self, request, obj):
        """
        Just set a flag, so we know something was changed, and can make
        new version if reversion installed.
        New version will be created in admin.views.edit_plugin
        """
        self.object_successfully_changed = True
        return super(CMSPluginBase, self).response_change(request, obj)
    
    def response_add(self, request, obj):
        """
        Just set a flag, so we know something was changed, and can make
        new version if reversion installed.
        New version will be created in admin.views.edit_plugin
        """
        self.object_successfully_changed = True
        return super(CMSPluginBase, self).response_add(request, obj)

    def log_addition(self, request, object):
        pass

    def log_change(self, request, object, message):
        pass

    def log_deletion(self, request, object, object_repr):
        pass
                
    def icon_src(self, instance):
        """
        Overwrite this if text_enabled = True
 
        Return the URL for an image to be used for an icon for this
        plugin instance in a text editor.
        """
        return ""
 
    def icon_alt(self, instance):
        """
        Overwrite this if necessary if text_enabled = True
        Return the 'alt' text to be used for an icon representing
        the plugin object in a text editor.
        """
        return "%s - %s" % (unicode(self.name), unicode(instance))
    
    def __repr__(self):
        return smart_str(self.name)
    
    def __unicode__(self):
        return self.name
