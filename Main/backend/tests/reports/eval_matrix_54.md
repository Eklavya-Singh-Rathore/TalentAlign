# TalentAlign — 54-Pair Deterministic Calibration Matrix

- Generated: 2026-06-08T09:35:53.844110+00:00
- Embedding backend: **sbert**  |  LLM: **none (deterministic)**
- Resumes: 6  |  JDs: 9  |  Pairs: 54

## 1. Normalized display-score matrix (0-100)
```
Resume          JD-1    JD-2    JD-3    JD-4    JD-5    JD-6    JD-7    JD-8    JD-9
------------------------------------------------------------------------------------
AKASH           68.5    62.5    73.2    55.5    64.1    68.1    73.1    63.1    66.2
Ananya          76.3    61.7    69.5    75.7    72.6    77.6    67.6    61.4    71.1
Eklavya         82.2    64.8    79.1    66.5    66.2    70.5    61.5    66.0    73.3
Rohit           58.5    54.2    53.2    34.4    49.5    67.3    55.1    59.3    47.4
VIGNESH         85.5    68.2    77.9    63.6    63.7    75.5    74.9    72.8    73.4
Wallace         39.7    41.3    53.8    43.2    35.7    39.5    52.9    52.1    40.6
```
### raw composite %
```
Resume          JD-1    JD-2    JD-3    JD-4    JD-5    JD-6    JD-7    JD-8    JD-9
------------------------------------------------------------------------------------
AKASH           45.5    40.4    49.6    34.6    41.7    45.1    49.5    41.0    43.5
Ananya          52.4    39.8    46.4    51.8    49.0    53.5    44.7    39.5    47.7
Eklavya         57.6    42.3    54.8    43.8    43.5    47.2    39.6    43.3    49.6
Rohit           37.1    33.5    32.6    20.6    29.7    44.5    34.3    37.8    28.5
VIGNESH         61.2    45.2    53.7    41.3    41.4    51.6    51.1    49.2    49.8
Wallace         23.8    24.8    33.2    25.9    21.4    23.7    32.4    31.7    24.3
```

## 2. Match-level matrix
```
Resume                 JD-1           JD-2           JD-3           JD-4           JD-5           JD-6           JD-7           JD-8           JD-9
---------------------------------------------------------------------------------------------------------------------------------------------------
AKASH              MODERATE       MODERATE           GOOD       MODERATE       MODERATE       MODERATE           GOOD       MODERATE       MODERATE
Ananya                 GOOD       MODERATE       MODERATE           GOOD           GOOD           GOOD       MODERATE       MODERATE           GOOD
Eklavya                GOOD       MODERATE           GOOD       MODERATE       MODERATE           GOOD       MODERATE       MODERATE           GOOD
Rohit              MODERATE       MODERATE       MODERATE  BELOW AVERAGE  BELOW AVERAGE       MODERATE       MODERATE       MODERATE  BELOW AVERAGE
VIGNESH           EXCELLENT       MODERATE           GOOD       MODERATE       MODERATE           GOOD           GOOD           GOOD           GOOD
Wallace       BELOW AVERAGE  BELOW AVERAGE       MODERATE  BELOW AVERAGE  BELOW AVERAGE  BELOW AVERAGE       MODERATE       MODERATE  BELOW AVERAGE
```

## 3. Per-JD ranking (by composite)

- **JD-1** (not_specified): VIGNESH 85.5  >  Eklavya 82.2  >  Ananya 76.3  >  AKASH 68.5  >  Rohit 58.5  >  Wallace 39.7
- **JD-2** (not_specified): VIGNESH 68.2  >  Eklavya 64.8  >  AKASH 62.5  >  Ananya 61.7  >  Rohit 54.2  >  Wallace 41.3
- **JD-3** (Artificial Intelligence Intern): Eklavya 79.1  >  VIGNESH 77.9  >  AKASH 73.2  >  Ananya 69.5  >  Wallace 53.8  >  Rohit 53.2
- **JD-4** (not_specified): Ananya 75.7  >  Eklavya 66.5  >  VIGNESH 63.6  >  AKASH 55.5  >  Wallace 43.2  >  Rohit 34.4
- **JD-5** (Software Engineer - Gen Ai): Ananya 72.6  >  Eklavya 66.2  >  AKASH 64.1  >  VIGNESH 63.7  >  Rohit 49.5  >  Wallace 35.7
- **JD-6** (Full Stack Developer): Ananya 77.6  >  VIGNESH 75.5  >  Eklavya 70.5  >  AKASH 68.1  >  Rohit 67.3  >  Wallace 39.5
- **JD-7** (Diligent Java Developer): VIGNESH 74.9  >  AKASH 73.1  >  Ananya 67.6  >  Eklavya 61.5  >  Rohit 55.1  >  Wallace 52.9
- **JD-8** (Machine Learning Engineer): VIGNESH 72.8  >  Eklavya 66.0  >  AKASH 63.1  >  Ananya 61.4  >  Rohit 59.3  >  Wallace 52.1
- **JD-9** (Business Analyst): VIGNESH 73.4  >  Eklavya 73.3  >  Ananya 71.1  >  AKASH 66.2  >  Rohit 47.4  >  Wallace 40.6

