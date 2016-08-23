from django.contrib import admin
from .models import Company, Profile, Picklist, Entity, ValidationGroup, ValidationGroupRule, Validation

# Register your models here.

admin.site.register(Company)
admin.site.register(Profile)
admin.site.register(Picklist)
admin.site.register(Entity)
admin.site.register(ValidationGroup)
admin.site.register(ValidationGroupRule)
admin.site.register(Validation)
