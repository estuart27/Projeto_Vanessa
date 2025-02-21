from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.views.generic import ListView, DetailView, View
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.db.models import Q, Count
from .models import Produto, Category, Postagem,Variacao
from perfil.models import Perfil
from .forms import ContatoForm, FormularioComentario

import mercadopago
import json
from django.conf import settings
from django.core.mail import send_mail


def about(request):
    return render(
        request,
        'produto/about.html',
    )

def index(request):
    # Obtém apenas os 4 primeiros produtos
    # queryset = Produto.objects.all()[:4]
    queryset = Produto.objects.order_by('?')[:4]

    # Obtém todas as categorias
    categories = Category.objects.prefetch_related('subcategories').all()

    # Calcula o desconto para cada produto
    produtos_com_desconto = []
    for produto in queryset:
        if produto.preco_marketing_promocional:
            desconto = ((produto.preco_marketing - produto.preco_marketing_promocional) / produto.preco_marketing) * 100
            desconto = int(round(desconto, 0))
        else:
            desconto = 0

        produtos_com_desconto.append({
            'produto': produto,
            'desconto': desconto,
        })

    # Passa os dados para o template
    context = {
        'produtos': queryset,
        'categories': categories,
        'produtos_com_desconto': produtos_com_desconto,
    }

    return render(request, 'produto/index.html', context)


class ListaPostagensView(ListView):
    model = Postagem
    template_name = 'produto/blog.html'
    context_object_name = 'postagens'
    paginate_by = 10

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['categorias'] = Category.objects.annotate(
            contagem_posts=Count('postagem')
        )
        contexto['posts_recentes'] = Postagem.objects.order_by('-data_criacao')[:3]
        return contexto

class DetalhesPostagemView(DetailView):
    model = Postagem
    template_name = 'produto/blog-single.html'
    context_object_name = 'postagem'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['posts_recentes'] = Postagem.objects.exclude(
            id=self.object.id
        ).order_by('-data_criacao')[:3]
        contexto['categorias'] = Category.objects.annotate(
            contagem_posts=Count('postagem')
        )
        return contexto

def troca(request):
    return render(
        request,
        'produto/Troca.html',
    )

def termos(request):
    return render(
        request,
        'produto/Termos.html',
    )

def politica(request):
    return render(
        request,
        'produto/Politica.html',
    )


def checkout(request):
    return render(
        request,
        'produto/checkout.html',
    )


def contact(request):
    if request.method == 'POST':
        form = ContatoForm(request.POST)
        if form.is_valid():
            form.save()
            send_mail(
                subject='Nova Avaliação Recebida - Vivan Calçados',
                message=(
                    'Olá,\n\n'
                    'Sua loja, Vivan Calçados, acaba de receber uma nova avaliação de um cliente! '
                    'Confira o feedback acessando o painel de administração do site.\n\n'
                    'Se precisar de mais informações, entre em contato com o suporte.\n\n'
                    'Atenciosamente,\n'
                    'Equipe Vivan Calçados'
                ),
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[settings.DEFAULT_FROM_EMAIL]
            )
            messages.success(request, 'Mensagem enviada com sucesso!')
            return redirect('produto:contact')
    else:
        form = ContatoForm()
    return render(request, 'produto/contact.html',{'form': form})  # Corrigindo o nome do arquivo


class ListaPostagensView(ListView):
    model = Postagem
    template_name = 'produto/blog.html'
    context_object_name = 'postagens'
    paginate_by = 10

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['categorias'] = Category.objects.annotate(
            contagem_posts=Count('postagem')
        )
        contexto['posts_recentes'] = Postagem.objects.order_by('-data_criacao')[:3]
        return contexto

class DetalhesPostagemView(DetailView):
    model = Postagem
    template_name = 'produto/blog-single.html'
    context_object_name = 'postagem'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['posts_recentes'] = Postagem.objects.exclude(
            id=self.object.id
        ).order_by('-data_criacao')[:3]
        contexto['categorias'] = Category.objects.annotate(
            contagem_posts=Count('postagem')
        )
        return contexto


def adicionar_comentario(request, slug):
    postagem = get_object_or_404(Postagem, slug=slug)

    if request.method == "POST":
        form = FormularioComentario(request.POST)
        if form.is_valid():
            comentario = form.save(commit=False)
            comentario.autor = request.user
            comentario.postagem = postagem
            comentario.save()
            messages.success(request, "Comentário adicionado com sucesso!")
            return redirect('produto:detalhes_post', slug=postagem.slug)
    else:
        form = FormularioComentario()

    return redirect('produto:detalhes_post', slug=postagem.slug)


from django.views.generic import ListView
from .models import Produto, Category, SubCategory

