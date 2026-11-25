# Roteiro de vídeo — até 2 minutos

**Objetivo:** gravar a equipe apresentando o problema e demonstrando a aplicação. Os tempos abaixo são aproximados; ensaiem e confirmem que o vídeo final tem no máximo dois minutos. Os nomes dos integrantes podem ser incluídos na gravação.

## 0:00–0:20 — O problema

> “No Bovinu’S Augusta, o cliente monta seu prato e depois pesa a comida. A balança mostra o peso total, mas não revela quanto desse peso é carne ou acompanhamento. A nossa proposta é investigar como transformar uma foto e o peso total em informações sobre a composição do prato.”

## 0:20–0:45 — Como desenvolvemos

> “Criamos uma prova de conceito focada em frango. Usamos fotos reais e pesos por ingrediente da base Nutrition5k. Treinamos os modelos com 300 pratos e separamos outros 100 para o teste. Um modelo tenta identificar a presença de frango e outro estima sua massa.”

## 0:45–1:10 — Mostrar o sistema

**Na tela:** abra a aplicação, selecione uma amostra e confira o peso total informado. Clique no botão de análise e mostre a classificação e os gramas estimados. Se houver valor de referência para a amostra, mostre-o junto à previsão.

> “Aqui, a foto e o peso total são as entradas. O sistema mostra uma estimativa para frango. Nesta versão, o peso é informado manualmente; ainda não conectamos uma balança nem uma câmera ao restaurante.”

## 1:10–1:35 — Resultados e limites

> “Nos 100 pratos de teste, a classificação acertou 67% das respostas, mas também gerou muitos falsos positivos. O erro médio da estimativa de massa foi de 29,4 gramas. Isso ainda não é suficiente para usar o sistema em decisões do restaurante; por isso, mostramos os resultados como um experimento.”

## 1:35–1:55 — Próximo passo

> “O próximo passo seria testar com imagens e amostras de peso conhecido do próprio Bovinu’S, para avaliar o modelo no ambiente real. Com validação e integração à balança, a ideia poderia ajudar o restaurante a entender melhor o mix dos pratos servidos.”

## Antes de enviar

- Conferir se o vídeo tem **até 2 minutos** e se a demonstração está legível.
- Publicar em um local acessível à banca e verificar o link em janela anônima.
- Inserir o link público no README e no formulário, conforme as instruções do hackathon.
- Diferenciar estimativas do modelo de pesos medidos; não atribuir ganhos ou precisão ao Bovinu’S que ainda não foram comprovados.
