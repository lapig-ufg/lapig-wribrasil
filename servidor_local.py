"""
Servidor local para visualização instantânea do site Jekyll multi-página (LAPIG - ILPF)
Processa dinamicamente _layouts, _includes, frontmatter YAML e tags Liquid simples em tempo real.
Basta rodar: python servidor_local.py
"""

import http.server
import socketserver
import os
import re
import urllib.parse
import webbrowser

PORT = 8000
BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'docs')


def parse_frontmatter(content):
    """Extrai variáveis do frontmatter YAML e retorna (dict_vars, body)"""
    match = re.match(r'^---\s*\n([\s\S]*?)\n---\s*\n?', content)
    if not match:
        return {}, content

    yaml_block = match.group(1)
    body = content[match.end():]
    data = {}

    # Parser simples de chave-valor para YAML
    lines = yaml_block.split('\n')
    current_key = None
    multiline_val = []

    for line in lines:
        if not line.strip() or line.strip().startswith('#'):
            continue

        # Multiline string continuation (>- or |)
        if current_key and (line.startswith('  ') or line.startswith('\t')):
            multiline_val.append(line.strip())
            continue
        elif current_key and multiline_val:
            data[current_key] = ' '.join(multiline_val)
            current_key = None
            multiline_val = []

        if ':' in line:
            parts = line.split(':', 1)
            key = parts[0].strip()
            val = parts[1].strip()

            if val in ('>-', '>', '|', '|-'):
                current_key = key
                multiline_val = []
            else:
                # Remove quotes if present
                if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                    val = val[1:-1]
                data[key] = val

    if current_key and multiline_val:
        data[current_key] = ' '.join(multiline_val)

    return data, body


def process_includes(content, includes_dir, page_data=None):
    """Processa recursivamente tags {% include filename.html %}"""
    def replace_include(match):
        inc_file = match.group(1).strip()
        file_path = os.path.join(includes_dir, inc_file)
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                inc_content = f.read()
                # Process nested includes
                return process_includes(inc_content, includes_dir, page_data)
        return f"<!-- Include não encontrado: {inc_file} -->"

    return re.sub(r'{%\s*include\s+([a-zA-Z0-9_\-\.]+)\s*%}', replace_include, content)


def process_liquid_conditionals(content, page_data):
    """Processa {% if page.var %}...{% else %}...{% endif %}"""
    def eval_if(match):
        var_name = match.group(1).strip()
        if_body = match.group(2)
        else_body = match.group(3) if match.group(3) is not None else ""

        # Check variable in page_data
        key = var_name.replace('page.', '')
        has_val = bool(page_data.get(key))

        return if_body if has_val else else_body

    pattern = r'{%\s*if\s+([a-zA-Z0-9_\.]+)\s*%}([\s\S]*?)(?:{%\s*else\s*%}([\s\S]*?))?{%\s*endif\s*%}'
    # Repeat until all nested conditionals are resolved
    for _ in range(5):
        if not re.search(pattern, content):
            break
        content = re.sub(pattern, eval_if, content)

    return content


def process_liquid_variables(content, page_data):
    """Substitui {{ page.var }} e {{ "/path" | relative_url }}"""
    # 1. Page variables: {{ page.title }}, etc.
    for k, v in page_data.items():
        pattern = r'\{\{\s*page\.' + re.escape(k) + r'\s*\}\}'
        content = re.sub(pattern, str(v), content)

    # Clean leftover unknown page vars
    content = re.sub(r'\{\{\s*page\.[a-zA-Z0-9_]+\s*\}\}', '', content)

    # 2. Relative URLs: {{ "/assets/..." | relative_url }} -> /assets/...
    def replace_rel_url(match):
        raw_path = match.group(1).strip()
        if not raw_path:
            return ""
        if raw_path == "/":
            return "/"
        if not raw_path.startswith("/"):
            raw_path = "/" + raw_path
        return raw_path

    content = re.sub(r'\{\{\s*["\'](.*?)["\']\s*\|\s*relative_url\s*\}\}', replace_rel_url, content)

    return content


def render_jekyll_page(page_rel_path):
    """Renderiza uma página Jekyll aplicando layouts, includes e variáveis Liquid."""
    page_full_path = os.path.join(BASE_DIR, page_rel_path)
    layouts_dir = os.path.join(BASE_DIR, '_layouts')
    includes_dir = os.path.join(BASE_DIR, '_includes')

    if not os.path.exists(page_full_path):
        return None

    with open(page_full_path, 'r', encoding='utf-8') as f:
        page_raw = f.read()

    page_data, body_content = parse_frontmatter(page_raw)

    # Process nested layouts
    current_content = body_content
    layout_name = page_data.get('layout')
    visited_layouts = set()

    while layout_name and layout_name not in visited_layouts:
        visited_layouts.add(layout_name)
        layout_path = os.path.join(layouts_dir, f"{layout_name}.html")

        if not os.path.exists(layout_path):
            break

        with open(layout_path, 'r', encoding='utf-8') as f:
            layout_raw = f.read()

        layout_data, layout_body = parse_frontmatter(layout_raw)
        current_content = layout_body.replace('{{ content }}', current_content)
        layout_name = layout_data.get('layout')

    # Process includes
    rendered = process_includes(current_content, includes_dir, page_data)

    # Process conditionals & variables
    rendered = process_liquid_conditionals(rendered, page_data)
    rendered = process_liquid_variables(rendered, page_data)

    return rendered


class JekyllRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        clean_path = urllib.parse.unquote(parsed.path)

        # Route detection
        target_file = None
        if clean_path in ('/', ''):
            target_file = 'index.html'
        else:
            rel = clean_path.lstrip('/')
            full = os.path.join(BASE_DIR, rel)

            if os.path.isdir(full):
                index_candidate = os.path.join(full, 'index.html')
                if os.path.exists(index_candidate):
                    target_file = os.path.join(rel, 'index.html').replace('\\', '/')
            elif rel.endswith('.html') and os.path.isfile(full):
                target_file = rel
            elif os.path.isfile(full + '.html'):
                target_file = (rel + '.html').replace('\\', '/')

        if target_file:
            rendered = render_jekyll_page(target_file)
            if rendered is not None:
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(rendered.encode('utf-8'))))
                self.end_headers()
                self.wfile.write(rendered.encode('utf-8'))
                return

        return super().do_GET()


if __name__ == '__main__':
    os.chdir(BASE_DIR)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), JekyllRequestHandler) as httpd:
        url = f"http://localhost:{PORT}"
        print("=" * 60)
        print(f"[OK] Servidor LAPIG/ILPF multi-página rodando em: {url}")
        print("Rotas disponíveis:")
        print(f"  • Home:              {url}/")
        print(f"  • Cronograma:        {url}/cronograma/")
        print(f"  • Análise Top-3:     {url}/analise-top3/")
        print(f"  • Produtos/Download: {url}/produtos/")
        print("=" * 60)
        webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor encerrado.")