class ListaProdutos(ListView):
    model = Produto
    template_name = 'produto/shop.html'
    context_object_name = 'produtos'
    paginate_by = 17
    ordering = ['-id']

    def get_queryset(self):
        queryset = Produto.objects.all()

        # Filtra por categoria, se houver
        category_id = self.request.GET.get('category')
        subcategory_id = self.request.GET.get('subcategory')

        # Filtra por categoria
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # Filtra por subcategoria, se houver
        if subcategory_id:
            queryset = queryset.filter(subcategory_id=subcategory_id)

        return queryset.order_by(*self.ordering)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Adiciona as categorias ao contexto
        context['categories'] = Category.objects.prefetch_related('subcategories').all()

        # Adiciona a categoria e subcategoria selecionadas ao contexto
        context['selected_category'] = self.request.GET.get('category')
        context['selected_subcategory'] = self.request.GET.get('subcategory')

        # Calcula o desconto para cada produto
        produtos_com_desconto = []
        for produto in context['produtos']:
            if produto.preco_marketing_promocional:
                desconto = ((produto.preco_marketing - produto.preco_marketing_promocional) / produto.preco_marketing) * 100
                desconto = int(round(desconto, 0))
            else:
                desconto = 0

            produtos_com_desconto.append({
                'produto': produto,
                'desconto': desconto,
            })

        context['produtos_com_desconto'] = produtos_com_desconto
        return context


class Busca(ListaProdutos):
    def get_queryset(self, *args, **kwargs):
        termo = self.request.GET.get('termo') or self.request.session['termo']
        qs = super().get_queryset(*args, **kwargs)

        if not termo:
            return qs

        self.request.session['termo'] = termo

        qs = qs.filter(
            Q(nome__icontains=termo) |
            Q(descricao_curta__icontains=termo) |
            Q(descricao_longa__icontains=termo)
        )

        self.request.session.save()
        return qs


class DetalheProduto(DetailView):
    model = Produto
    template_name = 'produto/product-single.html'
    context_object_name = 'produto'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        # Obtém o contexto padrão da DetailView
        context = super().get_context_data(**kwargs)
        
        # Obtém o produto atual
        produto = self.get_object()
        
        # Calcula o desconto, se houver preço promocional
        if produto.preco_marketing_promocional:
            desconto = ((produto.preco_marketing - produto.preco_marketing_promocional) / produto.preco_marketing) * 100
            desconto = int(round(desconto, 0))  # Arredonda e converte para inteiro
        else:
            desconto = 0
        
        # Adiciona o desconto ao contexto
        context['desconto'] = desconto
        
        # Obtém os produtos relacionados (da mesma categoria)
        produtos_relacionados = Produto.objects.filter(category=produto.category).exclude(id=produto.id)[:4]
        
        # Adiciona os produtos relacionados ao contexto
        context['produtos_relacionados'] = produtos_relacionados
        
        return context


class AdicionarAoCarrinho(View):
    def get(self, *args, **kwargs):
        http_referer = self.request.META.get(
            'HTTP_REFERER',
            reverse('produto:lista')
        )
        variacao_id = self.request.GET.get('vid')
        quantidade = int(self.request.GET.get('quantidade', 1))  # Captura a quantidade

        if not variacao_id:
            messages.error(self.request, 'Produto não existe')
            return redirect(http_referer)

        variacao = get_object_or_404(Variacao, id=variacao_id)
        variacao_estoque = variacao.estoque
        produto = variacao.produto

        produto_id = produto.id
        produto_nome = produto.nome
        variacao_nome = variacao.nome or ''
        preco_unitario = variacao.preco
        preco_unitario_promocional = variacao.preco_promocional
        slug = produto.slug
        imagem = produto.imagem.name if produto.imagem else ''

        if variacao_estoque < 1:
            messages.error(self.request, 'Estoque insuficiente')
            return redirect(http_referer)

        if not self.request.session.get('carrinho'):
            self.request.session['carrinho'] = {}
            self.request.session.save()

        carrinho = self.request.session['carrinho']

        if variacao_id in carrinho:
            quantidade_carrinho = carrinho[variacao_id]['quantidade']
            quantidade_carrinho += quantidade  # Adiciona a nova quantidade

            # Se a nova quantidade ultrapassar o estoque disponível
            if variacao_estoque < quantidade_carrinho:
                messages.warning(
                    self.request,
                    f'Estoque insuficiente para {quantidade_carrinho}x no '
                    f'produto "{produto_nome}". Adicionamos {variacao_estoque}x '
                    f'no seu carrinho.'
                )
                quantidade_carrinho = variacao_estoque  # Ajusta para o máximo possível

            carrinho[variacao_id]['quantidade'] = quantidade_carrinho
            carrinho[variacao_id]['preco_quantitativo'] = preco_unitario * quantidade_carrinho
            carrinho[variacao_id]['preco_quantitativo_promocional'] = preco_unitario_promocional * quantidade_carrinho
        else:
            # Adiciona o produto com a quantidade escolhida
            carrinho[variacao_id] = {
                'produto_id': produto_id,
                'produto_nome': produto_nome,
                'variacao_nome': variacao_nome,
                'variacao_id': variacao_id,
                'preco_unitario': preco_unitario,
                'preco_unitario_promocional': preco_unitario_promocional,
                'preco_quantitativo': preco_unitario * quantidade,
                'preco_quantitativo_promocional': preco_unitario_promocional * quantidade,
                'quantidade': quantidade,
                'slug': slug,
                'imagem': imagem,
            }

        self.request.session.save()

        messages.success(
            self.request,
            f'Produto {produto_nome} {variacao_nome} adicionado ao seu carrinho  '
            # f'carrinho {carrinho[variacao_id]["quantidade"]}x.'
        )

        return redirect(http_referer)


