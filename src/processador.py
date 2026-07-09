import numpy as np
from datetime import datetime
import os

class ProcessadorDados:
    """
    Processa dados GNSS, calcula VTEC e detecta bolhas.
    """
    
    def __init__(self, dados_completos, nome_arquivo):
        self.dados_completos = dados_completos
        self.nome_arquivo = nome_arquivo
        self.data = self._extrair_data()
        self.dados_media = {}
        self.eventos = []
    
    def _extrair_data(self):
        try:
            partes = self.nome_arquivo.split('_')
            data_str = partes[2]
            return datetime.strptime(data_str, '%Y%m%d')
        except:
            return None
    
    def _garantir_unidimensional(self, array):
        if array is None:
            return np.array([])
        array = np.array(array)
        if array.size == 0:
            return np.array([])
        if array.ndim == 2:
            return array.flatten()
        return array
    
    def _limpar_nan(self, array, valor_padrao=0.0):
        array = self._garantir_unidimensional(array)
        if len(array) == 0:
            return array
        if np.all(np.isnan(array)):
            return np.full_like(array, valor_padrao)
        media = np.nanmean(array)
        if np.isnan(media):
            media = valor_padrao
        return np.nan_to_num(array, nan=media)
    
    def _calcular_vtec(self, tec_obliquo, elevacao_graus):
        tec_obliquo = self._garantir_unidimensional(tec_obliquo)
        elevacao_graus = self._garantir_unidimensional(elevacao_graus)
        
        tec_obliquo = self._limpar_nan(tec_obliquo)
        elevacao_graus = self._limpar_nan(elevacao_graus)
        
        if len(tec_obliquo) == 0:
            return np.array([])
        
        if len(elevacao_graus) > 0 and np.max(elevacao_graus) > 90:
            print(f"    ⚠️ Elevação > 90° detectada. Usando PTEC como VTEC.")
            return tec_obliquo
        
        if len(elevacao_graus) > 0:
            min_len = min(len(tec_obliquo), len(elevacao_graus))
            tec_obliquo = tec_obliquo[:min_len]
            elevacao_graus = elevacao_graus[:min_len]
            
            elevacao_graus = np.clip(elevacao_graus, 0, 90)
            elevacao_rad = np.radians(elevacao_graus)
            vtec = tec_obliquo * np.sin(elevacao_rad)
            return vtec
        
        return tec_obliquo
    
    def _converter_tempo(self, tempo):
        tempo = self._garantir_unidimensional(tempo)
        tempo = self._limpar_nan(tempo)
        if len(tempo) == 0:
            return np.array([])
        
        horas = (tempo % 86400) / 3600.0
        return horas
    
    def _obter_s4(self, dados):
        # Tentar S401
        s4 = dados.get('S401')
        if s4 is not None:
            s4 = self._garantir_unidimensional(s4)
            if not np.all(np.isnan(s4)):
                return self._limpar_nan(s4, valor_padrao=0.0)
        
        # Tentar S402
        s4 = dados.get('S402')
        if s4 is not None:
            s4 = self._garantir_unidimensional(s4)
            if not np.all(np.isnan(s4)):
                return self._limpar_nan(s4, valor_padrao=0.0)
        
        # Fallback: S4 baseado no SNR
        snr = dados.get('SNR1')
        if snr is not None:
            snr = self._garantir_unidimensional(snr)
            if not np.all(np.isnan(snr)):
                snr_limpo = self._limpar_nan(snr, valor_padrao=30)
                s4_estimado = 1.0 / np.sqrt(snr_limpo)
                s4_estimado = np.clip(s4_estimado, 0, 1)
                return s4_estimado
        
        return np.ones(len(dados.get('PTEC', []))) * 0.1
    
    def _filtrar_satelite(self, vtec, s4, tempo):
        vtec = self._garantir_unidimensional(vtec)
        s4 = self._garantir_unidimensional(s4)
        tempo = self._garantir_unidimensional(tempo)
        
        if len(vtec) < 50:
            return None, None, None, False
        
        if np.std(vtec) < 0.1:
            return None, None, None, False
        
        if np.max(vtec) < 0.01 or np.max(vtec) > 300:
            return None, None, None, False
        
        return vtec, s4, tempo, True
    
    def processar_medias_diarias(self):
        print("\n" + "="*60)
        print("PROCESSANDO DADOS - VTEC")
        print("="*60)
        
        constelacoes_remover = []
        
        for constelacao, satelites in self.dados_completos.items():
            print(f"\nConstelação: {constelacao}")
            print(f"  Satélites encontrados: {len(satelites)}")
            
            todos_vtec = []
            todos_s4 = []
            todos_tempo = []
            satelites_validos = 0
            
            for svid, dados in satelites.items():
                try:
                    tec_obliquo = dados.get('PTEC')
                    elevacao = dados.get('ELEV')
                    
                    if tec_obliquo is None:
                        continue
                    
                    vtec = self._calcular_vtec(tec_obliquo, elevacao)
                    
                    if len(vtec) < 50:
                        continue
                    
                    s4 = self._obter_s4(dados)
                    
                    if len(s4) != len(vtec):
                        min_len = min(len(vtec), len(s4))
                        vtec = vtec[:min_len]
                        s4 = s4[:min_len]
                    
                    tempo = dados.get('S_TW')
                    if tempo is not None:
                        tempo = self._garantir_unidimensional(tempo)
                        if len(tempo) > len(vtec):
                            tempo = tempo[:len(vtec)]
                        elif len(tempo) < len(vtec):
                            vtec = vtec[:len(tempo)]
                            s4 = s4[:len(tempo)]
                    else:
                        tempo = np.linspace(0, 1440, len(vtec))
                    
                    vtec_f, s4_f, tempo_f, valido = self._filtrar_satelite(vtec, s4, tempo)
                    
                    if valido:
                        todos_vtec.append(vtec_f)
                        todos_s4.append(s4_f)
                        todos_tempo.append(tempo_f)
                        satelites_validos += 1
                        
                except Exception as e:
                    continue
            
            print(f"  Satélites válidos: {satelites_validos}")
            
            if satelites_validos < 2:
                print(f"  ⚠️ Menos de 2 satélites válidos - IGNORANDO {constelacao}")
                constelacoes_remover.append(constelacao)
                continue
            
            tamanho_min = min([len(t) for t in todos_tempo])
            print(f"  Tamanho mínimo comum: {tamanho_min} pontos")
            
            if tamanho_min < 50:
                print(f"  ⚠️ Tamanho muito pequeno - IGNORANDO {constelacao}")
                constelacoes_remover.append(constelacao)
                continue
            
            vtec_array = np.array([v[:tamanho_min] for v in todos_vtec])
            s4_array = np.array([s[:tamanho_min] for s in todos_s4])
            tempo_array = todos_tempo[0][:tamanho_min]
            
            vtec_medio = np.median(vtec_array, axis=0)
            s4_medio = np.median(s4_array, axis=0)
            
            horas = self._converter_tempo(tempo_array)
            
            vtec_std = np.std(vtec_medio)
            print(f"  VTEC std: {vtec_std:.3f}")
            
            # CRITÉRIO PRINCIPAL: DESCARTAR CONSTELAÇÕES COM DADOS CONSTANTES
            if vtec_std < 0.3:
                print(f"  ⚠️ VTEC CONSTANTE (std < 0.3) - IGNORANDO {constelacao}")
                constelacoes_remover.append(constelacao)
                continue
            
            self.dados_media[constelacao] = {
                'horas': horas,
                'vtec': vtec_medio,
                's4': s4_medio,
                'num_satelites': satelites_validos,
                'vtec_std': vtec_std
            }
            
            print(f"  ✅ {constelacao} APROVADO: VTEC médio {np.mean(vtec_medio):.2f} TECU")
        
        # Remover constelações ruins
        for const in constelacoes_remover:
            if const in self.dados_completos:
                del self.dados_completos[const]
                print(f"\n❌ Constelação removida: {const}")
        
        print(f"\nTotal de constelações aprovadas: {len(self.dados_media)}")
        print(f"Constelações: {list(self.dados_media.keys())}")
        return self.dados_media
    
    def detectar_bolhas(self):
        eventos = []
        
        print("\n" + "="*60)
        print("DETECTANDO BOLHAS")
        print("="*60)
        
        for constelacao, dados in self.dados_media.items():
            print(f"\n{constelacao}")
            
            horas = dados['horas']
            vtec = dados['vtec']
            s4 = dados['s4']
            
            mascara = (vtec > 0) & ~np.isnan(vtec) & ~np.isnan(s4)
            if not np.any(mascara):
                print("  Sem dados válidos")
                continue
            
            horas = horas[mascara]
            vtec = vtec[mascara]
            s4 = s4[mascara]
            
            mascara_dia = (horas >= 6) & (horas <= 18)
            if np.any(mascara_dia):
                vtec_medio_dia = np.mean(vtec[mascara_dia])
            else:
                vtec_medio_dia = np.mean(vtec)
            
            if vtec_medio_dia <= 0:
                print("  VTEC médio <= 0")
                continue
            
            print(f"  VTEC médio diário: {vtec_medio_dia:.2f} TECU")
            
            eventos_const = []
            for i in range(len(horas)):
                hora = horas[i]
                
                if not (hora >= 20 or hora <= 2):
                    continue
                
                if vtec[i] > 0:
                    queda = (1 - vtec[i] / vtec_medio_dia) * 100
                    if queda > 25 and s4[i] > 0.20:
                        eventos_const.append({
                            'constelacao': constelacao,
                            'horario': float(hora),
                            'vtec': float(vtec[i]),
                            's4': float(s4[i]),
                            'queda': float(queda),
                            'vtec_medio': float(vtec_medio_dia)
                        })
            
            eventos.extend(eventos_const)
            print(f"  Eventos: {len(eventos_const)}")
        
        self.eventos = eventos
        print(f"\nTotal de eventos: {len(eventos)}")
        return eventos
    
    def gerar_relatorio_eventos(self):
        if not self.eventos:
            self.detectar_bolhas()
        
        linhas = []
        linhas.append("=" * 60)
        linhas.append(f"RELATÓRIO DE EVENTOS - {self.data.strftime('%d/%m/%Y') if self.data else 'Data Desconhecida'}")
        linhas.append("=" * 60)
        linhas.append(f"Total de eventos detectados: {len(self.eventos)}")
        linhas.append("")
        
        if self.eventos:
            for i, evento in enumerate(self.eventos, 1):
                linhas.append(f"Evento #{i}")
                linhas.append(f"  Constelação: {evento['constelacao']}")
                linhas.append(f"  Horário: {evento['horario']:.1f}h")
                linhas.append(f"  VTEC: {evento['vtec']:.2f} TECU")
                linhas.append(f"  S4: {evento['s4']:.3f}")
                linhas.append(f"  Queda: {evento['queda']:.1f}%")
                linhas.append(f"  VTEC Médio Diário: {evento['vtec_medio']:.2f} TECU")
                linhas.append("-" * 40)
        else:
            linhas.append("Nenhum evento detectado.")
        
        return "\n".join(linhas)
    
    def salvar_relatorio(self, caminho_saida):
        relatorio = self.gerar_relatorio_eventos()
        os.makedirs(os.path.dirname(caminho_saida), exist_ok=True)
        with open(caminho_saida, 'w', encoding='utf-8') as f:
            f.write(relatorio)
        print(f"Relatório salvo: {caminho_saida}")