## 4. Per-resume summary

Resume          avg    min    max  best/worst JD
AKASH          66.0   55.5   73.2  JD-3(73) / JD-4(55)
Ananya         70.4   61.4   77.6  JD-6(78) / JD-8(61)
Eklavya        70.0   61.5   82.2  JD-1(82) / JD-7(62)
Rohit          53.2   34.4   67.3  JD-6(67) / JD-4(34)
VIGNESH        72.8   63.6   85.5  JD-1(85) / JD-4(64)
Wallace        44.3   35.7   53.8  JD-3(54) / JD-5(36)

## 5. Component-score breakdown by JD

### JD-1
```
Resume        Compos  Skills    Proj  Intern    Work    Acad     Ach
--------------------------------------------------------------------
AKASH           68.5    0.34    0.60    0.53    0.00    0.00    0.00
Ananya          76.3    0.35    0.74    0.64    0.00    0.00    0.00
Eklavya         82.2    0.61    0.70    0.51    0.00    0.00    0.30
Rohit           58.5    0.39    0.62    0.00    0.00    0.00    0.00
VIGNESH         85.5    0.60    0.74    0.54    0.00    0.00    0.50
Wallace         39.7    0.11    0.64    0.00    0.00    0.00    0.00
(JD-gated excluded: ['Work Experience', 'Academics', 'Achievements_Certifications'])
```

### JD-2
```
Resume        Compos  Skills    Proj  Intern    Work    Acad     Ach
--------------------------------------------------------------------
AKASH           62.5    0.25    0.57    0.53    0.00    0.00    0.00
Ananya          61.7    0.20    0.60    0.59    0.00    0.00    0.00
Eklavya         64.8    0.35    0.61    0.50    0.00    0.00    0.20
Rohit           54.2    0.31    0.63    0.00    0.00    0.00    0.00
VIGNESH         68.2    0.34    0.61    0.53    0.00    0.00    0.40
Wallace         41.3    0.15    0.61    0.00    0.00    0.00    0.00
(JD-gated excluded: ['Work Experience', 'Academics', 'Achievements_Certifications'])
```

### JD-3
```
Resume        Compos  Skills    Proj  Intern    Work    Acad     Ach
--------------------------------------------------------------------
AKASH           73.2    0.38    0.63    0.60    0.00    0.00    0.00
Ananya          69.5    0.24    0.70    0.66    0.00    0.00    0.00
Eklavya         79.1    0.54    0.68    0.55    0.00    0.00    0.30
Rohit           53.2    0.29    0.63    0.00    0.00    0.00    0.00
VIGNESH         77.9    0.39    0.78    0.57    0.00    0.00    0.50
Wallace         53.8    0.25    0.73    0.00    0.00    0.00    0.00
(JD-gated excluded: ['Work Experience', 'Academics', 'Achievements_Certifications'])
```

### JD-4
```
Resume        Compos  Skills    Proj  Intern    Work    Acad     Ach
--------------------------------------------------------------------
AKASH           55.5    0.17    0.60    0.57    0.10    0.00    0.00
Ananya          75.7    0.24    0.70    0.60    1.00    0.00    0.00
Eklavya         66.5    0.41    0.69    0.53    0.04    0.00    0.30
Rohit           34.4    0.11    0.64    0.00    0.00    0.00    0.00
VIGNESH         63.6    0.28    0.66    0.54    0.12    0.00    0.50
Wallace         43.2    0.20    0.69    0.00    0.00    0.00    0.00
(JD-gated excluded: ['Academics', 'Achievements_Certifications'])
```

