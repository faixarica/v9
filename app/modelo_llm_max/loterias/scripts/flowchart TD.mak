flowchart TD

%% LOTOFÁCIL
A1[Raspagem Lotofácil\nraspar_loteria.py] --> A2[prepare_real_data_ls17_v4.py]
A2 --> A3[ls17_features_v4.npy]
A2 --> A4[rows_25bin.npy]

A3 & A4 --> A5[make_ls17_dataset_v4.py]
A5 --> A6[X_ls17_v4.npy & y_ls17_v4.npy]

A4 --> A7[build_ls14_dataset.py]
A7 --> A8[X_ls14.npy & y_ls14.npy]

A3 --> A9[build_ls15_dataset.py]
A9 --> A10[X_ls15.npy & y_ls15.npy]

%% Treinos LF
A8 --> T1[train_ls14pp.py]
A10 --> T2[train_ls15pp.py]
A3 --> T3[train_ls16.py]
A6 --> T4[train_ls17_v4.py]

T1 --> Mlf14[ls14pp_final.keras]
T2 --> Mlf15[ls15pp_final.keras]
T3 --> Mlf16[ls16_final.keras]
T4 --> Mlf17[ls17_v4_transformer.keras]

%% Mega
B1[Raspagem Mega-Sena\nraspar_loteria_mega.py] --> B2[prepare_real_data_ms17_v4.py]
B2 --> B3[ms17_features_v4.npy]
B2 --> B4[rows_60bin.npy]

B3 & B4 --> B5[make_ms17_dataset_v4.py]
B5 --> B6[X_ms17_v4.npy & y_ms17_v4.npy]

%% Treino Mega
B6 --> MT1[train_ms17_v4.py]
MT1 --> Mmg17[ms17_v4_transformer.keras]

%% Ensembles finais
Mlf14 & Mlf15 --> ES[ensemble_s2.py]
Mlf14 & Mlf15 & Mlf16 --> EG[ensemble_g3.py]
Mlf14 & Mlf15 & Mlf16 & Mlf17 --> EP[ensemble_v4.py]

Mmg17 --> EMP[ensemble_m4.py]

EP --> APP[(palpites.py)]
EMP --> APP
