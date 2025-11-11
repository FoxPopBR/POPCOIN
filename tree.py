# tree.py
"""
Foxtree: Visualizador de Estrutura de Diretórios com Ícones Personalizados

Repositório: https://github.com/FoxPopBR/Foxtree.git

Funcionalidades Principais:
- Geração de árvore de diretórios para projetos de software.
- Suporte a ícones personalizados para tipos de arquivo e diretórios específicos.
- Configuração flexível para ignorar diretórios e extensões de arquivos.
- Saída formatada em Markdown para fácil integração com documentações.

Como Usar:
1. Configure as preferências no arquivo `config_treemaker.py`.
2. Execute o script `tree.py` na raiz do seu projeto.
3. Visualize o arquivo `showtree.md` gerado para ver a estrutura de diretórios.

Personalização:
- `config_treemaker.py`: Define diretórios e extensões a serem ignorados, além de mapear ícones para tipos de arquivos e diretórios.
- Ícones e filtros podem ser ajustados para atender às necessidades específicas do seu projeto.

Estrutura do Projeto:
- `tree.py`: Script principal que inicia a geração da estrutura de diretórios.
- `config_treemaker.py`: Arquivo de configuração para personalização da ferramenta.
- `treemaker.py`: Contém a lógica para construir a representação visual da estrutura do diretório.

Desenvolvido por: [FoxpopBR]
Licença: [Mit]
"""
import pathlib
from tools.treemaker import TreeGenerator

def main():
    root_dir = pathlib.Path(__file__).resolve().parent
    generator = TreeGenerator(root_dir)
    tree = generator.generate_tree()

    with open("showtree.md", "w", encoding="utf-8") as file:
        file.write("<pre>\n")  # Adiciona a tag de início <pre>
        for line in tree:
            file.write(f"{line}\n")
        file.write("</pre>")  # Adiciona a tag de fim </pre>

if __name__ == "__main__":
    main()