### JD-5
```
Resume        Compos  Skills    Proj  Intern    Work    Acad     Ach
--------------------------------------------------------------------
AKASH           64.1    0.30    0.62    0.56    0.10    0.00    0.00
Ananya          72.6    0.21    0.62    0.59    1.00    0.00    0.00
Eklavya         66.2    0.36    0.70    0.51    0.04    0.00    0.20
Rohit           49.5    0.28    0.62    0.00    0.00    0.00    0.00
VIGNESH         63.7    0.27    0.64    0.57    0.12    0.00    0.45
Wallace         35.7    0.05    0.66    0.00    0.00    0.00    0.00
(JD-gated excluded: ['Academics', 'Achievements_Certifications'])
```

### JD-6
```
Resume        Compos  Skills    Proj  Intern    Work    Acad     Ach
--------------------------------------------------------------------
AKASH           68.1    0.40    0.60    0.56    0.10    0.00    0.00
Ananya          77.6    0.30    0.64    0.59    1.00    0.00    0.00
Eklavya         70.5    0.46    0.70    0.50    0.04    0.00    0.20
Rohit           67.3    0.63    0.63    0.00    0.00    0.00    0.00
VIGNESH         75.5    0.55    0.63    0.55    0.12    0.00    0.40
Wallace         39.5    0.13    0.63    0.00    0.00    0.00    0.00
(JD-gated excluded: ['Academics', 'Achievements_Certifications'])
```

### JD-7
```
Resume        Compos  Skills    Proj  Intern    Work    Acad     Ach
--------------------------------------------------------------------
AKASH           73.1    0.38    0.72    0.57    0.21    0.00    0.00
Ananya          67.6    0.10    0.63    0.59    1.00    0.00    0.00
Eklavya         61.5    0.23    0.73    0.51    0.08    0.00    0.20
Rohit           55.1    0.34    0.70    0.00    0.00    0.00    0.00
VIGNESH         74.9    0.43    0.69    0.58    0.25    0.00    0.50
Wallace         52.9    0.30    0.69    0.00    0.00    0.00    0.00
(JD-gated excluded: ['Academics', 'Achievements_Certifications'])
```

### JD-8
```
Resume        Compos  Skills    Proj  Intern    Work    Acad     Ach
--------------------------------------------------------------------
AKASH           63.1    0.21    0.64    0.56    0.00    0.00    0.00
Ananya          61.4    0.17    0.63    0.59    0.00    0.00    0.00
Eklavya         66.0    0.28    0.71    0.53    0.00    0.00    0.25
Rohit           59.3    0.39    0.64    0.00    0.00    0.00    0.00
VIGNESH         72.8    0.34    0.73    0.54    0.00    0.00    0.50
Wallace         52.1    0.22    0.72    0.00    0.00    0.00    0.00
(JD-gated excluded: ['Work Experience', 'Academics', 'Achievements_Certifications'])
```

### JD-9
```
Resume        Compos  Skills    Proj  Intern    Work    Acad     Ach
--------------------------------------------------------------------
AKASH           66.2    0.31    0.57    0.54    0.00    0.00    0.00
Ananya          71.1    0.29    0.69    0.62    0.00    0.00    0.00
Eklavya         73.3    0.46    0.68    0.50    0.00    0.00    0.25
Rohit           47.4    0.24    0.57    0.00    0.00    0.00    0.00
VIGNESH         73.4    0.42    0.66    0.49    0.00    0.00    0.45
Wallace         40.6    0.15    0.60    0.00    0.00    0.00    0.00
(JD-gated excluded: ['Work Experience', 'Academics', 'Achievements_Certifications'])
```

## 6. Matching statistics

### matched / total JD skills
```
Resume           JD-1     JD-2     JD-3     JD-4     JD-5     JD-6     JD-7     JD-8     JD-9
---------------------------------------------------------------------------------------------
AKASH            6/15     8/29     5/10     3/16     6/17     5/10    10/24     4/14     6/16
Ananya           6/15     5/29     3/10     4/16     4/17     4/10     2/24     3/14     5/16
Eklavya         11/15    11/29     7/10     8/16     8/17     6/10     6/24     5/14     9/16
Rohit            7/15    10/29     4/10     2/16     6/17     8/10     9/24     7/14     5/16
VIGNESH         11/15    11/29     5/10     6/16     6/17     7/10    12/24     6/14     8/16
Wallace          2/15     5/29     3/10     4/16     1/17     2/10     8/24     4/14     3/16
```
### skill coverage %
```
Resume          JD-1    JD-2    JD-3    JD-4    JD-5    JD-6    JD-7    JD-8    JD-9
------------------------------------------------------------------------------------
AKASH           41.4    27.6    50.0    20.0    36.4    55.6    41.6    28.0    37.3
Ananya          37.9    18.1    30.0    26.7    22.7    38.9     9.1    20.0    28.8
Eklavya         72.4    39.0    70.0    46.7    47.0    66.7    28.6    36.0    54.2
Rohit           48.3    35.2    40.0    13.3    34.9    83.3    39.0    52.0    30.5
VIGNESH         72.4    39.0    50.0    33.3    34.9    72.2    52.0    44.0    49.1
Wallace         13.8    18.1    36.7    26.7     6.1    16.7    35.1    32.0    18.6
```

