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
        verbose_name_plural = 'Categorias de Calçados'

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
        verbose_name_plural = 'Marcas'

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


class Cor(models.Model):
    CORES_CHOICES = [
        ("#FFFFFF", "Branco"),  # Adicionando Branco
        ("#000000", "Preto"),   # Preto
        ("#FF0000", "Vermelho"), # Vermelho
        ("#0000FF", "Azul"),    # Azul
        ("#008000", "Verde"),   # Verde
        ("#FFFF00", "Amarelo"), # Amarelo
        ("#FFA500", "Laranja"),
        ("#800080", "Roxo"),
        ("#A52A2A", "Marrom"),
        ("#C0C0C0", "Cinza"),
        ("#FFC0CB", "Rosa"),
        ("#FFD700", "Dourado"),
        ("#00FFFF", "Ciano"),
        ("#808080", "Grafite"),
        ("#8B4513", "Marrom Escuro"),
        ("#FF4500", "Vermelho Alaranjado"),
        ("#4B0082", "Índigo"),
        ("#00FF00", "Verde Limão"),
        ("#FF1493", "Rosa Choque"),
        ("#000080", "Azul Marinho"),
        ("#B22222", "Vermelho Tijolo"),
        ("#2E8B57", "Verde Musgo"),
        ("#4682B4", "Azul Aço"),
        ("#D2691E", "Chocolate"),
        ("#BC8F8F", "Rosa Antigo"),
        ("#1E90FF", "Azul Céu"),
        ("#FF6347", "Tomate"),
        ("#556B2F", "Verde Militar"),
        ("#FA8072", "Salmão"),
        ("#DAA520", "Mostarda"),
        ("#F5F5DC", "Bege"),
        ("#696969", "Cinza Escuro"),
        ("#483D8B", "Azul Royal"),
        ("#E6E6FA", "Lavanda"),
        ("#FFDAB9", "Pêssego"),
        ("#CD853F", "Camurça"),
        ("#191970", "Azul Meia-noite"),
        ("#8B0000", "Vermelho Escuro"),
        ("#F4A460", "Sépia"),
    ]

    produto = models.ForeignKey('Produto', on_delete=models.CASCADE, related_name='cores')
    codigo_hex = models.CharField(
        max_length=7, 
        choices=CORES_CHOICES,  # Agora só aceita as opções predefinidas
        verbose_name="Código Hex da Cor"
    )
    imagem = models.ImageField(upload_to='cores/', blank=True, null=True, verbose_name="Imagem da Cor")

    def __str__(self):
        return f"{self.produto.nome} - {self.get_codigo_hex_display()}"  # Exibe o nome da cor no admin


class Produto(models.Model):
    nome = models.CharField(max_length=255)
    descricao_curta = models.TextField(max_length=255)
    descricao_longa = models.TextField()
    #add
    cor_padrao_nome = models.CharField(max_length=50, default="Padrão", verbose_name="Nome da Cor Padrão")
    cor_padrao_codigo_hex = models.CharField(
        max_length=7, 
        choices=Cor.CORES_CHOICES,
        default="#000000",
        verbose_name="Código Hex da Cor Padrão"
    )
    imagem = ProcessedImageField(
        upload_to='produtos/',
        processors=[ResizeToFit(width=800, upscale=False)],
        format='JPEG',
        options={'quality': 85},
        verbose_name="Imagem da cor padrão",
        help_text="Esta imagem será usada para a cor padrão do produto"
    )
    cor_padrao = models.ForeignKey(
        'Cor',
        on_delete=models.SET_NULL,
        related_name='produtos_padrao',
        blank=True,
        null=True,
        verbose_name="Cor Padrão"
    )
    
    # Outros campos existentes...
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
    # No modelo Produto (produto/models.py)
    def get_cores(self):
        """Retorna todas as cores disponíveis para este produto."""
        return self.cores.all()

    def get_preco_formatado(self):
        return utils.formata_preco(self.preco_marketing)
    get_preco_formatado.short_description = 'Preço'

    def get_preco_promocional_formatado(self):
        return utils.formata_preco(self.preco_marketing_promocional)
    get_preco_promocional_formatado.short_description = 'Preço Promo.'

    #Add
    def set_cor_padrao(self, cor_id):
        """Define a cor padrão para o produto."""
        try:
            cor = Cor.objects.get(id=cor_id, produto=self)
            self.cor_padrao = cor
            self.save()
            return True
        except Cor.DoesNotExist:
            return False
    
    def get_cor_padrao(self):
        """Retorna a cor padrão ou a primeira cor disponível."""
        if self.cor_padrao:
            return self.cor_padrao
        
        # Se não tiver cor padrão definida, tenta usar a primeira cor disponível
        primeiro_cor = self.cores.first()
        if primeiro_cor:
            self.cor_padrao = primeiro_cor
            self.save()
            return primeiro_cor
        
        return None
    
    def tem_cores(self):
        """Verifica se o produto tem cores disponíveis."""
        return self.cores.exists()

    def save(self, *args, **kwargs):
        # Garantir que o slug seja criado
        if not self.slug:
            self.slug = slugify(self.nome)
        
        # Salvar o produto primeiro para ter um ID
        super().save(*args, **kwargs)
        
        # Criar automaticamente a cor padrão como uma entrada no modelo Cor
        # se não existir e o produto já for salvo
        if not self.cor_padrao and self.id:
            cor = Cor.objects.create(
                produto=self,
                codigo_hex=self.cor_padrao_codigo_hex,
                imagem=self.imagem  # Usar a mesma imagem
            )
            self.cor_padrao = cor
            # Salvar novamente sem acionar o save recursivamente
            Produto.objects.filter(id=self.id).update(cor_padrao=cor)
    
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
    estoque = models.PositiveIntegerField(default=10000)

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

