from django.conf import settings
from PIL import Image
from django.db import models
from django.utils.text import slugify
from utils import utils
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.urls import reverse
import os
from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFit  # Mudamos para ResizeToFit



class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'

    def __str__(self):
        return self.name
    
    
class SubCategory(models.Model):
    name = models.CharField(max_length=50)
    category = models.ForeignKey(
        Category, 
        on_delete=models.CASCADE, 
        related_name="subcategories"
    )

    class Meta:
        verbose_name = 'Subcategoria'
        verbose_name_plural = 'Subcategorias'

    def __str__(self):
        return f"{self.category.name} -> {self.name}"

    

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
        verbose_name_plural = 'Blog'
        
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
    imagem = ProcessedImageField(
        upload_to='produtos/',  # Alterado para pasta específica
        processors=[ResizeToFit(width=800, upscale=False)],
        format='JPEG',
        options={'quality': 85},
        blank=True,
        null=True
    )
    slug = models.SlugField(unique=True, blank=True, null=True)
    preco_marketing = models.FloatField(verbose_name='Preço')
    preco_marketing_promocional = models.FloatField(default=0, verbose_name='Preço Promo.')
    tipo = models.CharField(
        default='V',
        max_length=1,
        choices=(('V', 'Variável'), ('S', 'Simples'),)
    )
    category = models.ForeignKey(
        'Category',
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )
    subcategory = models.ForeignKey(
        SubCategory,
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )
    visivel = models.BooleanField(default=True)

    def get_preco_formatado(self):
        return utils.formata_preco(self.preco_marketing)
    get_preco_formatado.short_description = 'Preço'

    def get_preco_promocional_formatado(self):
        return utils.formata_preco(self.preco_marketing_promocional)
    get_preco_promocional_formatado.short_description = 'Preço Promo.'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nome)
        super().save(*args, **kwargs)
        # Removido o resize_image manual, pois ProcessedImageField já faz isso

    def __str__(self):
        return self.nome
    
    class Meta:
        verbose_name = 'Produtos'
        verbose_name_plural = 'Produtos da Loja'


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
        

class Contato(models.Model):
    MOTIVO_CHOICES = [
        ('reclamacao', 'Reclamação'),
        ('elogio', 'Elogio'),
        ('sugestao', 'Sugestão'),
        ('duvida', 'Dúvida'),
        ('outro', 'Outro'),
    ]

    nome = models.CharField(max_length=100)
    email = models.EmailField()
    motivo = models.CharField(max_length=20, choices=MOTIVO_CHOICES)
    mensagem = models.TextField()
    data_envio = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nome} - {self.get_motivo_display()}"

    class Meta:
        verbose_name = 'Contato'
        verbose_name_plural = 'Feedback dos Clientes'