## 7. Recommendations & missing skills (per pair)

### JD-1
- **AKASH** (69, MODERATE) — recs: ['Build 1-2 projects aligned with not_specified', "Obtain certification in 'data modeling'", "Obtain certification in 'statistics'", "Obtain certification in 'keras'"]
    - missing: ['data modeling', 'statistics', 'keras', 'pytorch', 'naive bayes', 'decision forests', 'data visualization tools', 'nosql', 'data representation methods']
- **Ananya** (76, GOOD) — recs: ["Obtain certification in 'data structures'", "Obtain certification in 'software architecture'", "Obtain certification in 'statistics'"]
    - missing: ['data structures', 'software architecture', 'statistics', 'java', 'keras', 'pytorch', 'naive bayes', 'decision forests', 'nosql']
- **Eklavya** (82, GOOD) — recs: ["Obtain certification in 'software architecture'", "Obtain certification in 'keras'"]
    - missing: ['software architecture', 'keras', 'naive bayes', 'decision forests']
- **Rohit** (59, MODERATE) — recs: ['Complete an internship in data science', 'Build 1-2 projects aligned with not_specified', "Obtain certification in 'data modeling'", "Obtain certification in 'statistics'", "Obtain certification in 'keras'"]
    - missing: ['data modeling', 'statistics', 'keras', 'pytorch', 'naive bayes', 'decision forests', 'data visualization tools', 'data representation methods']
- **VIGNESH** (85, EXCELLENT) — recs: ["Obtain certification in 'software architecture'", "Obtain certification in 'keras'"]
    - missing: ['software architecture', 'keras', 'naive bayes', 'decision forests']
- **Wallace** (40, BELOW AVERAGE) — recs: ['Complete an internship in data science', 'Build 1-2 projects aligned with not_specified', "Obtain certification in 'data structures'", "Obtain certification in 'data modeling'", "Obtain certification in 'software architecture'"]
    - missing: ['data structures', 'data modeling', 'software architecture', 'statistics', 'java', 'keras', 'pytorch', 'scikit-learn', 'naive bayes', 'decision forests']

### JD-2
- **AKASH** (62, MODERATE) — recs: ['Build 1-2 projects aligned with not_specified', "Obtain certification in 'generative ai'", "Obtain certification in 'cloud platforms'", "Obtain certification in 'apis'"]
    - missing: ['game development', 'melbourne to vancouver', 'generative ai', 'cloud platforms', 'workflows involving llms', 'rag pipelines', 'intelligent agents', 'apis', 'cloud-native applications', 'cloud infrastructure']
- **Ananya** (62, MODERATE) — recs: ['Build 1-2 projects aligned with not_specified', "Obtain certification in 'generative ai'", "Obtain certification in 'cloud platforms'", "Obtain certification in 'apis'"]
    - missing: ['game development', 'melbourne to vancouver', 'generative ai', 'cloud platforms', 'workflows involving llms', 'rag pipelines', 'intelligent agents', 'apis', 'cloud-native applications', 'cloud infrastructure']
- **Eklavya** (65, MODERATE) — recs: ['Build 1-2 projects aligned with not_specified', "Obtain certification in 'generative ai'", "Obtain certification in 'apis'", "Obtain certification in 'cloud-native applications'"]
    - missing: ['melbourne to vancouver', 'generative ai', 'workflows involving llms', 'rag pipelines', 'intelligent agents', 'apis', 'cloud-native applications', 'cloud infrastructure', 'ml application development', 'exposure to technologies']
- **Rohit** (54, MODERATE) — recs: ['Complete an internship in data science', 'Build 1-2 projects aligned with not_specified', "Obtain certification in 'machine learning'", "Obtain certification in 'generative ai'", "Obtain certification in 'cloud-native applications'"]
    - missing: ['game development', 'melbourne to vancouver', 'machine learning', 'generative ai', 'workflows involving llms', 'rag pipelines', 'intelligent agents', 'cloud-native applications', 'deployment pipelines', 'data science']
