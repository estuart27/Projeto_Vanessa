from utils import utils
from openrouteservice import Client
from openrouteservice.geocode import pelias_search
from django import template
from django.conf import settings


register = template.Library()


API_KEY = "5b3ce3597851110001cf6248151bddc9bb50465286bed08b4efaa1b3"
client = Client(key=API_KEY)

def obter_coordenadas(endereco, cidade="Londrina", estado="PR"):
    """Converte um endereço em texto para coordenadas [longitude, latitude]."""
    try:
        # Adicionando cidade e estado para melhorar a precisão da busca
        endereco_completo = f"{endereco}, {cidade}, {estado}, Brasil"
        print(f"Buscando geocodificação para: {endereco_completo}")
        
        resultados = pelias_search(client, endereco_completo)
        
        if resultados and len(resultados['features']) > 0:
            # Pega as coordenadas do primeiro resultado
            coord = resultados['features'][0]['geometry']['coordinates']
            # Verificar se as coordenadas estão na região esperada (aproximadamente para Londrina)
            # Londrina está aproximadamente em: longitude -51.15, latitude -23.30
            
            # Se as coordenadas estiverem muito distantes de Londrina, pode ser um erro
            if abs(coord[0] + 51.15) > 1 or abs(coord[1] + 23.30) > 1:
                print(f"AVISO: As coordenadas encontradas parecem estar fora da região de Londrina!")
            
            return coord
        else:
            print(f"Não foi possível encontrar coordenadas para: {endereco_completo}")
            return None
    except Exception as e:
        print(f"Erro ao converter endereço para coordenadas: {e}")
        return None

def calcular_distancia_por_endereco(endereco_origem, endereco_destino, cidade="Londrina", estado="PR"):
    """Calcula a distância entre dois endereços."""
    coord_origem = obter_coordenadas(endereco_origem, cidade, estado)
    coord_destino = obter_coordenadas(endereco_destino, cidade, estado)
    
    if not coord_origem or not coord_destino:
        return 0
    
    try:
        coordenadas = [coord_origem, coord_destino]
        
        # Imprime as coordenadas para verificação
        print(f"DEBUG - Coordenadas enviadas para API: {coordenadas}")
        
        resposta = client.directions(
            coordinates=coordenadas, 
            profile="driving-car", 
            format="geojson",
            radiuses=[50000, 50000]  # Raio de 50 km para cobrir toda a cidade

            # radiuses=[5000, 5000]  # 5km de raio
        )
        
        # Verificar se há rotas na resposta
        if 'features' in resposta and len(resposta['features']) > 0:
            distancia_km = resposta['features'][0]['properties']['segments'][0]['distance'] / 1000
            print(f"Distância calculada: {distancia_km:.2f} km")  # <-- Adicionado aqui
            return distancia_km
        else:
            print("Não foi possível encontrar uma rota entre os pontos")
            return 0
    except Exception as e:
        print(f"Erro ao calcular distância: {e}")
        print(f"Tente com coordenadas mais precisas ou verifique se os endereços estão corretos")
        return 0

@register.filter
def calcular_frete(perfil, origem=settings.ENDERECO_LOJA,):
    """
    Calcula o frete baseado na distância entre origem e o endereço do perfil
    """
    if not perfil:
        return 0
        
    # Monta o endereço completo do perfil
    destino = f"{perfil.endereco}"
    print(f'destino - {destino}')
    nomex = settings.ENDERECO_LOJA
    print(nomex)
    
    distancia_km = calcular_distancia_por_endereco(origem, destino)
    
    # Taxa base + valor por km (mínimo de R$ 10)
    preco_por_km = 2.50
    taxa_base = 5.00
    valor_frete = min(20.00, max(12.00, taxa_base + (distancia_km * preco_por_km)))

    # valor_frete = max(12.00, taxa_base + (distancia_km * preco_por_km))
    
    # Arredonda para o próximo valor inteiro
    valor_frete = round(valor_frete, 2)
    
    return valor_frete

@register.filter
def total_com_frete(carrinho, frete):
    """
    Calcula o total do carrinho incluindo o frete
    """
    total_carrinho = sum(
        [item.get('preco_quantitativo_promocional') if item.get('preco_quantitativo_promocional')
         else item.get('preco_quantitativo') for item in carrinho.values()]
    )
    
    return total_carrinho + float(frete)







