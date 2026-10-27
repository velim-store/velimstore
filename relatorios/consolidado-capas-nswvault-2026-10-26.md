# Resultado consolidado — capas NSWVault (26/10/2026)

Após o apontamento do caminho das capas pelo proprietário, foram executadas duas varreduras diretamente pelo GitHub Actions no repositório `velim-store/velimstore`.

## Resumo

| Indicador | Quantidade |
|---|---:|
| Jogos no catálogo | 212 |
| Capas provisórias examinadas | 34 |
| Capas trocadas para URL NSWVault com verificação de conteúdo de imagem | 14 |
| Capas provisórias remanescentes | 20 |
| Capa NSWVault anterior preservada (Castlevania Symphony of the Night) | 1 |

## Método

1. Página do jogo, como `https://nswvault.com/nintendo-switch/roms/dragon-ball-sparking-zero.html`.
2. Extração da URL real da capa nos campos `og:image`, `twitter:image` ou `img` do HTML.
3. Verificação da correspondência do nome e download da imagem para validar proporção vertical e predominância de vermelho na faixa superior esquerda.
4. Troca de `imageUrl` apenas de jogos previamente classificados como `mockup-provisorio`; os demais registros e tamanhos são preservados.
5. Não são criadas URLs por adivinhação do mês/ano de `/wp-content/uploads/`.

## Imagens atualizadas (14)

| Jogo | URL de imagem confirmada |
|---|---|
| Hades II | https://nswvault.com/wp-content/uploads/2026/09/hades-2.webp |
| Hello Kitty Island Adventure | https://nswvault.com/wp-content/uploads/2026/09/hello-kitty-island-adventure-deluxe-edition.webp |
| Inside | https://nswvault.com/wp-content/uploads/2026/10/inside.webp |
| Nine Sols | https://nswvault.com/wp-content/uploads/2024/11/Nine-Sols-nsp.png |
| Resident Evil 4 | https://nswvault.com/wp-content/uploads/2026/03/Resident-Evil-4.webp |
| Resident Evil 5 | https://nswvault.com/wp-content/uploads/2025/11/resident-evil-5.webp |
| Resident Evil 6 | https://nswvault.com/wp-content/uploads/2025/12/Resident_Evil_6.webp |
| Resident Evil Revelations | https://nswvault.com/wp-content/uploads/2025/12/Resident_Evil_Revelations.webp |
| Resident Evil Revelations 2 | https://nswvault.com/wp-content/uploads/2026/01/Resident_Evil_Revelations_2.webp |
| Shinobi Art of Vengeance | https://nswvault.com/wp-content/uploads/2025/09/SHINOBI-Art-of-Vengeance-nsp.png |
| Super Dragon Ball Heroes World Mission | https://nswvault.com/wp-content/uploads/2026/10/super-dragon-ball-heroes-world-mission.webp |
| The Rogue Prince of Persia | https://nswvault.com/wp-content/uploads/2026/01/the-rogue-prince-of-persia.webp |
| Tomb Raider Definitive edition | https://nswvault.com/wp-content/uploads/2026/10/tomb-raider-definitive-edition.webp |
| Tomodachi Life Living the Dream | https://nswvault.com/wp-content/uploads/2026/03/Tomodachi-Life-Living-the-Dream.webp |

## Ainda pendentes (20)

- Disney Classic Games Aladdin and The Lion King - Jungle Book
- Formula Legends
- Ghosts n Goblins Resurrection
- Hot Wheels Monster Trucks Stunt Mayhem
- Just Dance 2025 plus
- Let's Sing 2025
- Morbid the Lords of Ire
- My Universe Series for Nintendo Switch
- NAMCO Museum Archive Vol 1
- NAMCO Museum Archive Vol 2
- Naruto Shippuden Ultimate Ninja Storm Trilogy
- Pokemon Fire Red
- Pokemon Leaf Green
- Splatoon 2 + Octo Expansion
- Super Mario Bros 35
- Transformers Battlegrounds
- Transformers Earthspark Expedition
- Trials Rising [NSP]
- ULTIMATE NINJA STORM 4 ROAD TO BORUTO
- Virtual Boy Nintendo Classics

Os títulos pendentes não apresentaram página na forma testada ou exigem uma correspondência de edição diferente. Eles continuam com as capas provisórias anteriores; nenhuma capa de outro jogo foi reutilizada.

## Referências

- Varredura mais recente (diagnóstico detalhado): `relatorios/varredura-nswvault-2026-10-26.md`.
- Revisão anterior (remoção Arcade Archives e 7 substituições): `relatorios/revisao-capas-nswvault-2026-10-26.md`.
- Programa de verificação: `scripts/conferir_capas_nswvault.py`.
- Fluxo do GitHub Actions: `.github/workflows/conferir-capas-nswvault.yml`.
- Checkpoint anterior: `checkpoint/antes-dos-ajustes-2026-10-24` intacto.

**Limitação:** a verificação automática avalia URLs, dimensões e uma característica visual da capa. Ela não substitui a conferência humana de edição exata e pode classificar fotos distintas com faixas vermelhas similares. Não inclui verificação de licença de uso de imagem nem garante disponibilidade futura de arquivos hospedados por terceiros.