- **VIGNESH** (68, MODERATE) — recs: ['Build 1-2 projects aligned with not_specified', "Obtain certification in 'generative ai applications'", "Obtain certification in 'apis'", "Obtain certification in 'cloud-native applications'"]
    - missing: ['melbourne to vancouver', 'generative ai applications', 'workflows involving llms', 'rag pipelines', 'intelligent agents', 'apis', 'cloud-native applications', 'cloud infrastructure', 'deployment pipelines', 'ml application development']
- **Wallace** (41, BELOW AVERAGE) — recs: ['Complete an internship in data science', 'Build 1-2 projects aligned with not_specified', "Obtain certification in 'generative ai'", "Obtain certification in 'cloud platforms'", "Obtain certification in 'cloud infrastructure'"]
    - missing: ['game development', 'melbourne to vancouver', 'generative ai', 'cloud platforms', 'workflows involving llms', 'rag pipelines', 'intelligent agents', 'cloud infrastructure', 'deployment pipelines', 'data science']

### JD-3
- **AKASH** (73, GOOD) — recs: ['Build 1-2 projects aligned with Artificial Intelligence Intern', "Obtain certification in 'tensorflow'", "Obtain certification in 'academic ai projects'", "Obtain certification in 'practical ai'"]
    - missing: ['structured problem-solving', 'tensorflow', 'pytorch basics', 'academic ai projects', 'practical ai']
- **Ananya** (70, MODERATE) — recs: ["Obtain certification in 'artificial intelligence'", "Obtain certification in 'tensorflow'", "Obtain certification in 'academic ai projects'"]
    - missing: ['artificial intelligence', 'structured problem-solving', 'tensorflow', 'pytorch basics', 'academic ai projects', 'intelligent data systems', 'practical ai']
- **Eklavya** (79, GOOD) — recs: ['Build 1-2 projects aligned with Artificial Intelligence Intern', "Obtain certification in 'tensorflow'", "Obtain certification in 'practical ai'"]
    - missing: ['structured problem-solving', 'tensorflow', 'practical ai']
- **Rohit** (53, MODERATE) — recs: ['Complete an internship in data science', 'Build 1-2 projects aligned with Artificial Intelligence Intern', "Obtain certification in 'tensorflow'", "Obtain certification in 'machine learning fundamentals'", "Obtain certification in 'academic ai projects'"]
    - missing: ['structured problem-solving', 'tensorflow', 'pytorch basics', 'machine learning fundamentals', 'academic ai projects', 'practical ai']
- **VIGNESH** (78, GOOD) — recs: ["Obtain certification in 'tensorflow'", "Obtain certification in 'academic ai projects'", "Obtain certification in 'practical ai'"]
    - missing: ['structured problem-solving', 'tensorflow', 'pytorch basics', 'academic ai projects', 'practical ai']
- **Wallace** (54, MODERATE) — recs: ['Complete an internship in data science', "Obtain certification in 'tensorflow'", "Obtain certification in 'academic ai projects'", "Obtain certification in 'intelligent data systems'"]
    - missing: ['structured problem-solving', 'tensorflow', 'pytorch basics', 'academic ai projects', 'intelligent data systems', 'data science', 'practical ai']

### JD-4
- **AKASH** (55, MODERATE) — recs: ['Build 1-2 projects aligned with not_specified', 'Gain work experience in data science', "Obtain certification in 'tensorflow'", "Obtain certification in 'keras'", "Obtain certification in 'pytorch'"]
    - missing: ['transformer models', 'tensorflow', 'keras', 'pytorch', 'large language models', 'learning models', 'product managers', 'sentiment detection', 'openai', 'open-source models']
- **Ananya** (76, GOOD) — recs: ["Obtain certification in 'neural networks'", "Obtain certification in 'tensorflow'", "Obtain certification in 'keras'"]
    - missing: ['neural networks', 'transformer models', 'tensorflow', 'keras', 'pytorch', 'large language models', 'product managers', 'sentiment detection', 'openai', 'langchain']
- **Eklavya** (67, MODERATE) — recs: ['Build 1-2 projects aligned with not_specified', 'Gain work experience in data science', "Obtain certification in 'tensorflow'", "Obtain certification in 'keras'", "Obtain certification in 'large language models'"]
    - missing: ['tensorflow', 'keras', 'large language models', 'product managers', 'sentiment detection', 'openai', 'open-source models', 'langchain']
- **Rohit** (34, BELOW AVERAGE) — recs: ['Complete an internship in data science', 'Build 1-2 projects aligned with not_specified', 'Gain work experience in data science', "Obtain certification in 'machine learning'", "Obtain certification in 'tensorflow'", "Obtain certification in 'keras'"]
    - missing: ['machine learning', 'transformer models', 'tensorflow', 'keras', 'pytorch', 'large language models', 'learning models', 'product managers', 'sentiment detection', 'openai']
