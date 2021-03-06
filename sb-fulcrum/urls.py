from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.models import User, Permission, Group
from blog.models import Blogpost, Tags
from blog.handlers import CustomHandler
import fulcrum

admin.autodiscover()

urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),
    (r'^srv/', include(fulcrum.site.urls)),
    url(r'^js$', 'blog.views.test_js'),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_URL}),
    )

auth = fulcrum.authentication.HttpBasicAuthentication(realm="My realm")
fulcrum.site.register(Blogpost, authentication=auth, group="My Group")
fulcrum.site.register(Tags, authentication=auth, group="My Group")
fulcrum.site.register(User, authentication=auth)
fulcrum.site.register_arbitrary(CustomHandler, 'CustomArbitraryResource', authentication=auth, group="Arbitrary Resources")
fulcrum.site.register(Permission, authentication=auth)
fulcrum.site.register(Group, authentication=auth)