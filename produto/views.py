import json
import uuid
import logging

from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.db.models import Q, Count
from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.views.generic import ListView, DetailView, View

import mercadopago

from .models import Produto, Category, Postagem, Variacao, Cor
from perfil.models import Perfil
from .forms import ContatoForm, FormularioComentario



logger = logging.getLogger(__name__)


def about(request):
    return render(
        request,
        'produto/about.html',
    )

def index(request):
    try:
        queryset = Produto.objects.order_by('?')[:4]
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

        context = {
            'produtos': queryset,
            'categories': categories,
            'produtos_com_desconto': produtos_com_desconto,
        }

        return render(request, 'produto/index.html', context)
    except Exception as e:
        messages.error(request, "Ocorreu um erro ao carregar a página inicial. Por favor, tente novamente mais tarde.")

        logger.error(f"Erro na página inicial: {str(e)}")
        # Return a simple page instead of the full index
        return render(request, 'produto/error.html', {'message': 'Erro ao carregar produtos'})


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


def contact(request):
    if request.method == 'POST':
        form = ContatoForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                try:
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
                except Exception as email_error:
                    # Log email error but don't show to user since the form was saved
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Erro ao enviar email: {str(email_error)}")
                    
                messages.success(request, 'Mensagem enviada com sucesso!')
                return redirect('produto:contact')
            except Exception as e:
                messages.error(request, 'Erro ao salvar mensagem. Por favor, tente novamente.')
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Erro ao salvar formulário de contato: {str(e)}")
    else:
        form = ContatoForm()
    return render(request, 'produto/contact.html', {'form': form})



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


class ListaProdutos(ListView):
    model = Produto
    template_name = 'produto/shop.html'
    context_object_name = 'produtos'
    paginate_by = 15
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
        context = super().get_context_data(**kwargs)
        produto = self.get_object()
        
        # Adiciona as cores disponíveis
        context['cores'] = produto.cores.all()
        
        # Calcula o desconto
        if produto.preco_marketing_promocional:
            desconto = ((produto.preco_marketing - produto.preco_marketing_promocional) / produto.preco_marketing) * 100
            desconto = int(round(desconto, 0))
        else:
            desconto = 0
        
        context['desconto'] = desconto
        # context['produtos_relacionados'] = Produto.objects.filter(category=produto.category).exclude(id=produto.id)[:4]
        # No modelo Produto, verifique se o método get_absolute_url está correto
        # Exemplo:
        def get_absolute_url(self):
            return reverse('produto:detalhe', kwargs={'slug': self.slug})
        
        return context



class RemoverDoCarrinho(View):
    def get(self, *args, **kwargs):
        request = self.request
        http_referer = request.META.get('HTTP_REFERER', reverse('produto:lista'))
        
        variacao_id = request.GET.get('vid')
        cor_id = request.GET.get('cid', '0')  # Se não houver cor, definir como '0'

        if not variacao_id:
            messages.error(request, 'Produto não identificado.')
            return redirect(http_referer)

        if 'carrinho' not in request.session or not request.session['carrinho']:
            messages.error(request, 'Seu carrinho está vazio.')
            return redirect(http_referer)

        carrinho = request.session['carrinho']

        # Criar a chave específica do produto
        item_key = f"{variacao_id}-{cor_id}"

        # Buscar qualquer variação de cor caso a chave exata não seja encontrada
        chave_encontrada = None
        if item_key in carrinho:
            chave_encontrada = item_key
        else:
            # Tenta encontrar qualquer chave que tenha esse `variacao_id`
            for key in carrinho.keys():
                if key.startswith(f"{variacao_id}-"):
                    chave_encontrada = key
                    break  # Para no primeiro encontrado

        # Debug: Exibir chaves para depuração
        print(f"Chave do item a remover: {item_key}")
        print(f"Chave realmente removida: {chave_encontrada}")
        print(f"Chaves no carrinho antes: {list(carrinho.keys())}")

        if not chave_encontrada:
            messages.error(request, 'Produto não encontrado no carrinho.')
            return redirect(http_referer)

        # Obter informações do item antes de remover
        produto_nome = carrinho[chave_encontrada]['produto_nome']
        variacao_nome = carrinho[chave_encontrada]['variacao_nome']
        cor_nome = carrinho[chave_encontrada]['cor_nome']

        # Remover o item do carrinho
        del carrinho[chave_encontrada]
        request.session.modified = True

        # Debug: Mostrar chaves após remoção
        print(f"Chaves no carrinho depois: {list(carrinho.keys())}")

        mensagem = f'Produto {produto_nome}'
        if variacao_nome:
            mensagem += f' ({variacao_nome})'
        if cor_nome != "Padrão":
            mensagem += f' na cor {cor_nome}'
        mensagem += ' foi removido do seu carrinho.'

        messages.success(request, mensagem)
        return redirect(http_referer)
    

