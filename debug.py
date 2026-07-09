import h5py
import numpy as np

# Abrir um arquivo de exemplo
caminho = 'dados/sc3_lvl3_20231013_0000_359061.4062W_72121.4453S_v326d.h5'
arquivo = h5py.File(caminho, 'r')

# Ver sistemas disponíveis
print("Sistemas:", list(arquivo.keys()))

# Ver um satélite do GPS
sistema = 'GPS'
svid = 'SVID001'

print(f"\nSatélite: {sistema}/{svid}")
print("Chaves:", list(arquivo[sistema][svid].keys()))

# Ver os dados
for chave in ['PTEC', 'ELEV', 'S_TW', 'S401']:
    dados = arquivo[sistema][svid][chave][:]
    print(f"\n{chave}:")
    print(f"  shape: {dados.shape}")
    print(f"  dtype: {dados.dtype}")
    print(f"  primeiros 10 valores: {dados.flatten()[:10] if dados.ndim > 1 else dados[:10]}")
    print(f"  min: {np.min(dados)}, max: {np.max(dados)}")
    print(f"  std: {np.std(dados)}")

arquivo.close()