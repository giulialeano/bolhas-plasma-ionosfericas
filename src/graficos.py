import matplotlib.pyplot as plt
import numpy as np
import os

class GeradorGraficos:
    """
    Gera gráficos profissionais das bolhas de plasma.
    Média de todas as constelações, sem linhas extras.
    """
    
    def __init__(self, dados_media, eventos, data):
        self.dados_media = dados_media
        self.eventos = eventos
        self.data = data
    
    def _calcular_media_geral(self):
        """
        Calcula a média de VTEC e S4 entre TODAS as constelações.
        """
        if not self.dados_media:
            return None, None, None
        
        todos_vtec = []
        todos_s4 = []
        horas_referencia = None
        
        for constelacao, dados in self.dados_media.items():
            horas = dados['horas']
            vtec = dados['vtec']
            s4 = dados['s4']
            
            # Pular constelações com dados constantes
            if np.std(vtec) < 0.3:
                print(f"  ⚠️ {constelacao} ignorada na média (std < 0.3)")
                continue
            
            if horas_referencia is None:
                horas_referencia = horas
            
            min_len = min(len(horas), len(vtec), len(s4))
            if min_len < len(horas_referencia):
                horas_referencia = horas_referencia[:min_len]
            
            todos_vtec.append(vtec[:min_len])
            todos_s4.append(s4[:min_len])
        
        if not todos_vtec:
            print("  ⚠️ Nenhuma constelação com dados válidos para a média")
            return None, None, None
        
        vtec_array = np.array(todos_vtec)
        s4_array = np.array(todos_s4)
        
        vtec_medio = np.median(vtec_array, axis=0)
        s4_medio = np.median(s4_array, axis=0)
        
        print(f"  ✅ Média calculada com {len(todos_vtec)} constelações")
        print(f"     VTEC médio: {np.mean(vtec_medio):.2f} TECU")
        print(f"     S4 médio: {np.mean(s4_medio):.3f}")
        
        return horas_referencia, vtec_medio, s4_medio
    
    def grafico_dia(self, salvar=True, caminho=None):
        """
        Gera um único gráfico com a MÉDIA de todas as constelações.
        """
        if not self.dados_media:
            print("Sem dados para gerar gráfico")
            return
        
        horas, vtec_medio, s4_medio = self._calcular_media_geral()
        
        if horas is None:
            print("Não foi possível calcular a média geral")
            return
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
        fig.patch.set_facecolor('#FAFAFA')
        
        # ===== GRÁFICO SUPERIOR: VTEC MÉDIO =====
        ax1.plot(horas, vtec_medio, 
                color='#1A1A2E', linewidth=3, label='VTEC Médio')
        
        # Destacar eventos no VTEC (quedas > 30%)
        for e in self.eventos:
            if e['queda'] > 30:
                ax1.scatter(e['horario'], e['vtec'], 
                           color='red', s=150, marker='*', 
                           edgecolors='white', linewidth=1.5, zorder=5)
                ax1.annotate(f'{e["queda"]:.0f}%', 
                            (e['horario'], e['vtec']),
                            xytext=(5, 10), textcoords='offset points',
                            color='red', fontsize=10, fontweight='bold')
        
        ax1.set_ylabel('VTEC (TECU)', fontsize=13, fontweight='bold')
        ax1.set_title(f'Bolhas de Plasma - {self.data.strftime("%d/%m/%Y")}', 
                      fontsize=16, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.set_xlim(0, 24)
        ax1.legend(loc='upper left')
        
        # Área noturna
        ax1.axvspan(20, 24, alpha=0.08, color='blue')
        ax1.axvspan(0, 2, alpha=0.08, color='blue')
        ymin, ymax = ax1.get_ylim()
        ax1.text(22, ymax*0.95, 'NOTURNO\n20h-02h', 
                 color='#457B9D', ha='center', va='top', fontsize=10, fontweight='bold')
        
        # ===== GRÁFICO INFERIOR: S4 MÉDIO =====
        ax2.plot(horas, s4_medio, 
                color='#1A1A2E', linewidth=2.5, linestyle='--', label='S4 Médio')
        
        # Destacar eventos no S4 (S4 > 0.25)
        for e in self.eventos:
            if e['s4'] > 0.25:
                ax2.scatter(e['horario'], e['s4'],
                           color='#FF6600', s=100, marker='^',
                           edgecolors='white', linewidth=1.5, zorder=5)
        
        ax2.set_xlabel('Hora Local', fontsize=13, fontweight='bold')
        ax2.set_ylabel('S4', fontsize=13, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        ax2.set_xlim(0, 24)
        ax2.set_xticks(range(0, 25, 2))
        ax2.set_xticklabels([f'{h}h' for h in range(0, 25, 2)])
        
        # Área noturna
        ax2.axvspan(20, 24, alpha=0.08, color='blue')
        ax2.axvspan(0, 2, alpha=0.08, color='blue')
        
        # Resumo no canto
        n_eventos = len(self.eventos)
        n_constelacoes = len(self.dados_media)
        ax2.text(0.02, 0.98, f'Eventos: {n_eventos}\nConstelações: {n_constelacoes}',
                 transform=ax2.transAxes, va='top',
                 bbox=dict(boxstyle='round', facecolor='white', alpha=0.8),
                 fontsize=10)
        
        plt.tight_layout()
        
        if salvar:
            if caminho is None:
                os.makedirs('resultados/graficos', exist_ok=True)
                caminho = f'resultados/graficos/bolhas_{self.data.strftime("%Y%m%d")}.png'
            else:
                os.makedirs(os.path.dirname(caminho), exist_ok=True)
            plt.savefig(caminho, dpi=300, bbox_inches='tight', facecolor='white')
            print(f'Gráfico salvo: {caminho}')
        
        plt.show()
        return fig