from django.conf import settings
import os
from PIL import Image
from django.db import models
from django.utils.text import slugify
from utils import utils
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse


class Category(models.Model):
    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'

    name = models.CharField(max_length=50)

    def __str__(self) -> str:
        return self.name
    


class Postagem(models.Model):
    titulo = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    conteudo = models.TextField()
    imagem_destaque = models.ImageField(upload_to='blog_imagens/')
    data_criacao = models.DateTimeField(default=timezone.now)
    autor = models.ForeignKey(User, on_delete=models.CASCADE)
    categoria = models.ForeignKey('Category', on_delete=models.CASCADE)  # usando sua Category existente
    quantidade_comentarios = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = 'Postagem'
        verbose_name_plural = 'Postagens'
    
    def __str__(self):
        return self.titulo
    
    def get_absolute_url(self):
        return reverse('blog:detalhes_post', kwargs={'slug': self.slug})

class Comentario(models.Model):
    postagem = models.ForeignKey(Postagem, on_delete=models.CASCADE, related_name='comentarios')
    autor = models.ForeignKey(User, on_delete=models.CASCADE)
    conteudo = models.TextField()
    data_criacao = models.DateTimeField(default=timezone.now)
    
    class Meta:
        verbose_name = 'Comentário'
        verbose_name_plural = 'Comentários'
    
    def __str__(self):
        return f'Comentário de {self.autor} em {self.postagem}'
    

    

class Produto(models.Model):
    nome = models.CharField(max_length=255)
    descricao_curta = models.TextField(max_length=255)
    descricao_longa = models.TextField()
    imagem = models.ImageField(upload_to='produtos/', blank=True, null=True)
    slug = models.SlugField(unique=True, blank=True, null=True)
    preco_marketing = models.FloatField(verbose_name='Preço')
    preco_marketing_promocional = models.FloatField(default=0, verbose_name='Preço Promo.')
    tipo = models.CharField(default='V', max_length=1, choices=(('V', 'Variável'), ('S', 'Simples'),))
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, blank=True, null=True)
    visivel = models.BooleanField(default=True, verbose_name="Visível na tela de vendas")


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        return context

    def get_preco_formatado(self):
        return utils.formata_preco(self.preco_marketing)
    get_preco_formatado.short_description = 'Preço'

    def get_preco_promocional_formatado(self):
        return utils.formata_preco(self.preco_marketing_promocional)
    get_preco_promocional_formatado.short_description = 'Preço Promo.'

    @staticmethod
    def resize_image(img, new_width=800):
        img_full_path = os.path.join(settings.MEDIA_ROOT, img.name)
        img_pil = Image.open(img_full_path)
        original_width, original_height = img_pil.size

        if original_width <= new_width:
            img_pil.close()
            return

        new_height = round((new_width * original_height) / original_width)
        new_img = img_pil.resize((new_width, new_height), Image.LANCZOS)
        new_img.save(img_full_path, optimize=True, quality=50)
        img_pil.close()

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nome)

        super().save(*args, **kwargs)

        max_image_size = 800

        if self.imagem:
            self.resize_image(self.imagem, max_image_size)

    def __str__(self):
        return self.nome



class Variacao(models.Model):
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    nome = models.CharField(max_length=50, blank=True, null=True)
    preco = models.FloatField()
    preco_promocional = models.FloatField(default=0)
    estoque = models.PositiveIntegerField(default=1)

    def __str__(self):
        return self.nome or self.produto.nome

    class Meta:
        verbose_name = 'Variação'
        verbose_name_plural = 'Variações'
        

