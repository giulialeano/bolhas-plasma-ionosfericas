import os
import numpy as np
from datetime import datetime
from src.leitor import LeitorH5
from src.processador import ProcessadorDados
from src.graficos import GeradorGraficos

def processar_dia(dados_arquivos, data):
    """
    Processa múltiplos arquivos de um mesmo dia e retorna os dados consolidados.
    
    Args:
        dados_arquivos: Lista de dicionários com dados de cada arquivo
        data: Data do dia
    
    Returns:
        dict: Dados consolidados com médias
    """
    print(f"\n{'='*60}")
    print(f"CONSOLIDANDO DIA: {data.strftime('%d/%m/%Y')}")
    print(f"Arquivos: {len(dados_arquivos)}")
    print(f"{'='*60}")
    
    # Verificar quais constelações estão presentes em todos os arquivos
    constelacoes_comuns = None
    for dados in dados_arquivos:
        consts = set(dados.keys())
        if constelacoes_comuns is None:
            constelacoes_comuns = consts
        else:
            constelacoes_comuns = constelacoes_comuns.intersection(consts)
    
    print(f"Constelações comuns: {constelacoes_comuns}")
    
    if not constelacoes_comuns:
        print("Nenhuma constelação comum entre os arquivos.")
        return None
    
    # Dicionário para dados consolidados
    dados_consolidados = {}
    eventos_consolidados = []
    
    for constelacao in constelacoes_comuns:
        print(f"\nConsolidando: {constelacao}")
        
        # Coletar dados de todos os arquivos para esta constelação
        todos_vtec = []
        todos_s4 = []
        todos_tempo = []
        todos_eventos = []
        
        for dados_arquivo in dados_arquivos:
            if constelacao not in dados_arquivo:
                continue
            
            dados_const = dados_arquivo[constelacao]
            
            # Extrair dados
            vtec = dados_const.get('vtec')
            s4 = dados_const.get('s4')
            horas = dados_const.get('horas')
            eventos = dados_const.get('eventos', [])
            
            if vtec is not None and len(vtec) > 0:
                todos_vtec.append(vtec)
                todos_s4.append(s4)
                todos_tempo.append(horas)
                todos_eventos.extend(eventos)
        
        if not todos_vtec:
            print(f"  Nenhum dado válido para {constelacao}")
            continue
        
        # Calcular a mediana entre os arquivos
        tamanho_min = min([len(t) for t in todos_tempo])
        print(f"  Tamanho mínimo: {tamanho_min} pontos")
        
        # Truncar todos para o mesmo tamanho
        vtec_array = np.array([v[:tamanho_min] for v in todos_vtec])
        s4_array = np.array([s[:tamanho_min] for s in todos_s4])
        tempo_array = todos_tempo[0][:tamanho_min]
        
        # Média (ou mediana) entre os arquivos
        vtec_medio = np.mean(vtec_array, axis=0)
        s4_medio = np.mean(s4_array, axis=0)
        
        # Salvar dados consolidados
        dados_consolidados[constelacao] = {
            'horas': tempo_array,
            'vtec': vtec_medio,
            's4': s4_medio,
            'num_arquivos': len(todos_vtec)
        }
        
        # Adicionar eventos (com data para identificar)
        for evento in todos_eventos:
            evento['data'] = data
            eventos_consolidados.append(evento)
        
        print(f"  VTEC médio: {np.mean(vtec_medio):.2f} TECU")
        print(f"  S4 médio: {np.mean(s4_medio):.3f}")
    
    return {
        'dados': dados_consolidados,
        'eventos': eventos_consolidados,
        'num_arquivos': len(dados_arquivos)
    }


def processar_arquivo(caminho):
    """Processa um único arquivo .h5 e retorna os dados processados."""
    nome = os.path.basename(caminho)
    print(f"  Processando: {nome}")
    
    # 1. Ler dados
    leitor = LeitorH5(caminho)
    leitor.abrir()
    dados = leitor.extrair_todas_constelacoes()
    leitor.fechar()
    
    if not dados:
        print(f"  ⚠️ Nenhum dado encontrado em {nome}")
        return None
    
    # 2. Processar
    processador = ProcessadorDados(dados, nome)
    processador.processar_medias_diarias()
    processador.detectar_bolhas()
    
    # Retornar dados processados
    resultado = {}
    for constelacao, dados_media in processador.dados_media.items():
        resultado[constelacao] = {
            'horas': dados_media['horas'],
            'vtec': dados_media['vtec'],
            's4': dados_media['s4'],
            'num_satelites': dados_media.get('num_satelites', 0),
            'eventos': [e for e in processador.eventos if e['constelacao'] == constelacao]
        }
    
    return resultado