- **VIGNESH** (64, MODERATE) — recs: ['Build 1-2 projects aligned with not_specified', 'Gain work experience in data science', "Obtain certification in 'neural networks'", "Obtain certification in 'tensorflow'", "Obtain certification in 'keras'"]
    - missing: ['neural networks', 'transformer models', 'tensorflow', 'keras', 'large language models', 'product managers', 'sentiment detection', 'openai', 'open-source models', 'langchain']
- **Wallace** (43, BELOW AVERAGE) — recs: ['Complete an internship in data science', 'Build 1-2 projects aligned with not_specified', 'Gain work experience in data science', "Obtain certification in 'neural networks'", "Obtain certification in 'tensorflow'", "Obtain certification in 'keras'"]
    - missing: ['neural networks', 'transformer models', 'tensorflow', 'keras', 'pytorch', 'large language models', 'product managers', 'openai', 'open-source models', 'langchain']

### JD-5
- **AKASH** (64, MODERATE) — recs: ['Build 1-2 projects aligned with Software Engineer - Gen Ai', 'Gain work experience in software dev', "Obtain certification in 'langchain'", "Obtain certification in 'model evaluation frameworks'", "Obtain certification in 'google adk a2a'"]
    - missing: ['llm orchestration frameworks', 'langchain', 'rag architectures', 'embedding techniques', 'model evaluation frameworks', 'efficient retrieval methods', 'prompt engineering techniques', 'cd pipelines', 'financial crimes', 'google adk a2a']
- **Ananya** (73, GOOD) — recs: ['Build 1-2 projects aligned with Software Engineer - Gen Ai', "Obtain certification in 'java'", "Obtain certification in 'langchain'", "Obtain certification in 'ui'"]
    - missing: ['java', 'llm orchestration frameworks', 'langchain', 'rag architectures', 'embedding techniques', 'ui', 'vector databases', 'prompt engineering techniques', 'containerization', 'microservices architecture']
- **Eklavya** (66, MODERATE) — recs: ['Gain work experience in software dev', "Obtain certification in 'langchain'", "Obtain certification in 'ui'", "Obtain certification in 'containerization'"]
    - missing: ['llm orchestration frameworks', 'langchain', 'rag architectures', 'embedding techniques', 'ui', 'containerization', 'microservices architecture', 'financial crimes', 'openai apis']
- **Rohit** (50, BELOW AVERAGE) — recs: ['Complete an internship in software dev', 'Build 1-2 projects aligned with Software Engineer - Gen Ai', 'Gain work experience in software dev', "Obtain certification in 'langchain'", "Obtain certification in 'ui'", "Obtain certification in 'containerization'"]
    - missing: ['llm orchestration frameworks', 'langchain', 'rag architectures', 'embedding techniques', 'ui', 'efficient retrieval methods', 'containerization', 'microservices architecture', 'cd pipelines', 'financial crimes']
- **VIGNESH** (64, MODERATE) — recs: ['Build 1-2 projects aligned with Software Engineer - Gen Ai', 'Gain work experience in software dev', "Obtain certification in 'langchain'", "Obtain certification in 'ui'", "Obtain certification in 'containerization'"]
    - missing: ['llm orchestration frameworks', 'langchain', 'rag architectures', 'embedding techniques', 'ui', 'vector databases', 'containerization', 'microservices architecture', 'cd pipelines', 'financial crimes']
- **Wallace** (36, BELOW AVERAGE) — recs: ['Complete an internship in software dev', 'Build 1-2 projects aligned with Software Engineer - Gen Ai', 'Gain work experience in software dev', "Obtain certification in 'java'", "Obtain certification in 'langchain'", "Obtain certification in 'model evaluation frameworks'"]
    - missing: ['java', 'llm orchestration frameworks', 'langchain', 'rag architectures', 'embedding techniques', 'model evaluation frameworks', 'ui', 'vector databases', 'efficient retrieval methods', 'containerization']

### JD-6
- **AKASH** (68, MODERATE) — recs: ['Build 1-2 projects aligned with Full Stack Developer', 'Gain work experience in software dev', "Obtain certification in 'aws'", "Obtain certification in 'apis'", "Obtain certification in 'ms office'"]
    - missing: ['object-oriented design', 'aws', 'project planning', 'apis', 'ms office']
