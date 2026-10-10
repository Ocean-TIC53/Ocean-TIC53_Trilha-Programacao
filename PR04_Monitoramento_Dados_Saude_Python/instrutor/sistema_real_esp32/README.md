# Edições futuras - aquisição com ESP32-S3

Esta pasta preserva a possibilidade de substituir o gerador sintético por uma fonte física sem alterar o trabalho do aluno.

## Arquitetura proposta

`Sensores -> ESP32-S3 -> USB/UART (ou gateway Wi-Fi) -> publicador Python -> Firebase RTDB -> Colabs dos alunos`

O ponto de compatibilidade é o **contrato de dados** publicado em `oficina/live`.

### Possível configuração de sensores

- **ECG:** eletrodos + front-end analógico/ADC dedicado. Para demonstrações simples, um módulo como AD8232 pode ser usado; para aquisição mais robusta, considerar um AFE/ADC biomédico dedicado (por exemplo, família ADS129x).
- **PPG:** sensor óptico com canais vermelho e infravermelho, como MAX30102 ou equivalente.
- **Controlador:** ESP32-S3, responsável pela amostragem, `sample_index`, empacotamento local e envio ao gateway/publicador.

A escolha dos sensores não é requisito dos notebooks dos alunos. O dispositivo deve produzir, no mínimo, uma linha JSON por amostra no formato:

```json
{"sample_index":12345,"ecg":0.51,"ppg_ir":53210,"ppg_red":42100,"source":"HW"}
```

O `sample_index` deve nascer no lado da aquisição e permanecer monotônico. O arquivo `publicador_serial_firebase.py` agrupa as amostras e publica o mesmo esquema da oficina.

## Segurança para uma versão com dados reais

A arquitetura didática desta oficina usa apenas dados sintéticos. Em uma aplicação clínica, não exponha um banco aberto diretamente ao dispositivo/cliente. Prefira gateway/backend autenticado, HTTPS/TLS, controle de acesso e auditoria. Para interoperabilidade, avaliar HL7 FHIR no nível de dados clínicos/APIs e a família ISO/IEEE 11073 para comunicação com dispositivos quando aplicável.

Firebase base usada apenas na oficina: `https://oficina-python-saude-teste-default-rtdb.firebaseio.com/`
