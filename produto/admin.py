from django.contrib import admin
from .forms import VariacaoObrigatoria
from . import models
from django.utils.html import format_html
from .models import Produto, Category, SubCategory, Contato, Postagem, Comentario,Cor


class CorInline(admin.TabularInline):
    model = Cor
    extra = 1  
    min_num = 0  # Agora a cor não é obrigatória
    fields = ['codigo_hex', 'imagem']
    can_delete = True  


class VariacaoInline(admin.TabularInline):
    model = models.Variacao
    formset = VariacaoObrigatoria
    min_num = 1
    extra = 0
    can_delete = True


class ProdutoAdmin(admin.ModelAdmin):
    list_display = [
        'nome', 
        'descricao_curta', 
        'get_preco_formatado', 
        'get_preco_promocional_formatado', 
        'tipo', 
        'category', 
        'slug'
    ]
    search_fields = ['nome', 'slug']
    list_filter = ['tipo', 'category']
    prepopulated_fields = {'slug': ('nome',)}
    ordering = ['nome']
    inlines = [VariacaoInline, CorInline]  # Adiciona o inline para cores aqui

    def get_preco_formatado(self, obj):
        return obj.get_preco_formatado()
    get_preco_formatado.short_description = 'Preço'

    def get_preco_promocional_formatado(self, obj):
        return obj.get_preco_promocional_formatado()
    get_preco_promocional_formatado.short_description = 'Preço Promo.'


class SubCategoryInline(admin.TabularInline):
    model = SubCategory
    extra = 1  

class CategoryAdmin(admin.ModelAdmin):
    inlines = [SubCategoryInline]


@admin.register(Postagem)
class PostagemAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'autor', 'categoria', 'data_criacao', 'quantidade_comentarios')
    list_filter = ('categoria', 'data_criacao', 'autor')
    search_fields = ('titulo', 'conteudo')
    prepopulated_fields = {'slug': ('titulo',)}
    date_hierarchy = 'data_criacao'


@admin.register(Cor)
class CorAdmin(admin.ModelAdmin):
    list_display = ['produto', 'codigo_hex', 'imagem']
    search_fields = ['produto__nome']
    list_filter = ['produto']



admin.site.register(models.Produto, ProdutoAdmin)
admin.site.register(models.Variacao)
admin.site.register(Category, CategoryAdmin)
admin.site.register(SubCategory)
admin.site.register(Contato)