- **Ananya** (78, GOOD) — recs: ['Build 1-2 projects aligned with Full Stack Developer', "Obtain certification in 'amazon web services'", "Obtain certification in 'apis'"]
    - missing: ['object-oriented design', 'amazon web services', 'object oriented design', 'project planning', 'application software', 'apis']
- **Eklavya** (70, GOOD) — recs: ['Build 1-2 projects aligned with Full Stack Developer', 'Gain work experience in software dev', "Obtain certification in 'apis'", "Obtain certification in 'ms office'"]
    - missing: ['object-oriented design', 'project planning', 'apis', 'ms office']
- **Rohit** (67, MODERATE) — recs: ['Complete an internship in software dev', 'Build 1-2 projects aligned with Full Stack Developer', 'Gain work experience in software dev', "Obtain certification in 'ms office'"]
    - missing: ['project planning', 'ms office']
- **VIGNESH** (75, GOOD) — recs: ['Build 1-2 projects aligned with Full Stack Developer', 'Gain work experience in software dev', "Obtain certification in 'apis'"]
    - missing: ['object-oriented design', 'project planning', 'apis']
- **Wallace** (39, BELOW AVERAGE) — recs: ['Complete an internship in software dev', 'Build 1-2 projects aligned with Full Stack Developer', 'Gain work experience in software dev', "Obtain certification in 'amazon web services'", "Obtain certification in 'aws'", "Obtain certification in 'data structures'"]
    - missing: ['object-oriented design', 'amazon web services', 'aws', 'object oriented design', 'computer science', 'data structures', 'project planning', 'ms office']

### JD-7
- **AKASH** (73, GOOD) — recs: ['Gain work experience in software dev', "Obtain certification in 'mysql'", "Obtain certification in 'nosql'", "Obtain certification in 'scrapy cloud'"]
    - missing: ['mysql', 'web apis', 'efficient code', 'nosql', 'nginx plus', 'app engine', 'scrapy cloud', 'pusher.io', 'getstream.io', 'postmark app']
- **Ananya** (68, MODERATE) — recs: ['Build 1-2 projects aligned with Diligent Java Developer', "Obtain certification in 'java'", "Obtain certification in 'mysql'", "Obtain certification in 'rest'"]
    - missing: ['spring boot', 'java', 'mysql', 'web apis', 'rest', 'efficient code', 'nosql', 'nginx plus', 'app engine', 'firebase hosting']
- **Eklavya** (62, MODERATE) — recs: ['Gain work experience in software dev', "Obtain certification in 'rest'", "Obtain certification in 'nosql'", "Obtain certification in 'pusher.io'"]
    - missing: ['spring boot', 'web apis', 'rest', 'nosql', 'nginx plus', 'app engine', 'firebase hosting', 'pusher.io', 'getstream.io', 'postmark app']
- **Rohit** (55, MODERATE) — recs: ['Complete an internship in software dev', 'Build 1-2 projects aligned with Diligent Java Developer', 'Gain work experience in software dev', "Obtain certification in 'rest'", "Obtain certification in 'nosql'", "Obtain certification in 'pusher.io'"]
    - missing: ['spring boot', 'rest', 'efficient code', 'nosql', 'nginx plus', 'app engine', 'pusher.io', 'getstream.io', 'postmark app', 'as2 gateway']
- **VIGNESH** (75, GOOD) — recs: ['Build 1-2 projects aligned with Diligent Java Developer', 'Gain work experience in software dev', "Obtain certification in 'nosql'", "Obtain certification in 'pusher.io'", "Obtain certification in 'getstream.io'"]
    - missing: ['spring boot', 'nosql', 'nginx plus', 'app engine', 'firebase hosting', 'pusher.io', 'getstream.io', 'postmark app', 'as2 gateway', 'gitlab']
- **Wallace** (53, MODERATE) — recs: ['Complete an internship in software dev', 'Build 1-2 projects aligned with Diligent Java Developer', 'Gain work experience in software dev', "Obtain certification in 'database'", "Obtain certification in 'java'", "Obtain certification in 'mysql'"]
    - missing: ['spring boot', 'database', 'java', 'mysql', 'nosql', 'nginx plus', 'app engine', 'scrapy cloud', 'pusher.io', 'getstream.io']

### JD-8
- **AKASH** (63, MODERATE) — recs: ['Build 1-2 projects aligned with Machine Learning Engineer', "Obtain certification in 'cloud storage'", "Obtain certification in 'apis'", "Obtain certification in 'cloud platforms'"]
    - missing: ['simple rag concepts', 'memory fundamentals', 'cloud storage', 'apis', 'ml development', 'ml concepts', 'cloud platforms', 'preferably gcp', 'ai workflows', 'cloud run']
