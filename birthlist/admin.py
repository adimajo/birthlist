from django.contrib import admin

from birthlist.models import Cadeau


@admin.register(Cadeau)
class CadeauAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "description")
    search_fields = ("name", "description")
    filter_horizontal = ("interested_families", "bought_by")
