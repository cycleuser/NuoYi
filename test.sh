(dev) fred@ubuntu:~/Documents/参考文献/arXiv_45000/pdfs/arxiv$ nuoyi /home/fred/Documents/参考文献/arXiv_45000/pdfs/arxiv --batch --device cuda --existing-files skip  --output '/home/fred/Documents/参考文献/arXiv_45000/markdown' 
Input dir:  /home/fred/Documents/参考文献/arXiv_45000/pdfs/arxiv
Output dir: /home/fred/Documents/参考文献/arXiv_45000/markdown
Engine: auto
Device: cuda

[Batch] Converting 44315 files...
[Batch] 1/44315: -Qing_2002_Hawking_Radiation_of_arXiv-gr-qc-0204005.pdf - Skipping (already exists)
[Batch] 2/44315: A'Campo_1997_Real_deformations_and_arXiv-alg-geom-9710023.pdf - Skipping (already exists)
[Batch] 3/44315: ALTARELLI_2004_The_Electroweak_Interactions_arXiv-hep-ph-0406270.pdf - Skipping (already exists)
[Batch] 4/44315: ARTRU_2004_General_Constraints_on_arXiv-hep-ph-0401234.pdf - Skipping (already exists)
[Batch] 5/44315: ASAGA_2002_Possible_Suppression_of_arXiv-hep-ph-0202197.pdf - Skipping (already exists)
[Batch] 6/44315: ASAI_1999_The_Ground_and_arXiv-cond-mat-9904310.pdf - Skipping (already exists)
[Batch] 7/44315: A_1998_Microwave_Emission_by_arXiv-astro-ph-9811043.pdf - Skipping (already exists)
[Batch] 8/44315: A_1998_Resonance_Paramagnetic_Relaxation_arXiv-astro-ph-9811041.pdf - Skipping (already exists)
[Batch] 9/44315: A_1998_What_Grain_Alignment_arXiv-astro-ph-9811039.pdf - Skipping (already exists)
[Batch] 10/44315: A_2001_Stellar_Populations_in_arXiv-astro-ph-0110245.pdf - Skipping (already exists)
[Batch] 11/44315: A_2002_Spectroscopic_Dating_of_arXiv-astro-ph-0202178.pdf - Skipping (already exists)
[Batch] 12/44315: Aalseth_2004_Neutrinoless_double_beta_arXiv-hep-ph-0412300.pdf - Skipping (already exists)
[Batch] 13/44315: Aalto_2000_Complex_molecular_gas_arXiv-astro-ph-0008233.pdf - Skipping (already exists)
[Batch] 14/44315: Aalto_2001_An_Inner_Molecular_arXiv-astro-ph-0107590.pdf - Skipping (already exists)
[Batch] 15/44315: Aalto_2001_Gas_properties_in_arXiv-astro-ph-0108083.pdf
[Device] NVIDIA GPU detected: 7.6GB total, 7.6GB free
[Device] Using CUDA (sufficient VRAM: 7.6GB >= 6.0GB)
[Memory] GPU detected: 7.6GB total, 7.6GB free
/home/fred/miniconda3/envs/dev/lib/python3.12/site-packages/requests/__init__.py:113: RequestsDependencyWarning: urllib3 (2.6.3) or chardet (7.4.0.post2)/charset_normalizer (3.4.6) doesn't match a supported version!
  warnings.warn(
[Memory] Loading marker-pdf models...
[Memory] Standard mode: all models on GPU
[Memory] GPU: 7.6GB total, 7.6GB free
[Memory] Models loaded: 3.2GB used, 3.2GB reserved
[Memory] Ready for conversion
Recognizing Layout: 100%|██████████████████████████████████████████████████████████████████████████████████| 6/6 [00:02<00:00,  2.14it/s]
Running OCR Error Detection: 100%|█████████████████████████████████████████████████████████████████████████| 1/1 [00:00<00:00, 10.09it/s]
Detecting bboxes: 100%|████████████████████████████████████████████████████████████████████████████████████| 1/1 [00:00<00:00,  1.23it/s]
Recognizing Text:   0%|                                                                                           | 0/97 [00:00<?, ?it/s][Memory] OOM: CUDA out of memory. Tried to allocate 306.00 MiB. GPU 0 has a total capacity of 7.62 GiB of which 207.25 MiB is free. Including non-PyTorch memory, th...
[Memory] Insufficient memory for retry
Recognizing Text:   0%|                                                                                           | 0/97 [00:00<?, ?it/s]
[Batch] ✗ Aalto_2001_Gas_properties_in_arXiv-astro-ph-0108083.pdf: CUDA OOM
[Batch] Attempting CPU fallback...
[Memory] Converter resources cleaned up
[Memory] Converter cache cleared
[Batch] GPU memory cleared
[Device] Using CPU as requested.
[Memory] Loading marker-pdf models...
[Memory] Standard mode: all models on GPU
[Memory] GPU: 7.6GB total, 7.6GB free
[Memory] Models loaded: 0.0GB used, 0.0GB reserved
[Memory] Ready for conversion
Recognizing Layout:   0%|                     