- **Ananya** (61, MODERATE) — recs: ['Build 1-2 projects aligned with Machine Learning Engineer', "Obtain certification in 'cloud storage'", "Obtain certification in 'apis'", "Obtain certification in 'data engineering'"]
    - missing: ['simple rag concepts', 'tool integration', 'memory fundamentals', 'cloud storage', 'apis', 'data engineering', 'ml development', 'ml concepts', 'cloud platforms', 'ai workflows']
- **Eklavya** (66, MODERATE) — recs: ["Obtain certification in 'apis'", "Obtain certification in 'preferably gcp'", "Obtain certification in 'ai workflows'"]
    - missing: ['simple rag concepts', 'tool integration', 'memory fundamentals', 'apis', 'ml development', 'ml concepts', 'preferably gcp', 'ai workflows', 'cloud run']
- **Rohit** (59, MODERATE) — recs: ['Complete an internship in data science', 'Build 1-2 projects aligned with Machine Learning Engineer', "Obtain certification in 'preferably gcp'", "Obtain certification in 'ai workflows'", "Obtain certification in 'cloud run'"]
    - missing: ['simple rag concepts', 'memory fundamentals', 'ml development', 'ml concepts', 'preferably gcp', 'ai workflows', 'cloud run']
- **VIGNESH** (73, GOOD) — recs: ["Obtain certification in 'apis'", "Obtain certification in 'preferably gcp'", "Obtain certification in 'ai workflows'"]
    - missing: ['simple rag concepts', 'tool integration', 'memory fundamentals', 'apis', 'ml development', 'preferably gcp', 'ai workflows', 'cloud run']
- **Wallace** (52, MODERATE) — recs: ['Complete an internship in data science', "Obtain certification in 'cloud storage'", "Obtain certification in 'data engineering'", "Obtain certification in 'preferably gcp'"]
    - missing: ['simple rag concepts', 'tool integration', 'memory fundamentals', 'cloud storage', 'data engineering', 'ml development', 'preferably gcp', 'ai workflows', 'cloud run', 'data handling policies']

### JD-9
- **AKASH** (66, MODERATE) — recs: ['Build 1-2 projects aligned with Business Analyst', "Obtain certification in 'advanced analytics'", "Obtain certification in 'data visualization'"]
    - missing: ['statistical techniques', 'nonlinear models', 'logistic regression', 'macroeconomic forecast', 'cluster analysis', 'cards pl', 'forecasting methodologies', 'credit card', 'advanced analytics', 'data visualization']
- **Ananya** (71, GOOD) — recs: ['Build 1-2 projects aligned with Business Analyst', "Obtain certification in 'neural networks'", "Obtain certification in 'advanced analytics'"]
    - missing: ['statistical techniques', 'nonlinear models', 'logistic regression', 'macroeconomic forecast', 'decision trees', 'cluster analysis', 'neural networks', 'cards pl', 'forecasting methodologies', 'credit card']
- **Eklavya** (73, GOOD) — recs: ['Build 1-2 projects aligned with Business Analyst']
    - missing: ['logistic regression', 'macroeconomic forecast', 'decision trees', 'cluster analysis', 'cards pl', 'forecasting methodologies', 'credit card']
- **Rohit** (47, BELOW AVERAGE) — recs: ['Complete an internship in data science', 'Build 1-2 projects aligned with Business Analyst', "Obtain certification in 'machine learning'", "Obtain certification in 'data visualization'"]
    - missing: ['statistical techniques', 'nonlinear models', 'logistic regression', 'macroeconomic forecast', 'decision trees', 'cluster analysis', 'cards pl', 'forecasting methodologies', 'credit card', 'machine learning']
- **VIGNESH** (73, GOOD) — recs: ['Build 1-2 projects aligned with Business Analyst', "Obtain certification in 'neural networks'", "Obtain certification in 'advanced analytics'"]
    - missing: ['nonlinear models', 'macroeconomic forecast', 'cluster analysis', 'neural networks', 'cards pl', 'forecasting methodologies', 'credit card', 'advanced analytics']
- **Wallace** (41, BELOW AVERAGE) — recs: ['Complete an internship in data science', 'Build 1-2 projects aligned with Business Analyst', "Obtain certification in 'sql'", "Obtain certification in 'data science'", "Obtain certification in 'advanced analytics'"]
    - missing: ['sql', 'statistical techniques', 'nonlinear models', 'logistic regression', 'macroeconomic forecast', 'decision trees', 'cluster analysis', 'cards pl', 'forecasting methodologies', 'credit card']