class RemoverDoCarrinho(View):
    def get(self, *args, **kwargs):
        http_referer = self.request.META.get(
            'HTTP_REFERER',
            reverse('produto:lista')
        )
        variacao_id = self.request.GET.get('vid')

        if not variacao_id:
            return redirect(http_referer)

        if not self.request.session.get('carrinho'):
            return redirect(http_referer)

        if variacao_id not in self.request.session['carrinho']:
            return redirect(http_referer)

        carrinho = self.request.session['carrinho'][variacao_id]

        messages.success(
            self.request,
            f'Produto {carrinho["produto_nome"]} {carrinho["variacao_nome"]} '
            f'removido do seu carrinho.'
        )

        del self.request.session['carrinho'][variacao_id]
        self.request.session.save()
        return redirect(http_referer)


class Carrinho(View):
    def get(self, *args, **kwargs):
        contexto = {
            'carrinho': self.request.session.get('carrinho', {})
        }

        return render(self.request, 'produto/cart.html', contexto)


class ResumoDaCompra(View):
    def get(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return redirect('perfil:criar')

        perfil = Perfil.objects.filter(usuario=self.request.user).exists()        

        if not perfil:
            messages.error(
                self.request,
                'Usuário sem perfil.'
            )
            return redirect('perfil:criar')

        if not self.request.session.get('carrinho'):
            messages.error(
                self.request,
                'Carrinho vazio.'
            )
            return redirect('produto:lista')

        contexto = {
            'usuario': self.request.user,
            'carrinho': self.request.session['carrinho'],
        }

        return render(self.request, 'produto/resumodacompra.html', contexto)


class GerarPagamentoMercadoPago(View):
    def get(self, request, *args, **kwargs):
        # Verifica se o usuário está autenticado
        if not request.user.is_authenticated:
            messages.error(request, 'Você precisa fazer login.')
            return redirect(reverse('perfil:criar'))

        # Verifica se há itens no carrinho
        carrinho = request.session.get('carrinho')
        if not carrinho:
            messages.error(request, 'Carrinho vazio.')
            return redirect(reverse('produto:lista'))

        try:
            sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)
            nome = settings.MERCADO_PAGO_STORE_NAME
            # Prepara os itens para pagamento
            items = [
                {
                    "id": item_id,
                    "title": item_data['produto_nome'],
                    "quantity": item_data['quantidade'],
                    "currency_id": "BRL",
                    "unit_price": float(item_data['preco_unitario'])  # Usar o preço unitário correto
                }
                for item_id, item_data in carrinho.items()
            ]

            # Define as URLs de retorno
            base_url = request.build_absolute_uri('/')  # Gera a URL base do site
            back_urls = {
                "success": request.build_absolute_uri(reverse('pedido:pagamento_confirmado')),
                "failure": request.build_absolute_uri(reverse('produto:resumodacompra')),
                "pending": request.build_absolute_uri(reverse('produto:resumodacompra'))

            }

            # Salva os dados do pagamento na sessão
            request.session['payment_data'] = {
                "items": items,
                "back_urls": back_urls,
                "auto_return": "approved",
                "binary_mode": True,
                "statement_descriptor": nome,
            }
            request.session.modified = True  # Garante que a sessão será salva

            # Redireciona para salvar o pedido antes de gerar o pagamento
            return redirect(reverse('pedido:salvarpedido'))

        except Exception as e:
            messages.error(request, f"Erro ao processar pagamento: {str(e)}")
            return redirect(reverse('produto:lista'))



    