def main():
    """Pipeline principal - consolida dados por dia."""
    print("="*60)
    print("ANÁLISE DE BOLHAS DE PLASMA - CONSOLIDADA POR DIA")
    print("Identificação de estruturas com diminuição abrupta de densidade")
    print("="*60)
    
    # Listar arquivos .h5
    pasta_dados = 'dados/'
    arquivos = [f for f in os.listdir(pasta_dados) if f.endswith('.h5')]
    
    print(f"\nArquivos encontrados: {len(arquivos)}")
    for a in arquivos:
        print(f"  - {a}")
    
    # Agrupar arquivos por dia
    dias = {}
    for arquivo in arquivos:
        # Extrair data do nome
        partes = arquivo.split('_')
        if len(partes) >= 3:
            data_str = partes[2]
            try:
                data = datetime.strptime(data_str, '%Y%m%d')
                data_key = data.strftime('%Y%m%d')
                if data_key not in dias:
                    dias[data_key] = {'data': data, 'arquivos': []}
                dias[data_key]['arquivos'].append(os.path.join(pasta_dados, arquivo))
            except:
                continue
    
    print(f"\nDias encontrados: {list(dias.keys())}")
    
    # Processar cada dia
    for data_key, info in dias.items():
        data = info['data']
        arquivos_dia = info['arquivos']
        
        print(f"\n{'='*60}")
        print(f"DIA: {data.strftime('%d/%m/%Y')}")
        print(f"Arquivos: {len(arquivos_dia)}")
        print(f"{'='*60}")
        
        # Processar cada arquivo do dia
        dados_arquivos = []
        for caminho in arquivos_dia:
            resultado = processar_arquivo(caminho)
            if resultado:
                dados_arquivos.append(resultado)
        
        if not dados_arquivos:
            print("Nenhum dado processado para este dia.")
            continue
        
        # Consolidar dados do dia
        if len(dados_arquivos) > 1:
            print(f"\nConsolidando {len(dados_arquivos)} arquivos...")
            consolidado = processar_dia(dados_arquivos, data)
        else:
            print(f"\nApenas 1 arquivo para este dia.")
            consolidado = {
                'dados': dados_arquivos[0],
                'eventos': [],
                'num_arquivos': 1
            }
            # Extrair eventos dos dados
            for constelacao, dados_const in dados_arquivos[0].items():
                eventos = dados_const.get('eventos', [])
                for e in eventos:
                    e['data'] = data
                    consolidado['eventos'].append(e)
        
        if not consolidado or not consolidado['dados']:
            print("Nenhum dado consolidado.")
            continue
        
        # Salvar relatório do dia
        os.makedirs('resultados/relatorios', exist_ok=True)
        caminho_relatorio = f'resultados/relatorios/eventos_{data_key}.txt'
        
        with open(caminho_relatorio, 'w', encoding='utf-8') as f:
            f.write("="*60 + "\n")
            f.write(f"RELATÓRIO DE EVENTOS CONSOLIDADOS - {data.strftime('%d/%m/%Y')}\n")
            f.write("="*60 + "\n")
            f.write(f"Arquivos processados: {consolidado['num_arquivos']}\n")
            f.write(f"Constelações: {', '.join(consolidado['dados'].keys())}\n")
            f.write(f"Total de eventos: {len(consolidado['eventos'])}\n")
            f.write("\n")
            
            if consolidado['eventos']:
                for i, evento in enumerate(consolidado['eventos'], 1):
                    f.write(f"Evento #{i}\n")
                    f.write(f"  Constelação: {evento['constelacao']}\n")
                    f.write(f"  Horário: {evento['horario']:.1f}h\n")
                    f.write(f"  VTEC: {evento['vtec']:.2f} TECU\n")
                    f.write(f"  S4: {evento['s4']:.3f}\n")
                    f.write(f"  Queda: {evento['queda']:.1f}%\n")
                    f.write(f"  VTEC Médio Diário: {evento['vtec_medio']:.2f} TECU\n")
                    f.write("-"*40 + "\n")
            else:
                f.write("Nenhum evento detectado.\n")
        
        print(f"\nRelatório salvo: {caminho_relatorio}")
        
        # Gerar gráfico consolidado
        os.makedirs(f'resultados/graficos/{data_key}', exist_ok=True)
        caminho_grafico = f'resultados/graficos/{data_key}/bolhas_{data_key}.png'
        
        graficos = GeradorGraficos(
            consolidado['dados'],
            consolidado['eventos'],
            data
        )
        graficos.grafico_dia(salvar=True, caminho=caminho_grafico)
    
    print("\n" + "="*60)
    print("PROCESSAMENTO CONCLUÍDO!")
    print("="*60)
    print("\nEstrutura gerada:")
    print("  - resultados/relatorios/eventos_YYYYMMDD.txt")
    print("  - resultados/graficos/YYYYMMDD/bolhas_YYYYMMDD.png")
    print("="*60)


if __name__ == "__main__":
    main()