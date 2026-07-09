import h5py
import numpy as np

class LeitorH5:
    """
    Leitor de arquivos .h5 dos receptores GNSS ScintPi.
    """
    
    def __init__(self, caminho_arquivo):
        self.caminho = caminho_arquivo
        self.arquivo = None
        self.dados = {}
    
    def abrir(self):
        self.arquivo = h5py.File(self.caminho, 'r')
        return self
    
    def fechar(self):
        if self.arquivo:
            self.arquivo.close()
    
    def listar_sistemas(self):
        """Lista as constelações disponíveis (GPS, GLO, GAL, BDS, SBS)"""
        return list(self.arquivo.keys())
    
    def extrair_dados_satelite(self, sistema='GPS', svid='SVID001'):
        """
        Extrai dados de um satélite específico.
        """
        caminho = f"{sistema}/{svid}"
        
        dados = {
            'PTEC': self.arquivo[caminho]['PTEC'][:],
            'S401': self.arquivo[caminho]['S401'][:],
            'ELEV': self.arquivo[caminho]['ELEV'][:],
            'S_TW': self.arquivo[caminho]['S_TW'][:],
            'SNR1': self.arquivo[caminho]['SNR1'][:],
        }
        
        # Achatar arrays 2D para 1D
        for chave in dados:
            if dados[chave].ndim == 2 and dados[chave].shape[0] == 1:
                dados[chave] = dados[chave].flatten()
        
        return dados
    
    def extrair_todas_constelacoes(self):
        """Extrai dados de todas as constelações."""
        dados_completos = {}
        
        for sistema in self.listar_sistemas():
            # Pular SBS (ruído) e BDS (poucos satélites no Brasil)
            if sistema in ['SBS']:
                continue
            
            satelites = list(self.arquivo[sistema].keys())
            dados_sistema = {}
            
            for svid in satelites:
                try:
                    dados_sistema[svid] = self.extrair_dados_satelite(sistema, svid)
                except:
                    continue
            
            if dados_sistema:
                dados_completos[sistema] = dados_sistema
        
        return dados_completos