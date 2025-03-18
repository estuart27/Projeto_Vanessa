# from geopy.geocoders import Nominatim
# from geopy.distance import geodesic

# # Inicializa o geocoder
# geolocator = Nominatim(user_agent="calculo_frete")

# # Função para obter coordenadas de um endereço
# def get_coordinates(address):
#     location = geolocator.geocode(address)
#     if location:
#         return (location.latitude, location.longitude)
#     else:
#         print(f"Endereço não encontrado: {address}")
#         return None

# # Função para calcular frete baseado na distância em linha reta
# def calcular_frete(origem, destino, preco_por_km=2.50):
#     coords_origem = get_coordinates(origem)
#     coords_destino = get_coordinates(destino)
    
#     if not coords_origem or not coords_destino:
#         return None
    
#     # Calcula a distância em km (linha reta)
#     distancia_km = geodesic(coords_origem, coords_destino).km
    
#     # Calcula o valor do frete
#     valor_frete = distancia_km * preco_por_km
    
#     # print(f"Distância: {distancia_km:.2f} km")
#     # print(f"Valor do Frete: R$ {valor_frete:.2f}")
    
#     valor = f'{valor_frete:.2f}'

#     return valor

# # Teste: Insira os endereços
# origem = "R. da Fraternidade - Londrina - PR"
# destino = "Av. Theodoro Victorelli, Londrina, PR"


# frete = calcular_frete(origem, destino)

# print(frete)



# R. Francisco Arias Londrina, PR, Brasil

# Av. Theodoro Victorelli, Londrina, PR

# R. Dionísia Oliveira Taváres, Londrina - PR, 

# R. da Fraternidade - Londrina - PR



import openrouteservice
from openrouteservice.geocode import pelias_search

API_KEY = "5b3ce3597851110001cf6248151bddc9bb50465286bed08b4efaa1b3"
client = openrouteservice.Client(key=API_KEY)

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
            radiuses=[5000, 5000]  # 5km de raio
        )
        
        # Verificar se há rotas na resposta
        if 'features' in resposta and len(resposta['features']) > 0:
            distancia_km = resposta['features'][0]['properties']['segments'][0]['distance'] / 1000
            return distancia_km
        else:
            print("Não foi possível encontrar uma rota entre os pontos")
            return 0
    except Exception as e:
        print(f"Erro ao calcular distância: {e}")
        print(f"Tente com coordenadas mais precisas ou verifique se os endereços estão corretos")
        return 0

def calcular_taxa_por_endereco(endereco_origem, endereco_destino, cidade="Londrina", estado="PR"):
    """Calcula a taxa baseada na distância entre dois endereços."""
    distancia = calcular_distancia_por_endereco(endereco_origem, endereco_destino, cidade, estado)
    return distancia * 2.50  # R$2,50 por KM

# Exemplo de uso com interface para o usuário
def main():
    print("=== Calculadora de Distância e Taxa de Entrega ===")
    
    # Configuração da região padrão
    cidade = input("Digite a cidade (deixe em branco para usar Londrina): ") or "Londrina"
    estado = input("Digite o estado (deixe em branco para usar PR): ") or "PR"
    
    endereco_origem = input("Digite o endereço de origem: ")
    endereco_destino = input("Digite o endereço de destino: ")
    
    # Obtém e mostra as coordenadas
    coord_origem = obter_coordenadas(endereco_origem, cidade, estado)
    coord_destino = obter_coordenadas(endereco_destino, cidade, estado)
    
    if coord_origem and coord_destino:
        print(f"\nCoordenadas de origem: [longitude: {coord_origem[0]}, latitude: {coord_origem[1]}]")
        print(f"Coordenadas de destino: [longitude: {coord_destino[0]}, latitude: {coord_destino[1]}]")
        
        distancia = calcular_distancia_por_endereco(endereco_origem, endereco_destino, cidade, estado)
        taxa = calcular_taxa_por_endereco(endereco_origem, endereco_destino, cidade, estado)
        
        print(f"\nDistância: {distancia:.2f} km")
        print(f"Taxa de entrega: R$ {taxa:.2f}")
    else:
        print("\nNão foi possível calcular a distância devido a um erro na obtenção das coordenadas.")
        print("Dica: Verifique se o endereço está completo e se está na cidade e estado corretos.")

if __name__ == "__main__":
    main()



# # R. Francisco Arias Londrina, PR, Brasil

# # Av. Theodoro Victorelli, Londrina, PR

# # R. Dionísia Oliveira Taváres, Londrina - PR, 

# # R. da Fraternidade - Londrina - PR