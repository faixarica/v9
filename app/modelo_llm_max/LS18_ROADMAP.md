
---

```markdown
# 🚀 Roadmap Oficial — LS18 / MS18 (Next-Gen 2026)

## 🎯 Visão
Criar a geração mais avançada de modelos FaixaBet, usando:

- **Features v5 (estatística dinâmica + séries longas + eventos globais)**
- **Transformer híbrido + Mamba 2 + RWKV (state-space)**
- **Ensemble Dinâmico Inteligente**
- **Auto-Tuning baseado em telemetria real**

---

# 🧱 FEATURES V5 (Lotofácil e Mega)

### 1. Estratificação dinâmica temporal
- Probabilidades em janelas adaptativas:
  - 5 últimos concursos  
  - 30 últimos concursos  
  - 100 últimos  
  - 500 últimos  
  - série inteira

### 2. Comportamento inter-concursos
- Distância média  
- % repetição  
- % números novos  
- padrões de saltos  

### 3. Modelos estatísticos avançados
- PCA das probabilidades  
- embeddings de frequência  
- decomposição SVD  

### 4. Auto-lag + Fourier
- períodos comportamentais  
- sazonalidade  

### 5. Encoding “gramatical” da Lotofácil
- representando repetições como tokens especiais  

---

# 🧠 MODELO LS18 (arquitetura)
- Encoder: **Mamba 2**  
- Decoder auxiliar: **Transformer 4-heads**  
- Attention com **FlashAttention2**  
- Output: **Blockwise Sigmoid 25**  

---

# 🔮 ENSEMBLE DINÂMICO
G3, S2 e V4 deixam de ser fixos.

Agora:

- pesos mudam diariamente  
- baseados na telemetria real (acertos dos últimos 60 concursos)  
- cada modelo ganha nota dinâmica  
- ensemble se reajusta sozinho  

---

# 📊 TELEMETRIA 2.0
- salva performance por lote  
- salva distribuição de probabilidade do modelo  
- curva especial de “viés”  

---

# 📅 Cronograma
1. **Dez 2025:** features v5  
2. **Jan 2026:** dataset LS18  
3. **Fev 2026:** LS18 training  
4. **Mar 2026:** ensemble dinâmico  
5. **Abr 2026:** release público  