class AdicionarAoCarrinho(View):
    def get(self, *args, **kwargs):
        request = self.request
        http_referer = request.META.get('HTTP_REFERER', reverse('produto:lista'))
        
        try:
            variacao_id = request.GET.get('vid')
            cor_id = request.GET.get('cid')

            # Validação da quantidade
            try:
                quantidade = int(request.GET.get('quantidade', 1))
                if quantidade < 1:
                    messages.error(request, 'A quantidade deve ser maior que zero.')
                    return redirect(http_referer)
            except ValueError:
                messages.error(request, 'Quantidade inválida.')
                return redirect(http_referer)

            if not variacao_id:
                messages.error(request, 'Produto não selecionado.')
                return redirect(http_referer)

            # Buscar a variação e o produto
            variacao = get_object_or_404(Variacao, id=variacao_id)
            produto = variacao.produto
            
            # Verificar estoque
            if variacao.estoque < quantidade:
                messages.error(request, f'Estoque insuficiente. Apenas {variacao.estoque} unidades disponíveis.')
                return redirect(http_referer)
            
            # Buscar a cor (ou usar a cor padrão)
            cor = None
            cor_nome = produto.cor_padrao_nome  # Usar o nome da cor padrão do produto
            cor_codigo_hex = produto.cor_padrao_codigo_hex  # Usar o código hex da cor padrão
            cor_imagem = produto.imagem.url if produto.imagem else ''  # Imagem padrão do produto

            if cor_id:
                try:
                    cor = Cor.objects.get(id=cor_id, produto=produto)
                    cor_nome = cor.get_codigo_hex_display()
                    cor_codigo_hex = cor.codigo_hex
                    cor_imagem = cor.imagem.url if cor.imagem else cor_imagem  # Se não houver imagem da cor, mantém a imagem padrão
                except Cor.DoesNotExist:
                    # Se a cor solicitada não existir, usar a cor padrão do produto
                    pass
            
            # Inicializar o carrinho
            if 'carrinho' not in request.session:
                request.session['carrinho'] = {}

            carrinho = request.session['carrinho']

            # Criar chave única para o item no carrinho
            item_key = f"{variacao_id}-{cor_id}" if cor_id else f"{variacao_id}-padrao"

            # Se o item já existe no carrinho, atualizar a quantidade
            if item_key in carrinho:
                quantidade_atual = carrinho[item_key]['quantidade']
                nova_quantidade = quantidade_atual + quantidade

                # Verificar estoque disponível
                if nova_quantidade > variacao.estoque:
                    messages.warning(request, f'Estoque insuficiente para {nova_quantidade}x. '
                                              f'Foi adicionado o máximo disponível: {variacao.estoque}x.')
                    nova_quantidade = variacao.estoque
                
                carrinho[item_key]['quantidade'] = nova_quantidade
                carrinho[item_key]['preco_quantitativo'] = variacao.preco * nova_quantidade
                carrinho[item_key]['preco_quantitativo_promocional'] = variacao.preco_promocional * nova_quantidade
            else:
                # Criar um novo item no carrinho
                carrinho[item_key] = {
                    'produto_id': produto.id,
                    'produto_nome': produto.nome,
                    'variacao_nome': variacao.nome or '',
                    'variacao_id': variacao_id,
                    'cor_id': cor_id if cor else '',
                    'cor_nome': cor_nome,
                    'cor_codigo_hex': cor_codigo_hex,
                    'preco_unitario': variacao.preco,
                    'preco_unitario_promocional': variacao.preco_promocional,
                    'preco_quantitativo': variacao.preco * quantidade,
                    'preco_quantitativo_promocional': variacao.preco_promocional * quantidade,
                    'quantidade': quantidade,
                    'slug': produto.slug,
                    'imagem': cor_imagem,
                }

            request.session.modified = True
            
            # Mensagem de sucesso
            mensagem = f'Produto {produto.nome}'
            if variacao.nome:
                mensagem += f' ({variacao.nome})'
            if cor_nome != "Padrão":
                mensagem += f' na cor {cor_nome}'
            mensagem += ' foi adicionado ao seu carrinho.'

            messages.success(request, mensagem)
            return redirect(http_referer)

        except Exception as e:
            messages.error(request, 'Erro ao adicionar produto ao carrinho.')
            logger.error(f"Erro ao adicionar ao carrinho: {str(e)}")
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

# class ResumoDaCompra(View):
#     def get(self, *args, **kwargs):
#         if not self.request.user.is_authenticated:
#             return redirect('perfil:criar')

#         # Verifica se o usuário tem perfil
#         try:
#             perfil = Perfil.objects.get(usuario=self.request.user)
#         except Perfil.DoesNotExist:
#             messages.error(
#                 self.request,
#                 'Usuário sem perfil. Complete seu cadastro para continuar.'
#             )
#             return redirect('perfil:criar')

#         if not self.request.session.get('carrinho'):
#             messages.error(
#                 self.request,
#                 'Carrinho vazio.'
#             )
#             return redirect('produto:lista')

#         # Calcula o valor do frete com base no endereço do perfil
#         from templatetags.omfilters import calcular_frete
#         valor_frete = calcular_frete(perfil)

#         contexto = {
#             'usuario': self.request.user,
#             'carrinho': self.request.session['carrinho'],
#             'valor_frete': valor_frete,
#         }

#         return render(self.request, 'produto/resumodacompra.html', contexto)



#VERIFICADO
class GerarPagamentoMercadoPago(View):
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Você precisa fazer login.')
            return redirect(reverse('perfil:criar'))

        carrinho = request.session.get('carrinho')
        if not carrinho:
            messages.error(request, 'Carrinho vazio.')
            return redirect(reverse('produto:lista'))

        try:
            sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)
            nome = settings.MERCADO_PAGO_STORE_NAME

            if not hasattr(settings, 'MERCADO_PAGO_ACCESS_TOKEN') or not settings.MERCADO_PAGO_ACCESS_TOKEN:
                messages.error(request, 'Erro de configuração do sistema de pagamento.')
                logger.error("MERCADO_PAGO_ACCESS_TOKEN não está configurado")
                return redirect(reverse('produto:resumodacompra'))

            items = []
            try:
                for item_id, item_data in carrinho.items():
                    if not all(key in item_data for key in ['produto_nome', 'quantidade', 'preco_unitario']):
                        raise KeyError("Dados do carrinho incompletos")

                    price = float(item_data['preco_unitario'])
                    if price <= 0:
                        raise ValueError(f"Preço inválido para o produto {item_data['produto_nome']}")

                    items.append({
                        "id": item_id,
                        "title": item_data['produto_nome'],
                        "quantity": item_data['quantidade'],
                        "currency_id": "BRL",
                        "unit_price": price,
                        "category_id": "produtos",
                        "description": f"Produto: {item_data['produto_nome']}",
                    })
            except (KeyError, ValueError, TypeError) as e:
                messages.error(request, 'Erro nos dados do carrinho. Por favor, tente novamente.')
                logger.error(f"Erro ao processar itens do carrinho: {str(e)}")
                return redirect(reverse('produto:lista'))
            
            pedido_uuid = str(uuid.uuid4())
            
            # Armazenar na sessão para recuperar posteriormente
            self.request.session['pedido_referencia'] = pedido_uuid

            payer = {
                "first_name": request.user.first_name,  # Não use username aqui
                "last_name": request.user.last_name,
                "email": request.user.email,  # Adicione o email
                "identification": {
                    "type": "CPF",  # Você precisará coletar/armazenar esta informação
                    "number": request.user.perfil.cpf # Substitua pelo CPF real do usuário
                }
            }

            payment_data = {
                "items": items,
                "payer": payer,
                "back_urls": {
                    "success": request.build_absolute_uri(reverse('pedido:pagamento_confirmado')),
                    "failure": request.build_absolute_uri(reverse('produto:resumodacompra')),
                    "pending": request.build_absolute_uri(reverse('produto:resumodacompra'))
                },
                "auto_return": "approved",
                "binary_mode": False,
                "statement_descriptor": nome,
                "notification_url": request.build_absolute_uri(reverse('pedido:webhook')),
                "external_reference": pedido_uuid,
                
                "payment_methods": {
                    "excluded_payment_types": [],
                    "excluded_payment_methods": [],
                    "default_payment_method_id": None,
                    "installments": 12,
                    "default_installments": 1
                }
            }

            preference_response = sdk.preference().create(payment_data)

            if "response" in preference_response:
                logger.error(f"Erro completo do Mercado Pago: {json.dumps(preference_response, indent=2)}")
                logger.info(f"Preference ID: {preference_response['response']['id']}")
                logger.info(f"Payment methods: {json.dumps(preference_response['response'].get('payment_methods', {}), indent=2)}")
                logger.info(f"Init point URL: {preference_response['response']['init_point']}")
                return redirect(preference_response["response"]["init_point"])
            else:
                error_detail = preference_response.get('error', 'Sem detalhes')
                logger.error(f"Erro na resposta do Mercado Pago: {error_detail}")
                messages.error(request, 'Erro ao gerar pagamento.')
                return redirect(reverse('produto:resumodacompra'))

        except Exception as e:
            messages.error(request, f"Erro ao processar pagamento. Por favor, tente novamente mais tarde.")
            logger.info(f"Resposta do Mercado Pago: {preference_response}")
            logger.error(f"Erro detalhado ao processar pagamento: {str(e)}")
            return redirect(reverse('produto:resumodacompra'))


